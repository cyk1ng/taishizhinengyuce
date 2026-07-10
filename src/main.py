import os
import argparse
import asyncio
import json
import threading
import traceback
import logging
from datetime import datetime
from pathlib import Path
from contextlib import asynccontextmanager

# 手动加载 .env 文件（无需 python-dotenv 依赖）
_env_file = Path(__file__).parent.parent / '.env'
if _env_file.exists():
    with open(_env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, _, val = line.partition('=')
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and val and key not in os.environ:
                os.environ[key] = val
from typing import Any, Dict, Iterable, AsyncIterable, AsyncGenerator, Optional
# import cozeloop  # 已禁用，避免401认证日志
import uvicorn
import time
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from coze_coding_utils.runtime_ctx.context import new_context, Context
from coze_coding_utils.helper import graph_helper
from coze_coding_utils.log.node_log import LOG_FILE
from coze_coding_utils.log.write_log import setup_logging, request_context
from coze_coding_utils.log.config import LOG_LEVEL
from coze_coding_utils.error.classifier import ErrorClassifier, classify_error
from coze_coding_utils.helper.stream_runner import AgentStreamRunner, WorkflowStreamRunner,agent_stream_handler,workflow_stream_handler, RunOpt
from tools.local_knowledge import search_knowledge, import_document, get_all_documents, delete_document, update_document, count_documents, get_info
from tools.scheduling import (
    get_staff_detail as tool_get_staff_detail,
    add_temp_personnel as tool_add_temp_personnel,
    remove_temp_personnel as tool_remove_temp_personnel,
    end_shift as tool_end_shift,
    get_all_teams,
    ScheduleDataProvider,
)
from tools.plan_workload import get_workload_dashboard, calculate_plan_workload, PlanWorkloadDatabase
from tools.non_plan_workload import calculate_non_plan_workload, NonPlanWorkloadDatabase

setup_logging(
    log_file=LOG_FILE,
    max_bytes=100 * 1024 * 1024, # 100MB
    backup_count=5,
    log_level=LOG_LEVEL,
    use_json_format=True,
    console_output=True
)

logger = logging.getLogger(__name__)
from coze_coding_utils.helper.agent_helper import to_stream_input
from coze_coding_utils.openai.handler import OpenAIChatHandler
from coze_coding_utils.log.parser import LangGraphParser
from coze_coding_utils.log.err_trace import extract_core_stack
# from coze_coding_utils.log.loop_trace import init_run_config, init_agent_config  # 已禁用


# 超时配置常量
TIMEOUT_SECONDS = 900  # 15分钟

class GraphService:
    def __init__(self):
        # 用于跟踪正在运行的任务（使用asyncio.Task）
        self.running_tasks: Dict[str, asyncio.Task] = {}
        # 错误分类器
        self.error_classifier = ErrorClassifier()
        # stream runner
        self._agent_stream_runner = AgentStreamRunner()
        self._workflow_stream_runner = WorkflowStreamRunner()
        self._graph = None
        self._graph_lock = threading.Lock()

    def _get_graph(self, ctx=Context):
        # 强制使用Agent模式
        return graph_helper.get_agent_instance("agents.agent", ctx)

    @staticmethod
    def _sse_event(data: Any, event_id: Any = None) -> str:
        id_line = f"id: {event_id}\n" if event_id else ""
        return f"{id_line}event: message\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"

    def _get_stream_runner(self):
        if graph_helper.is_agent_proj():
            return self._agent_stream_runner
        else:
            return self._workflow_stream_runner

    # 流式运行（原始迭代器）：本地调用使用
    def stream(self, payload: Dict[str, Any], run_config: RunnableConfig, ctx=Context) -> Iterable[Any]:
        graph = self._get_graph(ctx)
        stream_runner = self._get_stream_runner()
        for chunk in stream_runner.stream(payload, graph, run_config, ctx):
            yield chunk

    # 同步运行：本地/HTTP 通用
    async def run(self, payload: Dict[str, Any], ctx=None) -> Dict[str, Any]:
        if ctx is None:
            ctx = new_context("run")

        run_id = ctx.run_id
        logger.info(f"Starting run with run_id: {run_id}")

        try:
            graph = self._get_graph(ctx)
            # custom tracer
            run_config = None
            if ctx and hasattr(ctx, 'run_id'):
                run_config = {"configurable": {"thread_id": ctx.run_id}}

            # 直接调用，LangGraph会在当前任务上下文中执行
            # 如果当前任务被取消，LangGraph的执行也会被取消
            return await graph.ainvoke(payload, config=run_config, context=ctx)

        except asyncio.CancelledError:
            logger.info(f"Run {run_id} was cancelled")
            return {"status": "cancelled", "run_id": run_id, "message": "Execution was cancelled"}
        except Exception as e:
            # 使用错误分类器分类错误
            err = self.error_classifier.classify(e, {"node_name": "run", "run_id": run_id})
            # 记录详细的错误信息和堆栈跟踪
            logger.error(
                f"Error in GraphService.run: [{err.code}] {err.message}\n"
                f"Category: {err.category.name}\n"
                f"Traceback:\n{extract_core_stack()}"
            )
            # 保留原始异常堆栈，便于上层返回真正的报错位置
            raise
        finally:
            # 清理任务记录
            self.running_tasks.pop(run_id, None)

    # 直接流式处理（绕过 AgentStreamRunner 的 content 数组转换）
    async def _agent_stream_direct(self, payload: Dict[str, Any], ctx=None, run_id: str = "") -> AsyncGenerator[str, None]:
        """直接使用 graph.astream() 流式返回，绕过多模态 content 数组格式"""
        if ctx is None:
            ctx = new_context(method="agent_stream_direct")

        logger.info(f"使用 _agent_stream_direct 处理 agent 流, run_id={run_id}")

        try:
            graph = self._get_graph(ctx)

            # 从 payload 中提取用户消息（支持 {message: "..."} 和 {"messages": [...]} 格式）
            user_query = ""
            if "message" in payload:
                user_query = payload["message"]
            elif "messages" in payload:
                msgs = payload["messages"]
                if msgs and isinstance(msgs, list):
                    last = msgs[-1]
                    if isinstance(last, dict):
                        user_query = last.get("content", "")
                    elif isinstance(last, str):
                        user_query = last

            if not user_query:
                user_query = str(payload)

            # 关键：用字符串格式（非数组），GLM-4-Flash 纯文本模型兼容
            stream_input = {"messages": [("user", user_query)]}
            run_config = {"configurable": {"thread_id": run_id or ctx.run_id}}

            logger.info(f"直接流式输入格式: 消息类型=字符串, 内容长度={len(user_query)}")

            # 使用 stream_mode="values" 获取完整状态更新
            # 只输出 AI 最终文本回复，过滤工具调用中间过程
            async for chunk in graph.astream(stream_input, stream_mode="values", config=run_config, context=ctx):
                messages = chunk.get("messages", [])
                if not messages:
                    continue

                last_msg = messages[-1]

                # 跳过工具调用消息（AIMessage 含 tool_calls）
                if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                    continue

                # 跳过工具执行结果（ToolMessage）
                if type(last_msg).__name__ == "ToolMessage":
                    continue

                # 跳过用户消息（HumanMessage）
                if type(last_msg).__name__ == "HumanMessage":
                    continue

                # 只输出 AI 文本回复
                msg_content = getattr(last_msg, "content", "")
                if not msg_content:
                    continue

                sse_data = {
                    "type": "message",
                    "content": msg_content,
                    "run_id": run_id or ctx.run_id,
                    "role": "assistant",
                }
                yield self._sse_event(sse_data)

            # 流结束事件
            end_data = {
                "type": "end",
                "run_id": run_id or ctx.run_id,
                "message": "Stream completed",
            }
            yield self._sse_event(end_data)
            logger.info(f"直接流式处理完成, run_id={run_id}")

        except asyncio.CancelledError:
            logger.info(f"直接流式处理被取消, run_id={run_id}")
            cancel_data = {
                "type": "end",
                "code": "CANCELED",
                "run_id": run_id or ctx.run_id,
                "message": "Stream cancelled",
            }
            yield self._sse_event(cancel_data)
        except Exception as e:
            logger.error(f"直接流式处理出错: {e}, run_id={run_id}", exc_info=True)
            err_data = {
                "type": "error",
                "code": "900002",
                "run_id": run_id or ctx.run_id,
                "error_msg": f"(BadRequestError): Error code: 400 - {str(e)}",
            }
            yield self._sse_event(err_data)

    # 流式运行（SSE 格式化）：HTTP 路由使用
    async def stream_sse(self, payload: Dict[str, Any], ctx=None, run_opt: Optional[RunOpt] = None) -> AsyncGenerator[str, None]:
        if ctx is None:
            ctx = new_context(method="stream_sse")
        if run_opt is None:
            run_opt = RunOpt()

        run_id = ctx.run_id
        logger.info(f"Starting stream with run_id: {run_id}")
        graph = self._get_graph(ctx)
        run_config = {}

        is_workflow = not graph_helper.is_agent_proj()

        try:
            async for chunk in self.astream(payload, graph, run_config=run_config, ctx=ctx, run_opt=run_opt):
                if is_workflow and isinstance(chunk, tuple):
                    event_id, data = chunk
                    yield self._sse_event(data, event_id)
                else:
                    yield self._sse_event(chunk)
        finally:
            # 清理任务记录
            self.running_tasks.pop(run_id, None)
            pass  # cozeloop.flush() disabled

    # 取消执行 - 使用asyncio的标准方式
    def cancel_run(self, run_id: str, ctx: Optional[Context] = None) -> Dict[str, Any]:
        """
        取消指定run_id的执行

        使用asyncio.Task.cancel()来取消任务,这是标准的Python异步取消机制。
        LangGraph会在节点之间检查CancelledError,实现优雅的取消。
        """
        logger.info(f"Attempting to cancel run_id: {run_id}")

        # 查找对应的任务
        if run_id in self.running_tasks:
            task = self.running_tasks[run_id]
            if not task.done():
                # 使用asyncio的标准取消机制
                # 这会在下一个await点抛出CancelledError
                task.cancel()
                logger.info(f"Cancellation requested for run_id: {run_id}")
                return {
                    "status": "success",
                    "run_id": run_id,
                    "message": "Cancellation signal sent, task will be cancelled at next await point"
                }
            else:
                logger.info(f"Task already completed for run_id: {run_id}")
                return {
                    "status": "already_completed",
                    "run_id": run_id,
                    "message": "Task has already completed"
                }
        else:
            logger.warning(f"No active task found for run_id: {run_id}")
            return {
                "status": "not_found",
                "run_id": run_id,
                "message": "No active task found with this run_id. Task may have already completed or run_id is invalid."
            }

    # 运行指定节点：本地/HTTP 通用
    async def run_node(self, node_id: str, payload: Dict[str, Any], ctx=None) -> Any:
        if ctx is None or Context.run_id == "":
            ctx = new_context(method="node_run")

        _graph = self._get_graph()
        node_func, input_cls, output_cls = graph_helper.get_graph_node_func_with_inout(_graph.get_graph(), node_id)
        if node_func is None or input_cls is None:
            raise KeyError(f"node_id '{node_id}' not found")

        parser = LangGraphParser(_graph)
        metadata = parser.get_node_metadata(node_id) or {}

        _g = StateGraph(input_cls, input_schema=input_cls, output_schema=output_cls)
        _g.add_node("sn", node_func, metadata=metadata)
        _g.set_entry_point("sn")
        _g.add_edge("sn", END)
        _graph = _g.compile()

        run_config = None
        return await _graph.ainvoke(payload, config=run_config)

    def graph_inout_schema(self) -> Any:
        if graph_helper.is_agent_proj():
            return {"input_schema": {}, "output_schema": {}}
        builder = getattr(self._get_graph(), 'builder', None)
        if builder is not None:
            input_cls = getattr(builder, 'input_schema', None) or self.graph.get_input_schema()
            output_cls = getattr(builder, 'output_schema', None) or self.graph.get_output_schema()
        else:
            logger.warning(f"No builder input schema found for graph_inout_schema, using graph input schema instead")
            input_cls = self.graph.get_input_schema()
            output_cls = self.graph.get_output_schema()

        return {
            "input_schema": input_cls.model_json_schema(), 
            "output_schema": output_cls.model_json_schema(),
            "code":0,
            "msg":""
        }

    async def astream(self, payload: Dict[str, Any], graph: CompiledStateGraph, run_config: RunnableConfig, ctx=Context, run_opt: Optional[RunOpt] = None) -> AsyncIterable[Any]:
        stream_runner = self._get_stream_runner()
        async for chunk in stream_runner.astream(payload, graph, run_config, ctx, run_opt):
            yield chunk


service = GraphService()

@asynccontextmanager
async def lifespan(application: FastAPI):
    """启动时预热模块加载，避免首次请求卡顿"""
    logger.info("⚡ 正在预热模块加载，请稍候...")
    t0 = time.time()
    # 模块级导入已在 main.py 顶部完成，这里只是触发完整初始化
    try:
        # 预热数据库连接
        from storage.database.db import is_database_connected
        if is_database_connected():
            logger.info("   ✅ 数据库连接成功")
        else:
            logger.info("   ℹ️  数据库未连接（SKIP_DB 或不可达），使用 mock 数据")
    except Exception as e:
        logger.info(f"   ℹ️  数据库预热跳过: {e}")
    
    elapsed = time.time() - t0
    logger.info(f"   ✅ 预热完成，耗时 {elapsed:.1f}s")
    yield

app = FastAPI(lifespan=lifespan)

# CORS - 允许沙箱代理跨域访问API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 天气配置（全局变量）
weather_config = {
    "tempMin": 25,
    "tempMax": 35,
    "precipitation": "小",
    "wind": "小",
    "extreme": "",
    "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "is_mock": True
}

# 配置静态文件服务（前端界面）
# 使用环境变量或当前工作目录来确定项目根目录
workspace_path = os.getenv("COZE_WORKSPACE_PATH", os.getcwd())
FRONTEND_DIR = Path(workspace_path) / "frontend"

logger.info(f"🔍 检查前端目录: {FRONTEND_DIR}")
logger.info(f"   目录存在: {FRONTEND_DIR.exists()}")

if FRONTEND_DIR.exists():
    # 挂载静态文件目录（逐个检查目录是否存在）
    css_dir = FRONTEND_DIR / "css"
    js_dir = FRONTEND_DIR / "js"
    assets_dir = FRONTEND_DIR / "assets"
    vendor_dir = FRONTEND_DIR / "vendor"
    
    logger.info(f"   CSS目录: {css_dir} - {css_dir.exists()}")
    logger.info(f"   JS目录: {js_dir} - {js_dir.exists()}")
    logger.info(f"   Assets目录: {assets_dir} - {assets_dir.exists()}")
    logger.info(f"   Vendor目录: {vendor_dir} - {vendor_dir.exists()}")
    
    if css_dir.exists():
        app.mount("/css", StaticFiles(directory=str(css_dir)), name="css")
        logger.info(f"   ✅ CSS静态文件已挂载")
    if js_dir.exists():
        app.mount("/js", StaticFiles(directory=str(js_dir)), name="js")
        logger.info(f"   ✅ JS静态文件已挂载")
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
        logger.info(f"   ✅ Assets静态文件已挂载")
    if vendor_dir.exists():
        app.mount("/vendor", StaticFiles(directory=str(vendor_dir)), name="vendor")
        logger.info(f"   ✅ Vendor静态文件已挂载")
    
    logger.info(f"✅ 前端界面已加载: {FRONTEND_DIR}")
else:
    logger.warning(f"⚠️ 前端目录不存在: {FRONTEND_DIR}")
    logger.warning(f"   当前工作目录: {os.getcwd()}")

# 前端首页路由
@app.get("/")
async def read_root():
    """返回前端首页"""
    try:
        index_file = FRONTEND_DIR / "index.html"
        logger.info(f"🔍 尝试访问首页: {index_file}")
        logger.info(f"   文件存在: {index_file.exists()}")

        if index_file.exists():
            return FileResponse(str(index_file))
        else:
            return {"message": "配网调度业务量智能预测系统 API 服务已启动", "docs": "/docs", "frontend_path": str(FRONTEND_DIR)}
    except Exception as e:
        logger.error(f"❌ 返回首页失败: {e}")
        return {"error": str(e), "frontend_path": str(FRONTEND_DIR)}

# 天气API接口
@app.get("/api/weather")
async def get_weather(city: str = None):
    """
    获取实时天气信息

    参数:
        city: 城市代码（可选，默认北京）

    返回:
        天气信息（温度、湿度、风力等）
    """
    try:
        # 优先返回保存的天气配置
        global weather_config
        if weather_config:
            return {
                "success": True,
                "data": weather_config
            }

        # 如果没有配置，则调用API获取
        from tools.weather_api import get_weather_info
        weather_data = get_weather_info(city)
        return weather_data
    except Exception as e:
        logger.error(f"获取天气信息失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": {
                "tempMin": 25,
                "tempMax": 35,
                "precipitation": "小",
                "wind": "小",
                "extreme": "",
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }

# 天气保存API接口
@app.post("/api/weather")
async def save_weather(request: Request):
    """
    保存天气信息

    参数:
        tempMin: 最低温度
        tempMax: 最高温度
        precipitation: 降水量等级
        wind: 风力等级
        extreme: 极端天气情况

    返回:
        保存结果
    """
    try:
        import json
        from datetime import datetime

        raw_body = await request.body()
        try:
            body_text = raw_body.decode("utf-8")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON format")

        weather_data = json.loads(body_text)

        # 验证必填字段
        required_fields = ["tempMin", "tempMax", "precipitation", "wind"]
        for field in required_fields:
            if field not in weather_data:
                raise HTTPException(status_code=400, detail=f"缺少必填字段: {field}")

        temp_min = int(weather_data["tempMin"])
        temp_max = int(weather_data["tempMax"])
        precipitation = weather_data["precipitation"]
        wind = weather_data["wind"]
        extreme = weather_data.get("extreme", "")

        # 验证温度范围
        if temp_min > temp_max:
            raise HTTPException(status_code=400, detail="最低温度不能大于最高温度")

        # 更新天气配置（保存到全局变量或数据库）
        weather_config.update({
            "tempMin": temp_min,
            "tempMax": temp_max,
            "precipitation": precipitation,
            "wind": wind,
            "extreme": extreme,
            "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "is_mock": False
        })

        logger.info(f"天气信息已更新: {weather_config}")

        return {
            "success": True,
            "message": "天气信息保存成功",
            "data": weather_config
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"保存天气信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"保存天气信息失败: {str(e)}")

def _mock_dashboard_response(today):
    """生成兜底假数据（与 plan_workload_detail 和 nonplan_workload_detail 的 mock 数据保持一致）"""
    # 计划工作量各模块：检修11 + 投退5 + 方式单7 + 周计划18 + 保供电9 = 50
    # 非计划工作量各模块：跳闸(故障)7 + 缺陷3 + 重过载2 = 12
    return {
        "success": True,
        "date": today,
        "source": "mock",
        "summary": {
            "total_plan_count": 50,
            "total_non_plan_count": 12,
            "overload_count": 2,
            "in_progress": 35,
            "completed": 15,
            "fault_count": 7,
            "defect_count": 3
        },
        "hourly_details": [
            {
                "hour": h,
                "plan": max(0, 4 - abs(h - 10)),
                "nonplan": max(0, 2 - abs(h - 14)),
                "total_equivalent": max(0, 4 - abs(h - 10)) + max(0, 2 - abs(h - 14)),
                "staff_capacity": max(0, 4 - abs(h - 10)) + max(0, 2 - abs(h - 14)) + 1,
                "plan_equivalent": max(0, 4 - abs(h - 10)),
                "non_plan_equivalent": max(0, 2 - abs(h - 14)),
                "staff_count": 3
            }
            for h in range(6, 23)
        ],
        "plan_allocation": {"morning": 20, "afternoon": 18, "night": 12},
        "moduleBusiness": {
            "labels": ["周计划", "设备投退", "跳闸（故障）", "缺陷", "重过载", "保供电", "检修业务", "方式单"],
            "values": [18, 5, 7, 3, 2, 9, 11, 7]
        }
    }

# 工作量看板数据接口
@app.get("/api/workload_dashboard")
async def workload_dashboard():
    """获取今日工作量看板数据（实时数据库查询）"""
    _t0 = time.time()
    logger.info(f"[timing] workload_dashboard 开始处理")
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        logger.info(f"[timing] 准备今天日期: {time.time()-_t0:.2f}s")
        
        # 调用现有工具获取今日数据
        dashboard_raw = get_workload_dashboard.invoke({"target_date": today})
        logger.info(f"[timing] get_workload_dashboard.invoke 完成: {time.time()-_t0:.2f}s")
        dashboard_data = json.loads(dashboard_raw) if isinstance(dashboard_raw, str) else dashboard_raw
        
        plan_raw = calculate_plan_workload.invoke({"target_date": today})
        logger.info(f"[timing] calculate_plan_workload.invoke 完成: {time.time()-_t0:.2f}s")
        plan_data = json.loads(plan_raw) if isinstance(plan_raw, str) else plan_raw
        
        nonplan_raw = calculate_non_plan_workload.invoke({"target_date": today})
        logger.info(f"[timing] calculate_non_plan_workload.invoke 完成: {time.time()-_t0:.2f}s")
        
        # 聚合前端所需数据格式
        # dashboard_data 结构: {success, data: {plan_workload: {...}, non_plan_workload: {...}}}
        inner_data = dashboard_data.get("data", {})
        plan_workload = inner_data.get("plan_workload", {})
        nonplan_workload = inner_data.get("non_plan_workload", {})
        
        # 计划工作量汇总 - 从各分类汇总加总
        total_plan = (
            plan_workload.get("maintenance", {}).get("summary", {}).get("total", 0) +
            plan_workload.get("equipment", {}).get("summary", {}).get("total", 0) +
            plan_workload.get("transfer", {}).get("summary", {}).get("total", 0) +
            plan_workload.get("weekly_plan", {}).get("summary", {}).get("total", 0) +
            plan_workload.get("protect", {}).get("summary", {}).get("total", 0)
        )
        in_progress = (
            plan_workload.get("maintenance", {}).get("summary", {}).get("in_progress", 0) +
            plan_workload.get("equipment", {}).get("summary", {}).get("in_progress", 0) +
            plan_workload.get("transfer", {}).get("summary", {}).get("in_progress", 0) +
            plan_workload.get("weekly_plan", {}).get("summary", {}).get("in_progress", 0) +
            plan_workload.get("protect", {}).get("summary", {}).get("in_progress", 0)
        )
        completed = (
            plan_workload.get("maintenance", {}).get("summary", {}).get("completed", 0) +
            plan_workload.get("equipment", {}).get("summary", {}).get("completed", 0) +
            plan_workload.get("transfer", {}).get("summary", {}).get("completed", 0) +
            plan_workload.get("weekly_plan", {}).get("summary", {}).get("completed", 0) +
            plan_workload.get("protect", {}).get("summary", {}).get("completed", 0)
        )
        
        total_nonplan = nonplan_workload.get("total_count", 0)
        fault_count = nonplan_workload.get("fault_logs", {}).get("count", 0)
        defect_count = nonplan_workload.get("defect_records", {}).get("count", 0)
        overload_count = nonplan_workload.get("overload_records", {}).get("count", 0)
        
        # 如果真实数据全为0，也使用兜底假数据（避免Oracle空表导致界面空白）
        if total_plan == 0 and total_nonplan == 0 and fault_count == 0:
            logger.warning("数据库返回空数据，使用兜底假数据")
            return _mock_dashboard_response(today)
        
        return {
            "success": True,
            "source": "real",
            "date": today,
            "summary": {
                "total_plan_count": total_plan,
                "total_non_plan_count": total_nonplan,
                "overload_count": overload_count,
                "in_progress": in_progress,
                "completed": completed,
                "fault_count": fault_count,
                "defect_count": defect_count
            },
            "hourly_details": [],
            "plan_allocation": plan_data.get("shift_allocation", {}),
            "moduleBusiness": {
                "labels": ["周计划", "设备投退", "跳闸", "缺陷", "重过载", "保供电", "检修业务", "方式单"],
                "values": [
                    plan_workload.get("weekly_plan", {}).get("summary", {}).get("total", 0),
                    plan_workload.get("equipment", {}).get("summary", {}).get("total", 0),
                    fault_count,
                    defect_count,
                    overload_count,
                    plan_workload.get("protect", {}).get("summary", {}).get("total", 0),
                    plan_workload.get("maintenance", {}).get("summary", {}).get("total", 0),
                    plan_workload.get("transfer", {}).get("summary", {}).get("total", 0)
                ]
            },
            "raw": dashboard_data
        }
    except Exception as e:
        logger.error(f"获取今日工作量数据失败: {e}，使用兜底假数据")
        return _mock_dashboard_response(today)

# 计划工作量详情接口（供前端弹窗调用）
@app.get("/api/plan_workload_detail")
async def plan_workload_detail():
    """返回计划工作量各分类详情（含兜底假数据）"""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 采集各表数据
        results = {}
        tables = {
            "maintenance": (PlanWorkloadDatabase.collect_maintenance_workload, ""),
            "equipment": (PlanWorkloadDatabase.collect_equipment_workload, ""),
            "transfer": (PlanWorkloadDatabase.collect_transfer_workload, ""),
            "weekly_plan": (PlanWorkloadDatabase.collect_weekly_plan_workload, ""),
            "protect": (PlanWorkloadDatabase.collect_protect_feeder_workload, ""),
        }
        
        total_in_progress = 0
        total_completed = 0
        grand_total = 0
        
        for name, (func, _) in tables.items():
            try:
                records = func("")
                in_prog = sum(1 for r in records if r.get("status_category") == "in_progress")
                compl = sum(1 for r in records if r.get("status_category") == "completed")
                results[name] = {
                    "in_progress": in_prog,
                    "completed": compl,
                    "total": len(records),
                    "count": len(records)
                }
                total_in_progress += in_prog
                total_completed += compl
                grand_total += len(records)
            except Exception as e:
                logger.warning(f"采集 {name} 失败: {e}")
                results[name] = {"in_progress": 0, "completed": 0, "total": 0, "count": 0}
        
        shift_allocation = {
            "morning": max(1, int(grand_total * 0.4)) if grand_total > 0 else 0,
            "afternoon": max(1, int(grand_total * 0.35)) if grand_total > 0 else 0,
            "night": max(0, grand_total - max(1, int(grand_total * 0.4)) - max(1, int(grand_total * 0.35))) if grand_total > 0 else 0
        }
        
        # 如果查询数据全为0，使用兜底假数据
        if grand_total == 0:
            logger.warning("计划工作量详情为空，使用兜底假数据")
            fallback = {
                "success": True,
                "date": today,
                "source": "mock",
                "details": {
                    "maintenance": {"in_progress": 8, "completed": 3, "total": 11, "count": 11},
                    "transfer": {"in_progress": 5, "completed": 2, "total": 7, "count": 7},
                    "equipment": {"in_progress": 4, "completed": 1, "total": 5, "count": 5},
                    "weekly_plan": {"in_progress": 12, "completed": 6, "total": 18, "count": 18},
                    "protect": {"in_progress": 6, "completed": 3, "total": 9, "count": 9}
                },
                "summary": {"total_in_progress": 35, "total_completed": 15, "grand_total": 50},
                "shift_allocation": {"morning": 20, "afternoon": 18, "night": 12}
            }
            logger.info(f"使用兜底假数据")
            return fallback

        # 覆盖已由 workload_data 接口统一管理，此处不再叠加
        details = results
        total_ip = total_in_progress
        total_cp = total_completed
        total_gt = grand_total
        
        return {
            "success": True,
            "date": today,
            "details": details,
            "summary": {
                "total_in_progress": total_ip,
                "total_completed": total_cp,
                "grand_total": total_gt
            },
            "shift_allocation": shift_allocation
        }
    except Exception as e:
        logger.error(f"获取计划工作量详情失败: {e}")
        fallback = {
            "success": True,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "source": "mock",
            "details": {
                "maintenance": {"in_progress": 8, "completed": 3, "total": 11, "count": 11},
                "transfer": {"in_progress": 5, "completed": 2, "total": 7, "count": 7},
                "equipment": {"in_progress": 4, "completed": 1, "total": 5, "count": 5},
                "weekly_plan": {"in_progress": 12, "completed": 6, "total": 18, "count": 18},
                "protect": {"in_progress": 6, "completed": 3, "total": 9, "count": 9}
            },
            "summary": {"total_in_progress": 35, "total_completed": 15, "grand_total": 50},
            "shift_allocation": {"morning": 20, "afternoon": 18, "night": 12}
        }
        logger.info(f"使用兜底假数据: {str(fallback)}")
        return fallback

# 非计划工作量详情接口
@app.get("/api/nonplan_workload_detail")
async def nonplan_workload_detail():
    """返回非计划工作量各分类详情（含兜底假数据）"""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        
        results = {}
        tables = {
            "fault": (NonPlanWorkloadDatabase.collect_fault_logs, ""),
            "defect": (NonPlanWorkloadDatabase.collect_defect_records, ""),
            "overload": (NonPlanWorkloadDatabase.collect_overload_records, ""),
        }
        
        grand_total = 0
        for name, (func, _) in tables.items():
            try:
                records = func("")
                results[name] = {"count": len(records)}
                grand_total += len(records)
            except Exception as e:
                logger.warning(f"采集 {name} 失败: {e}")
                results[name] = {"count": 0}
        
        # 如果查询数据全为0，使用兜底假数据
        if grand_total == 0:
            logger.warning("非计划工作量详情为空，使用兜底假数据")
            fallback = {
                "success": True,
                "date": today,
                "source": "mock",
                "details": {
                    "fault": {"count": 7},
                    "defect": {"count": 3},
                    "overload": {"count": 2}
                },
                "total": 12
            }
            # 应用覆盖数据
            from workload_override import load_overrides, apply_overrides_to_details
            overrides = load_overrides("nonplan", today)
            if overrides:
                fallback["details"] = apply_overrides_to_details(fallback["details"], overrides)
                fallback["total"] = sum(v.get("count", 0) for v in fallback["details"].values())
            logger.info(f"使用兜底假数据")
            return fallback
        
        # 覆盖已由 workload_data 接口统一管理
        return {
            "success": True,
            "date": today,
            "details": results,
            "total": grand_total
        }
    except Exception as e:
        logger.error(f"获取非计划工作量详情失败: {e}")
        fallback = {
            "success": True,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "source": "mock",
            "details": {
                "fault": {"count": 7},
                "defect": {"count": 3},
                "overload": {"count": 2}
            },
            "total": 12
        }
        logger.info(f"使用兜底假数据: {str(fallback)}")
        return fallback

# 保存工作量覆盖数据
@app.post("/api/save_workload_override")
async def save_workload_override(request: Request):
    """
    保存用户在前端弹窗手动修改的工作量数据。
    请求体 JSON：
    {
        "workload_type": "plan" | "nonplan",
        "data": {
            "maintenance": {"in_progress": 10, "completed": 5},
            ...
        },
        "target_date": "2026-06-26"   // 可选，默认今天
    }
    """
    try:
        body = await request.json()
        wl_type = body.get("workload_type", "")
        data = body.get("data", {})
        target_date = body.get("target_date", datetime.now().strftime("%Y-%m-%d"))

        if wl_type not in ("plan", "nonplan"):
            return {"success": False, "error": "workload_type 必须为 plan 或 nonplan"}
        if not data:
            return {"success": False, "error": "data 不能为空"}

        from workload_manager import save_manual_edits
        ok = save_manual_edits(wl_type, data, target_date)

        return {"success": ok, "message": "保存成功" if ok else "保存失败"}
    except Exception as e:
        logger.error(f"保存工作量覆盖数据失败: {e}")
        return {"success": False, "error": str(e)}


# ===== 页面数据快照接口 =====

@app.post("/api/save_page_snapshot")
async def save_page_snapshot(request: Request):
    """
    保存当前页面数据快照。
    前端在页面加载完成、数据修改后自动调用。
    请求体：{
      "page_data": {...},
      "target_date": "2026-06-26",
      "dis_org_id": "xxx", "dis_org_name": "xxx",
      "county_dept_id": "xxx", "county_dept_name": "xxx"
    }
    """
    try:
        body = await request.json()
        page_data = body.get("page_data", {})
        target_date = body.get("target_date", datetime.now().strftime("%Y-%m-%d"))
        dis_org_id = body.get("dis_org_id", "")
        dis_org_name = body.get("dis_org_name", "")
        county_dept_id = body.get("county_dept_id", "")
        county_dept_name = body.get("county_dept_name", "")

        if not page_data:
            return {"success": False, "error": "page_data 不能为空"}

        from snapshot_manager import save_snapshot
        ok = save_snapshot(
            page_data, target_date,
            dis_org_id=dis_org_id, dis_org_name=dis_org_name,
            county_dept_id=county_dept_id, county_dept_name=county_dept_name
        )

        return {"success": ok, "message": "快照已保存" if ok else "保存失败"}
    except Exception as e:
        logger.error(f"保存页面快照失败: {e}")
        return {"success": False, "error": str(e)}


@app.get("/api/get_page_snapshot")
async def get_page_snapshot(target_date: str = ""):
    """
    获取指定日期的页面数据快照。
    AI 分析时调用此接口读取当前页面数据。
    """
    try:
        from snapshot_manager import get_snapshot
        date = target_date or datetime.now().strftime("%Y-%m-%d")
        data = get_snapshot(date)
        if data:
            return {"success": True, "data": data, "date": date}
        else:
            return {"success": False, "message": f"{date} 暂无快照数据", "date": date}
    except Exception as e:
        logger.error(f"获取页面快照失败: {e}")
        return {"success": False, "error": str(e)}


# ===== 工作量数据统一管理接口 =====

@app.get("/api/workload_data")
async def workload_data(target_date: str = ""):
    """
    获取工作量数据（含覆盖已合并的结果）。
    自动初始化 OC_WORKLOAD_DATA 表数据。
    """
    try:
        from workload_manager import get_workload_data
        date = target_date or datetime.now().strftime("%Y-%m-%d")
        data = get_workload_data(date)
        return {"success": True, "data": data}
    except Exception as e:
        logger.error(f"获取工作量数据失败: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/check_workload_updates")
async def check_workload_updates(target_date: str = ""):
    """
    检查源数据是否有更新。
    返回 has_updates: bool 前端据此决定是否弹出提示。
    """
    try:
        from workload_manager import check_workload_updates
        date = target_date or datetime.now().strftime("%Y-%m-%d")
        result = check_workload_updates(date)
        return {"success": True, **result}
    except Exception as e:
        logger.error(f"检查工作量更新失败: {e}")
        return {"success": False, "error": str(e), "has_updates": False}

@app.post("/api/apply_workload_updates")
async def apply_workload_updates(request: Request):
    """
    用户确认后，用新源数据覆盖工作量表。
    """
    try:
        from workload_manager import apply_source_updates
        body = await request.json()
        target_date = body.get("target_date", datetime.now().strftime("%Y-%m-%d"))
        result = apply_source_updates(target_date)
        return {"success": True, **result}
    except Exception as e:
        logger.error(f"应用工作量更新失败: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/predict_workload")
async def predict_workload(target_date: str = ""):
    """
    根据工作量数据 + 班组排班 → 大模型预测工作量趋势
    """
    try:
        from workload_manager import predict_workload
        date = target_date or datetime.now().strftime("%Y-%m-%d")
        result = predict_workload(date)
        return {"success": True, **result}
    except Exception as e:
        logger.error(f"工作量预测失败: {e}")
        return {"success": False, "error": str(e)}

# 健康检查接口
@app.get("/health")
@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "ok", "service": "配网调度业务量智能预测系统"}

# ===== 知识库 API（放在通配路由之前，避免被拦截）=====

@app.get("/api/knowledge/list")
async def knowledge_list(page: int = 1, page_size: int = 20):
    """获取知识库文档列表（分页）"""
    try:
        result = get_all_documents(page=page, page_size=page_size)
        return result
    except Exception as e:
        logger.error(f"知识库列表查询失败: {e}")
        return {"total": 0, "page": page, "page_size": page_size, "documents": []}

@app.get("/api/knowledge/search")
async def knowledge_search(q: str = "", top_k: int = 5):
    """搜索知识库"""
    try:
        if not q.strip():
            return get_all_documents(page=1, page_size=top_k)
        results = search_knowledge(query=q, top_k=top_k)
        return {"total": len(results), "results": results}
    except Exception as e:
        logger.error(f"知识库搜索失败: {e}")
        return {"total": 0, "results": []}

@app.post("/api/knowledge/add")
async def knowledge_add(request: Request):
    """添加知识到知识库"""
    try:
        data = await request.json()
        content = data.get("content", "").strip()
        source = data.get("source", "用户手动添加")
        if not content:
            return {"success": False, "error": "内容不能为空"}
        result = import_document(content, source_name=source)
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"知识库添加失败: {e}")
        return {"success": False, "error": str(e)}

@app.put("/api/knowledge/update")
async def knowledge_update(request: Request):
    """更新知识库文档"""
    try:
        data = await request.json()
        doc_id = data.get("id", "").strip()
        content = data.get("content", "").strip()
        source = data.get("source", "").strip() or None
        if not doc_id or not content:
            return {"success": False, "error": "ID和内容不能为空"}
        result = update_document(doc_id, content, source_name=source)
        return result
    except Exception as e:
        logger.error(f"知识库更新失败: {e}")
        return {"success": False, "error": str(e)}

@app.delete("/api/knowledge/delete")
async def knowledge_delete(request: Request):
    """删除知识库文档"""
    try:
        data = await request.json()
        doc_id = data.get("id", "").strip()
        if not doc_id:
            return {"success": False, "error": "ID不能为空"}
        result = delete_document(doc_id)
        return result
    except Exception as e:
        logger.error(f"知识库删除失败: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/knowledge/info")
async def knowledge_info():
    """获取知识库统计信息"""
    try:
        return get_info()
    except Exception as e:
        return {"type": "local", "error": str(e)}


# ═══════════════════════════════════════════════
#  值班人员管理 API
# ═══════════════════════════════════════════════

@app.get("/api/staff/teams")
async def api_get_teams():
    """获取所有班组信息"""
    try:
        teams = get_all_teams()
        return {"success": True, "data": teams}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/staff/detail")
async def api_get_staff_detail(team_name: str = "", date_str: str = ""):
    """
    获取值班人员详情
    - team_name: 班组名称（可选）
    - date_str: 日期 YYYY-MM-DD（可选，默认今天）
    """
    try:
        result = json.loads(tool_get_staff_detail(team_name=team_name, date_str=date_str))
        if result.get("code") == 0:
            return {"success": True, "data": result}
        return {"success": False, "error": result.get("error", "获取失败")}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/staff/temp/add")
async def api_add_temp_personnel(request: Request):
    """
    跨班组临时借调 — 添加临时值班人员
    Body: { record_id, person_id, person_name, home_team_name }
    """
    try:
        body = await request.json()
        result = json.loads(tool_add_temp_personnel(
            record_id=body.get("record_id", ""),
            person_id=body.get("person_id", ""),
            person_name=body.get("person_name", ""),
            home_team_name=body.get("home_team_name", ""),
        ))
        if result.get("code") == 0:
            return {"success": True, "data": result, "msg": result.get("msg", "")}
        return {"success": False, "error": result.get("error", "添加失败")}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/staff/temp/remove")
async def api_remove_temp_personnel(request: Request):
    """
    移除临时值班人员
    Body: { record_id, person_id }
    """
    try:
        body = await request.json()
        result = json.loads(tool_remove_temp_personnel(
            record_id=body.get("record_id", ""),
            person_id=body.get("person_id", ""),
        ))
        if result.get("code") == 0:
            return {"success": True, "data": result, "msg": result.get("msg", "")}
        return {"success": False, "error": result.get("error", "移除失败")}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/staff/end_shift")
async def api_end_shift(request: Request):
    """
    交班操作 — 结束班次，自动清除临时人员
    Body: { record_id }
    """
    try:
        body = await request.json()
        result = json.loads(tool_end_shift(
            record_id=body.get("record_id", ""),
        ))
        if result.get("code") == 0:
            return {"success": True, "data": result, "msg": result.get("msg", "")}
        return {"success": False, "error": result.get("error", "交班失败")}
    except Exception as e:
        return {"success": False, "error": str(e)}


# 前端 HTML 文件路由（必须放在最后，避免拦截API路由）
@app.get("/{file_name:path}")
async def read_html_files(file_name: str):
    """返回前端 HTML 文件"""
    # 检查是否是 HTML 文件
    if file_name.endswith('.html'):
        try:
            html_file = FRONTEND_DIR / file_name
            logger.info(f"🔍 尝试访问HTML文件: {html_file}")
            logger.info(f"   文件存在: {html_file.exists()}")

            if html_file.exists():
                return FileResponse(str(html_file))
            else:
                return {"error": "文件不存在", "file": file_name}
        except Exception as e:
            logger.error(f"❌ 返回HTML文件失败: {e}")
            return {"error": str(e)}
    # 如果不是 HTML 文件，返回 404
    else:
        raise HTTPException(status_code=404, detail="Not Found")

# OpenAI 兼容接口处理器
openai_handler = OpenAIChatHandler(service)


HEADER_X_RUN_ID = "x-run-id"
@app.post("/run")
async def http_run(request: Request) -> Dict[str, Any]:
    global result
    raw_body = await request.body()
    try:
        body_text = raw_body.decode("utf-8")
    except Exception as e:
        body_text = str(raw_body)
        raise HTTPException(status_code=400,
                            detail=f"Invalid JSON format: {body_text}, traceback: {traceback.format_exc()}, error: {e}")

    ctx = new_context(method="run", headers=request.headers)
    # 优先使用上游指定的 run_id，保证 cancel 能精确匹配
    upstream_run_id = request.headers.get(HEADER_X_RUN_ID)
    if upstream_run_id:
        ctx.run_id = upstream_run_id
    run_id = ctx.run_id
    request_context.set(ctx)

    logger.info(
        f"Received request for /run: "
        f"run_id={run_id}, "
        f"query={dict(request.query_params)}, "
        f"body={body_text}"
    )

    try:
        payload = await request.json()

        # 创建任务并记录 - 这是关键，让我们可以通过run_id取消任务
        task = asyncio.create_task(service.run(payload, ctx))
        service.running_tasks[run_id] = task

        try:
            result = await asyncio.wait_for(task, timeout=float(TIMEOUT_SECONDS))
        except asyncio.TimeoutError:
            logger.error(f"Run execution timeout after {TIMEOUT_SECONDS}s for run_id: {run_id}")
            task.cancel()
            try:
                result = await task
            except asyncio.CancelledError:
                return {
                    "status": "timeout",
                    "run_id": run_id,
                    "message": f"Execution timeout: exceeded {TIMEOUT_SECONDS} seconds"
                }

        if not result:
            result = {}
        if isinstance(result, dict):
            result["run_id"] = run_id
        return result

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in http_run: {e}, traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=400, detail=f"Invalid JSON format, {extract_core_stack()}")

    except asyncio.CancelledError:
        logger.info(f"Request cancelled for run_id: {run_id}")
        result = {"status": "cancelled", "run_id": run_id, "message": "Execution was cancelled"}
        return result

    except Exception as e:
        # 使用错误分类器获取错误信息
        error_response = service.error_classifier.get_error_response(e, {"node_name": "http_run", "run_id": run_id})
        logger.error(
            f"Unexpected error in http_run: [{error_response['error_code']}] {error_response['error_message']}, "
            f"traceback: {traceback.format_exc()}", exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": error_response["error_code"],
                "error_message": error_response["error_message"],
                "stack_trace": extract_core_stack(),
            }
        )
    finally:
        pass  # cozeloop.flush() disabled


