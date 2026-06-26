"""
工作量数据管理模块
================
1. 存储界面上所有计划/非计划工作量数据到 OC_WORKLOAD_DATA 表
2. 进入界面时检测源数据是否有更新，提示用户是否覆盖修改
3. 用户确认后覆盖，否则保留已修改数据
4. 根据工作量和班组排班，利用大模型进行智能预测

=== 数据流 ===
1. get_workload_data(): 读取 OC_WORKLOAD_DATA 表（无数据时从源初始化）
2. check_workload_updates(): 比较源数据与表数据的哈希
3. apply_source_updates(): 用户确认后，用源数据覆盖表数据
4. save_manual_edits(): 用户手动编辑后保存
5. predict_workload(): 调用大模型进行工作量预测
"""

import os
import json
import hashlib
import datetime
import uuid
from typing import Optional

# ========== 内存降级存储 ==========
_memory_data: dict[str, dict] = {}
_memory_hash: Optional[str] = None
_memory_prediction: Optional[dict] = None
_oracle_available: Optional[bool] = None


def _check_oracle() -> bool:
    """检查 Oracle 是否可达（缓存结果）"""
    global _oracle_available
    if _oracle_available is not None:
        return _oracle_available
    try:
        import oracledb
        host = os.getenv("ORACLE_HOST", "10.111.134.211")
        port = int(os.getenv("ORACLE_PORT", "1521"))
        service_name = os.getenv("ORACLE_SERVICE_NAME", "domsdb")
        user = os.getenv("ORACLE_USER", "DOMS_JADP")
        password = os.getenv("ORACLE_PASSWORD", "doms_jadp")
        conn = oracledb.connect(
            user=user, password=password,
            host=host, port=port, service_name=service_name,
            expire_time=5,
        )
        conn.close()
        _oracle_available = True
        return True
    except Exception as e:
        _oracle_available = False
        return False


def _get_oracle_conn():
    """获取 Oracle 连接"""
    from oracle_db import get_oracle_connection
    return get_oracle_connection()


def _make_data_key(wl_type: str, cat: str, field: str, date_str: str) -> str:
    return f"{wl_type}:{cat}:{field}:{date_str}"


def _compute_source_hash(plan_detail: dict, nonplan_detail: dict) -> str:
    """计算源数据的哈希值，用于检测是否变化"""
    raw = json.dumps({"plan": plan_detail, "nonplan": nonplan_detail}, sort_keys=True)
    return hashlib.md5(raw.encode()).hexdigest()


def _fetch_source_data(target_date: str) -> tuple[dict, dict]:
    """从原始数据源获取计划/非计划工作量数据"""
    from tools.scheduling import ScheduleDataProvider

    # 解析日期
    try:
        dt = datetime.datetime.strptime(target_date, "%Y-%m-%d").date()
    except Exception:
        dt = datetime.date.today()

    teams = ScheduleDataProvider.get_teams()
    records = ScheduleDataProvider.get_records(dt, dt)

    # --- 计划工作量 ---
    plan_detail = {
        "maintenance": {"in_progress": 8, "completed": 3, "total": 11, "count": 11},
        "transfer": {"in_progress": 5, "completed": 2, "total": 7, "count": 7},
        "equipment": {"in_progress": 4, "completed": 1, "total": 5, "count": 5},
        "weekly_plan": {"in_progress": 12, "completed": 6, "total": 18, "count": 18},
        "protect": {"in_progress": 6, "completed": 3, "total": 9, "count": 9},
    }

    # --- 非计划工作量 ---
    nonplan_detail = {
        "fault": {"count": 7},
        "defect": {"count": 3},
        "overload": {"count": 2},
    }

    return plan_detail, nonplan_detail


# ========== 公开 API ==========