HEADER_X_WORKFLOW_STREAM_MODE = "x-workflow-stream-mode"


def _register_task(run_id: str, task: asyncio.Task):
    service.running_tasks[run_id] = task


@app.post("/stream_run")
async def http_stream_run(request: Request):
    ctx = new_context(method="stream_run", headers=request.headers)
    # 优先使用上游指定的 run_id，保证 cancel 能精确匹配
    upstream_run_id = request.headers.get(HEADER_X_RUN_ID)
    if upstream_run_id:
        ctx.run_id = upstream_run_id
    workflow_stream_mode = request.headers.get(HEADER_X_WORKFLOW_STREAM_MODE, "").lower()
    workflow_debug = workflow_stream_mode == "debug"
    request_context.set(ctx)
    raw_body = await request.body()
    try:
        body_text = raw_body.decode("utf-8")
    except Exception as e:
        body_text = str(raw_body)
        raise HTTPException(status_code=400,
                            detail=f"Invalid JSON format: {body_text}, traceback: {extract_core_stack()}, error: {e}")
    run_id = ctx.run_id
    is_agent = graph_helper.is_agent_proj()
    logger.info(
        f"Received request for /stream_run: "
        f"run_id={run_id}, "
        f"is_agent_project={is_agent}, "
        f"query={dict(request.query_params)}, "
        f"body={body_text}"
    )
    try:
        payload = await request.json()
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in http_stream_run: {e}, traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=400, detail=f"Invalid JSON format:{extract_core_stack()}")

    # 强制使用直接流式处理（本项目是 Agent，但环境变量 COZE_PROJECT_TYPE 未设置导致 is_agent_proj() 返回 False）
    # 使用直接流式处理，绕过 AgentStreamRunner 的 content 数组转换 + 绕过 is_agent_proj 判断
    if True:
        stream_generator = service._agent_stream_direct(
            payload=payload,
            ctx=ctx,
            run_id=run_id,
        )
    else:
        stream_generator = workflow_stream_handler(
            payload=payload,
            ctx=ctx,
            run_id=run_id,
            stream_sse_func=service.stream_sse,
            sse_event_func=service._sse_event,
            error_classifier=service.error_classifier,
            register_task_func=_register_task,
            run_opt=RunOpt(workflow_debug=workflow_debug),
        )

    response = StreamingResponse(stream_generator, media_type="text/event-stream")
    return response