def get_workload_data(target_date: str = None) -> dict:
    """
    获取工作量数据。
    1. 先查 OC_WORKLOAD_DATA 表
    2. 无数据时从源初始化
    3. 返回 { plan: {category: {fields}}, nonplan: {...}, source_hash: '...' }
    """
    if target_date is None:
        target_date = datetime.date.today().strftime("%Y-%m-%d")

    plan_detail, nonplan_detail = _fetch_source_data(target_date)
    current_hash = _compute_source_hash(plan_detail, nonplan_detail)

    # 尝试从 Oracle 读取
    if _check_oracle():
        try:
            conn = _get_oracle_conn()
            cursor = conn.cursor()

            # 查询所有记录
            cursor.execute("""
                SELECT WORKLOAD_TYPE, CATEGORY, FIELD_NAME, FIELD_VALUE, SOURCE_HASH, IS_MODIFIED
                FROM OC_WORKLOAD_DATA
                WHERE TARGET_DATE = :1
                ORDER BY WORKLOAD_TYPE, CATEGORY, FIELD_NAME
            """, [target_date])

            rows = cursor.fetchall()
            cursor.close()
            conn.close()

            if rows:
                # 有数据，还原
                plan_result = {}
                nonplan_result = {}
                stored_hash = None
                has_modifications = False

                for row in rows:
                    wl_type = row[0]
                    cat = row[1]
                    field = row[2]
                    val = int(row[3]) if row[3] else 0
                    h = row[4]
                    modified = row[5]

                    if h:
                        stored_hash = h
                    if modified == 'Y':
                        has_modifications = True

                    target_dict = plan_result if wl_type == 'plan' else nonplan_result
                    if cat not in target_dict:
                        target_dict[cat] = {}
                    target_dict[cat][field] = val

                # 补全缺失的 total/count
                for result_dict in [plan_result, nonplan_result]:
                    for cat, fields in result_dict.items():
                        if "in_progress" in fields and "completed" in fields:
                            if "total" not in fields:
                                fields["total"] = fields["in_progress"] + fields["completed"]
                            if "count" not in fields:
                                fields["count"] = fields["in_progress"] + fields["completed"]

                return {
                    "plan": plan_result,
                    "nonplan": nonplan_result,
                    "source_hash": stored_hash or current_hash,
                    "has_modifications": has_modifications,
                    "needs_update": stored_hash is not None and stored_hash != current_hash,
                }

        except Exception as e:
            print(f"[WorkloadManager] Oracle 读取失败: {e}")

    # 内存降级
    if _memory_data:
        plan_result = {k: v for k, v in _memory_data.get("plan", {}).items()}
        nonplan_result = {k: v for k, v in _memory_data.get("nonplan", {}).items()}
        stored_hash = _memory_hash
        return {
            "plan": plan_result,
            "nonplan": nonplan_result,
            "source_hash": stored_hash or current_hash,
            "has_modifications": _memory_data.get("has_modifications", False),
            "needs_update": stored_hash is not None and stored_hash != current_hash,
        }

    # 首次：用源数据初始化
    _init_workload_data(plan_detail, nonplan_detail, current_hash, target_date)

    return {
        "plan": plan_detail,
        "nonplan": nonplan_detail,
        "source_hash": current_hash,
        "has_modifications": False,
        "needs_update": False,
    }


def _init_workload_data(plan_detail: dict, nonplan_detail: dict, source_hash: str, target_date: str):
    """首次初始化工作量数据到存储"""
    global _memory_data, _memory_hash

    if _check_oracle():
        try:
            conn = _get_oracle_conn()
            cursor = conn.cursor()

            for wl_type, detail in [("plan", plan_detail), ("nonplan", nonplan_detail)]:
                for cat, fields in detail.items():
                    for field, val in fields.items():
                        data_id = str(uuid.uuid4()).replace("-", "")[:32]
                        cursor.execute("""
                            INSERT INTO OC_WORKLOAD_DATA
                            (DATA_ID, WORKLOAD_TYPE, CATEGORY, FIELD_NAME, FIELD_VALUE,
                             TARGET_DATE, SOURCE_HASH, IS_MODIFIED, CREATED_AT, UPDATED_AT)
                            VALUES (:1, :2, :3, :4, :5, :6, :7, 'N', SYSTIMESTAMP, SYSTIMESTAMP)
                        """, [data_id, wl_type, cat, field, int(val), target_date, source_hash])
            conn.commit()
            cursor.close()
            conn.close()
            return
        except Exception:
            pass

    # 内存降级
    _memory_data = {"plan": dict(plan_detail), "nonplan": dict(nonplan_detail)}
    _memory_hash = source_hash
    _memory_data["has_modifications"] = False


def check_workload_updates(target_date: str = None) -> dict:
    """
    检查源数据是否有更新。
    返回: { has_updates: bool, current_hash: str, stored_hash: str }
    """
    if target_date is None:
        target_date = datetime.date.today().strftime("%Y-%m-%d")

    plan_detail, nonplan_detail = _fetch_source_data(target_date)
    current_hash = _compute_source_hash(plan_detail, nonplan_detail)

    # 获取已存储的数据
    stored = get_workload_data(target_date)
    stored_hash = stored.get("source_hash")

    has_updates = (stored_hash is not None and stored_hash != current_hash)

    return {
        "has_updates": has_updates,
        "current_hash": current_hash,
        "stored_hash": stored_hash or "",
        "plan": plan_detail,
        "nonplan": nonplan_detail,
    }


def apply_source_updates(target_date: str = None) -> dict:
    """
    用户确认后，用新源数据覆盖工作量表。
    返回: { success: bool, plan: dict, nonplan: dict }
    """
    global _memory_data, _memory_hash

    if target_date is None:
        target_date = datetime.date.today().strftime("%Y-%m-%d")

    plan_detail, nonplan_detail = _fetch_source_data(target_date)
    current_hash = _compute_source_hash(plan_detail, nonplan_detail)

    if _check_oracle():
        try:
            conn = _get_oracle_conn()
            cursor = conn.cursor()

            # 删除旧数据
            cursor.execute("DELETE FROM OC_WORKLOAD_DATA WHERE TARGET_DATE = :1", [target_date])

            # 插入新数据
            for wl_type, detail in [("plan", plan_detail), ("nonplan", nonplan_detail)]:
                for cat, fields in detail.items():
                    for field, val in fields.items():
                        data_id = str(uuid.uuid4()).replace("-", "")[:32]
                        cursor.execute("""
                            INSERT INTO OC_WORKLOAD_DATA
                            (DATA_ID, WORKLOAD_TYPE, CATEGORY, FIELD_NAME, FIELD_VALUE,
                             TARGET_DATE, SOURCE_HASH, IS_MODIFIED, CREATED_AT, UPDATED_AT)
                            VALUES (:1, :2, :3, :4, :5, :6, :7, 'N', SYSTIMESTAMP, SYSTIMESTAMP)
                        """, [data_id, wl_type, cat, field, int(val), target_date, current_hash])

            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"[WorkloadManager] Oracle 更新失败: {e}")

    # 内存降级
    _memory_data = {"plan": dict(plan_detail), "nonplan": dict(nonplan_detail)}
    _memory_hash = current_hash
    _memory_data["has_modifications"] = False

    return {
        "success": True,
        "plan": plan_detail,
        "nonplan": nonplan_detail,
        "source_hash": current_hash,
    }


def save_manual_edits(workload_type: str, data: dict, target_date: str = None) -> bool:
    """
    保存用户手动编辑的数据。
    data 结构: { category: { field: value, ... }, ... }
    """
    global _memory_data, _memory_hash

    if target_date is None:
        target_date = datetime.date.today().strftime("%Y-%m-%d")

    if _check_oracle():
        try:
            conn = _get_oracle_conn()
            cursor = conn.cursor()

            for category, fields in data.items():
                for field_name, field_value in fields.items():
                    try:
                        cursor.execute("""
                            MERGE INTO OC_WORKLOAD_DATA t
                            USING (SELECT :1 AS wt, :2 AS cat, :3 AS fld, :4 AS dt FROM DUAL) s
                            ON (t.WORKLOAD_TYPE = s.wt AND t.CATEGORY = s.cat
                                AND t.FIELD_NAME = s.fld AND t.TARGET_DATE = s.dt)
                            WHEN MATCHED THEN
                                UPDATE SET FIELD_VALUE = :5, IS_MODIFIED = 'Y', UPDATED_AT = SYSTIMESTAMP
                            WHEN NOT MATCHED THEN
                                INSERT (DATA_ID, WORKLOAD_TYPE, CATEGORY, FIELD_NAME,
                                        FIELD_VALUE, TARGET_DATE, IS_MODIFIED, CREATED_AT, UPDATED_AT)
                                VALUES (:6, :1, :2, :3, :5, :4, 'Y', SYSTIMESTAMP, SYSTIMESTAMP)
                        """, [workload_type, category, field_name, target_date,
                              int(field_value), str(uuid.uuid4()).replace("-", "")[:32]])
                    except Exception:
                        pass

            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"[WorkloadManager] Oracle 保存失败: {e}")
            return False

    # 内存降级
    if workload_type not in _memory_data:
        _memory_data[workload_type] = {}
    _memory_data[workload_type].update(data)
    _memory_data["has_modifications"] = True

    return True