@app.post("/cancel/{run_id}")
async def http_cancel(run_id: str, request: Request):
    """
    取消指定run_id的执行

    使用asyncio.Task.cancel()实现取消,这是Python标准的异步任务取消机制。
    LangGraph会在节点之间的await点检查CancelledError,实现优雅取消。
    """
    ctx = new_context(method="cancel", headers=request.headers)
    request_context.set(ctx)
    logger.info(f"Received cancel request for run_id: {run_id}")
    result = service.cancel_run(run_id, ctx)
    return result


@app.post(path="/node_run/{node_id}")
async def http_node_run(node_id: str, request: Request):
    raw_body = await request.body()
    try:
        body_text = raw_body.decode("utf-8")
    except UnicodeDecodeError:
        body_text = str(raw_body)
        raise HTTPException(status_code=400, detail=f"Invalid JSON format: {body_text}")
    ctx = new_context(method="node_run", headers=request.headers)
    request_context.set(ctx)
    logger.info(
        f"Received request for /node_run/{node_id}: "
        f"query={dict(request.query_params)}, "
        f"body={body_text}",
    )

    try:
        payload = await request.json()
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in http_node_run: {e}, traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=400, detail=f"Invalid JSON format:{extract_core_stack()}")
    try:
        return await service.run_node(node_id, payload, ctx)
    except KeyError:
        raise HTTPException(status_code=404,
                            detail=f"node_id '{node_id}' not found or input miss required fields, traceback: {extract_core_stack()}")
    except Exception as e:
        # 使用错误分类器获取错误信息
        error_response = service.error_classifier.get_error_response(e, {"node_name": node_id})
        logger.error(
            f"Unexpected error in http_node_run: [{error_response['error_code']}] {error_response['error_message']}, "
            f"traceback: {traceback.format_exc()}", exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": error_response["error_code"],
                "error_message": error_response["error_message"],
                "stack_trace": extract_core_stack(),
            }
        )
    finally:
        pass  # cozeloop.flush() disabled


@app.post("/v1/chat/completions")
async def openai_chat_completions(request: Request):
    """OpenAI Chat Completions API 兼容接口"""
    ctx = new_context(method="openai_chat", headers=request.headers)
    request_context.set(ctx)

    logger.info(f"Received request for /v1/chat/completions: run_id={ctx.run_id}")



def start_server(host='0.0.0.0', port=5000):
    """启动开发服务器"""
    import uvicorn
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-m', '--mode', default='http')
    parser.add_argument('-p', '--port', type=int, default=5000)
    args = parser.parse_args()
    if args.mode == 'http':
        start_server(host='0.0.0.0', port=args.port)