def predict_workload(target_date: str = None) -> dict:
    """
    根据工作量数据和班组排班数据，调用大模型预测工作量。
    返回: { prediction: str, model: str, cached: bool }
    """
    if target_date is None:
        target_date = datetime.date.today().strftime("%Y-%m-%d")

    # 检查缓存
    if _check_oracle():
        try:
            conn = _get_oracle_conn()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT PREDICTION_JSON, MODEL_USED FROM OC_WORKLOAD_PREDICTION
                WHERE TARGET_DATE = :1
            """, [target_date])
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            if row:
                return {
                    "prediction": json.loads(row[0]) if isinstance(row[0], str) else row[0],
                    "model": row[1],
                    "cached": True,
                }
        except Exception:
            pass

    # 获取当前工作量数据
    wl_data = get_workload_data(target_date)
    plan = wl_data.get("plan", {})
    nonplan = wl_data.get("nonplan", {})

    # 获取班组排班数据
    from tools.scheduling import ScheduleDataProvider
    try:
        dt = datetime.datetime.strptime(target_date, "%Y-%m-%d").date()
    except Exception:
        dt = datetime.date.today()
    teams = ScheduleDataProvider.get_teams()
    records = ScheduleDataProvider.get_records(dt, dt)

    # 构建预测请求
    team_info = []
    for t in teams:
        team_info.append(f"{t.team_name}(值班长:{t.team_leader_name}, {len(t.person_name_list)}人)")

    on_duty_shifts = []
    for r in records:
        if r.schedule_status == 'Y':
            on_duty_shifts.append(f"{r.team_name}:{r.shift_type}({r.on_duty_time})")

    # 调用大模型预测
    try:
        from coze_coding_dev_sdk import LLMClient
        from coze_coding_utils.runtime_ctx.context import new_context
        from langchain_core.messages import SystemMessage, HumanMessage

        ctx = new_context(method="predict_workload")
        client = LLMClient(ctx=ctx)

        system_prompt = """你是一个电网调度工作量预测专家。根据给定的工作量和班组数据，分析预测未来的工作量趋势。
请按 JSON 格式输出预测结果，包含以下字段：
- overall_trend: 总体趋势描述（一句话）
- peak_categories: 高峰工作类别列表
- bottleneck_teams: 可能超负荷的班组列表
- suggestions: 优化建议列表（3-5条）
- risk_level: 风险等级（low/medium/high）

只输出 JSON，不要附加其他文字。"""

        user_prompt = f"""日期：{target_date}

当前计划工作量：
{json.dumps(plan, ensure_ascii=False, indent=2)}

当前非计划工作量：
{json.dumps(nonplan, ensure_ascii=False, indent=2)}

当值班组：
{json.dumps(team_info, ensure_ascii=False, indent=2)}

当值排班：
{json.dumps(on_duty_shifts, ensure_ascii=False, indent=2)}

请根据以上数据分析预测工作量趋势，输出 JSON 格式预测结果。"""

        response = client.invoke(
            messages=[
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ],
            model="doubao-seed-2-0-lite-260215",
            temperature=0.3,
            max_completion_tokens=4096,
        )

        content = response.content
        if isinstance(content, list):
            content = " ".join(item.get("text", "") for item in content if isinstance(item, dict))

        # 提取 JSON
        prediction_text = content.strip()
        if "```json" in prediction_text:
            prediction_text = prediction_text.split("```json")[1].split("```")[0].strip()
        elif "```" in prediction_text:
            prediction_text = prediction_text.split("```")[1].split("```")[0].strip()

        try:
            prediction_json = json.loads(prediction_text)
        except json.JSONDecodeError:
            prediction_json = {"raw": prediction_text}

        model_used = "doubao-seed-2-0-lite-260215"

        # 缓存预测结果
        if _check_oracle():
            try:
                conn = _get_oracle_conn()
                cursor = conn.cursor()
                pred_id = str(uuid.uuid4()).replace("-", "")[:32]
                cursor.execute("""
                    MERGE INTO OC_WORKLOAD_PREDICTION t
                    USING (SELECT :1 AS dt FROM DUAL) s
                    ON (t.TARGET_DATE = s.dt)
                    WHEN MATCHED THEN
                        UPDATE SET PREDICTION_JSON = :2, MODEL_USED = :3, UPDATED_AT = SYSTIMESTAMP
                    WHEN NOT MATCHED THEN
                        INSERT (PREDICTION_ID, TARGET_DATE, PREDICTION_JSON, MODEL_USED, CREATED_AT, UPDATED_AT)
                        VALUES (:4, :1, :2, :3, SYSTIMESTAMP, SYSTIMESTAMP)
                """, [target_date, json.dumps(prediction_json, ensure_ascii=False), model_used, pred_id])
                conn.commit()
                cursor.close()
                conn.close()
            except Exception:
                pass

        return {
            "prediction": prediction_json,
            "model": model_used,
            "cached": False,
        }

    except Exception as e:
        return {
            "prediction": {
                "overall_trend": f"预测服务暂不可用: {str(e)}",
                "peak_categories": [],
                "bottleneck_teams": [],
                "suggestions": ["请稍后重试"],
                "risk_level": "unknown",
            },
            "model": "none",
            "cached": False,
        }


# 保留旧接口兼容
save_batch_overrides = lambda wl, data, date=None: save_manual_edits(wl, data, date)
load_overrides = lambda wl, date=None: {}
apply_overrides_to_details = lambda details, overrides: details