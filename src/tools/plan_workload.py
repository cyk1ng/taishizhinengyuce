"""
计划工作量统计模块 - 严格按照业务需求实现

功能：
1. 计划检修工作量统计
2. 转供电工作量统计
3. 设备投退工作量统计
4. 周计划工作量统计

时间段定义：
- 早班：08:00~14:00
- 中班：14:00~21:00
- 夜班：21:00~次日08:00

业务规则：
1. 计划检修、转供电、设备投退开展时间段为批准开始时间至批准结束时间
2. 计划工作数量均可手动更改
3. 根据时间段（早班、中班、夜班）分配工作量
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from langchain.tools import tool, ToolRuntime
from coze_coding_utils.runtime_ctx.context import new_context

# 配置日志
logger = logging.getLogger(__name__)


# ============================================================
# 数据库操作类
# ============================================================

class PlanWorkloadDatabase:
    """计划工作量数据库操作类"""
    
    @staticmethod
    def get_session():
        """获取数据库会话"""
        try:
            from storage.database.db import get_session, is_database_connected
            if is_database_connected():
                return get_session()
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
        return None
    
    @staticmethod
    def collect_maintenance_workload(target_date: str) -> List[Dict]:
        """
        采集计划检修工作量
        
        业务规则：
        1. 待执行-批准停电开始时间为当天 → 纳入统计
        2. 执行中-批准工作结束时间为当天（21:00后的也包括）→ 纳入统计
        3. 白天工作量 = 上述两项
        4. 批准工作结束时间为21:00后的工作量纳入夜班
        
        参数：
            target_date: 目标日期 (YYYY-MM-DD)
        
        返回：检修工作量记录列表
        """
        session = PlanWorkloadDatabase.get_session()
        if not session:
            logger.warning("数据库未连接，返回空列表")
            return []
        
        records = []
        
        try:
            from sqlalchemy import text
            
            # 查询计划检修记录
            # 1. 待执行且批准停电开始时间为当天
            # 2. 执行中且批准工作结束时间为当天（包括21:00后的）
            sql = text("""
                SELECT 
                    RECORD_ID as record_id,
                    WORK_ORDER_NO as work_order_no,
                    OPERATION_TYPE as operation_type,
                    ORDER_TYPE as order_type,
                    EQUIPMENT_NAME as equipment_name,
                    APPROVED_START_TIME as approved_start_time,
                    APPROVED_END_TIME as approved_end_time,
                    ACTUAL_START_TIME as actual_start_time,
                    ACTUAL_END_TIME as actual_end_time,
                    STATUS as status,
                    OPERATOR_NAME as operator_name,
                    CASE 
                        WHEN OPERATION_TYPE = 'power_off' AND ORDER_TYPE = 'phone' THEN 'A1_phone'
                        WHEN OPERATION_TYPE = 'power_off' AND ORDER_TYPE = 'network' THEN 'A1_network'
                        WHEN OPERATION_TYPE = 'power_on' AND ORDER_TYPE = 'phone' THEN 'A2_phone'
                        WHEN OPERATION_TYPE = 'power_on' AND ORDER_TYPE = 'network' THEN 'A2_network'
                    END as task_category,
                    CASE 
                        WHEN OPERATION_TYPE = 'power_off' THEN '停电' 
                        WHEN OPERATION_TYPE = 'power_on' THEN '复电' 
                    END as task_name
                FROM maintenance_records
                WHERE (
                    -- 待执行且批准停电开始时间为当天
                    (STATUS = 'pending' AND DATE(APPROVED_START_TIME) = :target_date)
                    OR
                    -- 执行中且批准工作结束时间为当天（包括21:00后的）
                    (STATUS = 'executing' AND DATE(APPROVED_END_TIME) = :target_date)
                )
                ORDER BY APPROVED_START_TIME
            """)
            
            result = session.execute(sql, {"target_date": target_date})
            for row in result:
                data = dict(row._mapping)
                records.append(data)
            
            logger.info(f"采集计划检修工作量 {len(records)} 条")
            
        except Exception as e:
            logger.error(f"采集计划检修工作量失败: {e}")
        finally:
            if session:
                session.close()
        
        return records
    
    @staticmethod
    def collect_equipment_workload(target_date: str) -> List[Dict]:
        """
        采集设备投退工作量
        
        业务规则：
        1. 待执行-批准工作开始时间为当天 → 纳入统计
        2. 执行中-批准工作结束时间为当天（21:00后的也包括）→ 纳入统计
        3. 白天工作量 = 上述两项
        4. 批准工作结束时间为21:00后的工作量纳入夜班
        
        参数：
            target_date: 目标日期 (YYYY-MM-DD)
        
        返回：设备投退工作量记录列表
        """
        session = PlanWorkloadDatabase.get_session()
        if not session:
            logger.warning("数据库未连接，返回空列表")
            return []
        
        records = []
        
        try:
            from sqlalchemy import text
            
            sql = text("""
                SELECT 
                    OPERATION_ID as record_id,
                    OPERATION_NO as operation_no,
                    OPERATION_TYPE as operation_type,
                    EQUIPMENT_NAME as equipment_name,
                    APPROVED_START_TIME as approved_start_time,
                    APPROVED_END_TIME as approved_end_time,
                    STATUS as status,
                    OPERATOR_NAME as operator_name,
                    'A6' as task_category,
                    '设备投退' as task_name
                FROM equipment_operations
                WHERE (
                    -- 待执行且批准开始时间为当天
                    (STATUS = 'pending' AND DATE(APPROVED_START_TIME) = :target_date)
                    OR
                    -- 执行中且批准结束时间为当天（包括21:00后的）
                    (STATUS = 'executing' AND DATE(APPROVED_END_TIME) = :target_date)
                )
                ORDER BY APPROVED_START_TIME
            """)
            
            result = session.execute(sql, {"target_date": target_date})
            for row in result:
                data = dict(row._mapping)
                records.append(data)
            
            logger.info(f"采集设备投退工作量 {len(records)} 条")
            
        except Exception as e:
            logger.error(f"采集设备投退工作量失败: {e}")
        finally:
            if session:
                session.close()
        
        return records
    
    @staticmethod
    def collect_transfer_workload(target_date: str) -> List[Dict]:
        """
        采集转供电工作量
        
        业务规则：
        1. 待执行-批准转出开始时间为当天 → 纳入统计
        2. 执行中-转出开始时间为当天（21:00后的不包括）→ 纳入统计
        3. 白天工作量 = 上述两项
        4. 批准转出开始时间为21:00至次日08:30的工作量纳入夜班
        
        参数：
            target_date: 目标日期 (YYYY-MM-DD)
        
        返回：转供电工作量记录列表
        """
        session = PlanWorkloadDatabase.get_session()
        if not session:
            logger.warning("数据库未连接，返回空列表")
            return []
        
        records = []
        
        try:
            from sqlalchemy import text
            
            sql = text("""
                SELECT 
                    ORDER_ID as record_id,
                    ORDER_NO as order_no,
                    TRANSFER_TYPE as transfer_type,
                    EQUIPMENT_NAME as equipment_name,
                    TRANSFER_OUT_TIME as transfer_out_time,
                    TRANSFER_BACK_TIME as transfer_back_time,
                    STATUS as status,
                    OPERATOR_NAME as operator_name,
                    'A3' as task_category,
                    '转供电' as task_name
                FROM transfer_orders
                WHERE (
                    -- 待执行且批准转出开始时间为当天
                    (STATUS = 'pending' AND DATE(TRANSFER_OUT_TIME) = :target_date)
                    OR
                    -- 执行中且转出开始时间为当天（21:00后的不包括）
                    (STATUS = 'executing' 
                     AND DATE(TRANSFER_OUT_TIME) = :target_date
                     AND HOUR(TRANSFER_OUT_TIME) < 21)
                )
                ORDER BY TRANSFER_OUT_TIME
            """)
            
            result = session.execute(sql, {"target_date": target_date})
            for row in result:
                data = dict(row._mapping)
                records.append(data)
            
            logger.info(f"采集转供电工作量 {len(records)} 条")
            
        except Exception as e:
            logger.error(f"采集转供电工作量失败: {e}")
        finally:
            if session:
                session.close()
        
        return records
    
    @staticmethod
    def collect_weekly_plan_workload(target_date: str) -> List[Dict]:
        """
        采集周计划工作量
        
        业务规则：
        1. 需自动读取批准工作开始时间为当天的所有周计划（包括跨天工作的周计划）
        2. 若提前分析当天三值工作量：将周计划总数纳入早班、中班时间段内考虑
        3. 夜班周计划工作量暂时以跨天工作的周计划总数为准
        
        参数：
            target_date: 目标日期 (YYYY-MM-DD)
        
        返回：周计划工作量记录列表
        """
        session = PlanWorkloadDatabase.get_session()
        if not session:
            logger.warning("数据库未连接，返回空列表")
            return []
        
        records = []
        
        try:
            from sqlalchemy import text
            
            # 查询批准工作开始时间为当天的所有周计划
            sql = text("""
                SELECT 
                    PLAN_ID as record_id,
                    PLAN_NO as plan_no,
                    PLAN_TYPE as plan_type,
                    PLAN_NAME as plan_name,
                    EQUIPMENT_NAME as equipment_name,
                    APPROVED_START_TIME as approved_start_time,
                    APPROVED_END_TIME as approved_end_time,
                    STATUS as status,
                    OPERATOR_NAME as operator_name,
                    IS_LIVE_COOP as is_live_coop,
                    CASE 
                        WHEN PLAN_TYPE = 'live_operation' THEN 'A4'
                        WHEN PLAN_TYPE = 'commissioning' THEN 'A5'
                        ELSE 'A4'
                    END as task_category,
                    CASE 
                        WHEN PLAN_TYPE = 'live_operation' THEN '周计划(只带电)'
                        WHEN PLAN_TYPE = 'commissioning' THEN '周计划(只投产)'
                        ELSE '周计划'
                    END as task_name,
                    -- 判断是否跨天
                    CASE 
                        WHEN DATE(APPROVED_START_TIME) != DATE(APPROVED_END_TIME) THEN 1
                        ELSE 0
                    END as is_cross_day,
                    -- 计算任务数量
                    CASE 
                        WHEN PLAN_TYPE = 'live_operation' AND IS_LIVE_COOP = 1 THEN 2  -- 带电配合投产
                        WHEN PLAN_TYPE = 'live_operation' THEN 1  -- 只带电
                        WHEN PLAN_TYPE = 'commissioning' AND IS_LIVE_COOP = 1 THEN 2  -- 投产配合带电
                        ELSE 1
                    END as task_count
                FROM weekly_plans
                WHERE STATUS = 'executing'
                  AND DATE(APPROVED_START_TIME) = :target_date
                ORDER BY APPROVED_START_TIME
            """)
            
            result = session.execute(sql, {"target_date": target_date})
            for row in result:
                data = dict(row._mapping)
                records.append(data)
            
            logger.info(f"采集周计划工作量 {len(records)} 条")
            
        except Exception as e:
            logger.error(f"采集周计划工作量失败: {e}")
        finally:
            if session:
                session.close()
        
        return records


# ============================================================
# 工作量分配类
# ============================================================

class WorkloadAllocator:
    """工作量按时间段分配"""
    
    # 时间段定义
    SHIFT_MORNING_START = 8   # 早班开始 08:00
    SHIFT_MORNING_END = 14    # 早班结束 14:00
    SHIFT_AFTERNOON_START = 14 # 中班开始 14:00
    SHIFT_AFTERNOON_END = 21   # 中班结束 21:00
    SHIFT_NIGHT_START = 21     # 夜班开始 21:00
    SHIFT_NIGHT_END = 32       # 夜班结束 次日08:00 (24+8)
    
    @staticmethod
    def determine_shift(hour: int) -> str:
        """判断所属班次"""
        if hour >= WorkloadAllocator.SHIFT_MORNING_START and hour < WorkloadAllocator.SHIFT_MORNING_END:
            return "morning"
        elif hour >= WorkloadAllocator.SHIFT_AFTERNOON_START and hour < WorkloadAllocator.SHIFT_AFTERNOON_END:
            return "afternoon"
        elif hour >= WorkloadAllocator.SHIFT_NIGHT_START or hour < 8:
            return "night"
        else:
            return "night"  # 默认夜班
    
    @staticmethod
    def allocate_maintenance_task(record: Dict) -> Dict:
        """
        分配计划检修任务工作量到各班次
        
        业务规则：
        1. 待执行-批准停电开始时间为当天 → 计入开始时间所属班次
        2. 执行中-批准工作结束时间为当天（21:00后的也包括）→ 计入结束时间所属班次
        3. 如果批准工作结束时间为21:00后，计入夜班
        """
        result = {
            "record_id": record["record_id"],
            "task_category": record["task_category"],
            "task_name": record["task_name"],
            "approved_start_time": record["approved_start_time"],
            "approved_end_time": record["approved_end_time"],
            "status": record["status"],
            "shift_allocation": {
                "morning": 0,
                "afternoon": 0,
                "night": 0
            },
            "total_count": 0
        }
        
        try:
            if record["status"] == "pending":
                # 待执行：根据批准开始时间分配
                start_time = record["approved_start_time"]
                if start_time:
                    hour = start_time.hour
                    shift = WorkloadAllocator.determine_shift(hour)
                    result["shift_allocation"][shift] = 1
                    result["total_count"] = 1
                    
            elif record["status"] == "executing":
                # 执行中：根据批准结束时间分配
                end_time = record["approved_end_time"]
                if end_time:
                    hour = end_time.hour
                    shift = WorkloadAllocator.determine_shift(hour)
                    result["shift_allocation"][shift] = 1
                    result["total_count"] = 1
                    
        except Exception as e:
            logger.error(f"分配检修任务失败: {e}")
        
        return result
    
    @staticmethod
    def allocate_equipment_task(record: Dict) -> Dict:
        """
        分配设备投退任务工作量到各班次
        
        业务规则：
        1. 待执行-批准工作开始时间为当天 → 计入开始时间所属班次
        2. 执行中-批准工作结束时间为当天（21:00后的也包括）→ 计入结束时间所属班次
        3. 如果批准工作结束时间为21:00后，计入夜班
        """
        result = {
            "record_id": record["record_id"],
            "task_category": record["task_category"],
            "task_name": record["task_name"],
            "approved_start_time": record["approved_start_time"],
            "approved_end_time": record["approved_end_time"],
            "status": record["status"],
            "shift_allocation": {
                "morning": 0,
                "afternoon": 0,
                "night": 0
            },
            "total_count": 0
        }
        
        try:
            if record["status"] == "pending":
                # 待执行：根据批准开始时间分配
                start_time = record["approved_start_time"]
                if start_time:
                    hour = start_time.hour
                    shift = WorkloadAllocator.determine_shift(hour)
                    result["shift_allocation"][shift] = 1
                    result["total_count"] = 1
                    
            elif record["status"] == "executing":
                # 执行中：根据批准结束时间分配
                end_time = record["approved_end_time"]
                if end_time:
                    hour = end_time.hour
                    shift = WorkloadAllocator.determine_shift(hour)
                    result["shift_allocation"][shift] = 1
                    result["total_count"] = 1
                    
        except Exception as e:
            logger.error(f"分配设备投退任务失败: {e}")
        
        return result
    
    @staticmethod
    def allocate_transfer_task(record: Dict) -> Dict:
        """
        分配转供电任务工作量到各班次
        
        业务规则：
        1. 待执行-批准转出开始时间为当天 → 计入转出开始时间所属班次
        2. 执行中-转出开始时间为当天（21:00后的不包括）→ 计入转出开始时间所属班次
        3. 批准转出开始时间为21:00至次日08:30的工作量纳入夜班
        """
        result = {
            "record_id": record["record_id"],
            "task_category": record["task_category"],
            "task_name": record["task_name"],
            "transfer_out_time": record["transfer_out_time"],
            "transfer_back_time": record["transfer_back_time"],
            "status": record["status"],
            "shift_allocation": {
                "morning": 0,
                "afternoon": 0,
                "night": 0
            },
            "total_count": 0
        }
        
        try:
            # 统一使用转出开始时间
            out_time = record["transfer_out_time"]
            if out_time:
                hour = out_time.hour
                shift = WorkloadAllocator.determine_shift(hour)
                result["shift_allocation"][shift] = 1
                result["total_count"] = 1
                
        except Exception as e:
            logger.error(f"分配转供电任务失败: {e}")
        
        return result
    
    @staticmethod
    def allocate_weekly_plan_task(record: Dict, pre_analyze: bool = False) -> Dict:
        """
        分配周计划任务工作量到各班次
        
        业务规则：
        1. 若提前分析当天三值工作量：将周计划总数纳入早班、中班时间段内考虑
        2. 夜班周计划工作量暂时以跨天工作的周计划总数为准
        
        参数：
            record: 周计划记录
            pre_analyze: 是否提前分析（影响分配策略）
        """
        result = {
            "record_id": record["record_id"],
            "task_category": record["task_category"],
            "task_name": record["task_name"],
            "approved_start_time": record["approved_start_time"],
            "approved_end_time": record["approved_end_time"],
            "is_cross_day": record.get("is_cross_day", 0),
            "task_count": record.get("task_count", 1),
            "shift_allocation": {
                "morning": 0,
                "afternoon": 0,
                "night": 0
            },
            "total_count": 0
        }
        
        try:
            if pre_analyze:
                # 提前分析：周计划总数纳入早班、中班
                # 简单分配：早班和中班平均分配
                count = record.get("task_count", 1)
                result["shift_allocation"]["morning"] = count // 2
                result["shift_allocation"]["afternoon"] = count - (count // 2)
                result["total_count"] = count
            else:
                # 正常分析：根据跨天情况分配
                is_cross_day = record.get("is_cross_day", 0)
                if is_cross_day == 1:
                    # 跨天工作：纳入夜班
                    count = record.get("task_count", 1)
                    result["shift_allocation"]["night"] = count
                    result["total_count"] = count
                else:
                    # 非跨天：根据批准开始时间分配
                    start_time = record["approved_start_time"]
                    if start_time:
                        hour = start_time.hour
                        shift = WorkloadAllocator.determine_shift(hour)
                        count = record.get("task_count", 1)
                        result["shift_allocation"][shift] = count
                        result["total_count"] = count
                        
        except Exception as e:
            logger.error(f"分配周计划任务失败: {e}")
        
        return result


# ============================================================
# 工具函数
# ============================================================

@tool
def calculate_plan_workload(
    target_date: str = "",
    pre_analyze: bool = False,
    runtime: ToolRuntime = None
) -> str:
    """
    计算计划工作量（按班次分配）
    
    功能：
    1. 采集计划检修、转供电、设备投退、周计划数据
    2. 按业务规则分配到早班、中班、夜班
    3. 支持提前分析模式（pre_analyze=True）
    
    参数：
    - target_date: 目标日期 (YYYY-MM-DD)，默认今天
    - pre_analyze: 是否提前分析（影响周计划分配策略）
    
    返回：计划工作量统计结果JSON字符串
    """
    ctx = runtime.context if runtime else new_context(method="calculate_plan_workload")
    
    try:
        if not target_date:
            target_date = datetime.now().strftime("%Y-%m-%d")
        
        # 1. 采集各类计划任务
        maintenance_records = PlanWorkloadDatabase.collect_maintenance_workload(target_date)
        equipment_records = PlanWorkloadDatabase.collect_equipment_workload(target_date)
        transfer_records = PlanWorkloadDatabase.collect_transfer_workload(target_date)
        weekly_plan_records = PlanWorkloadDatabase.collect_weekly_plan_workload(target_date)
        
        # 2. 分配工作量到各班次
        allocation_results = {
            "target_date": target_date,
            "pre_analyze": pre_analyze,
            "maintenance": [],
            "equipment": [],
            "transfer": [],
            "weekly_plan": [],
            "summary": {
                "morning": {"total_count": 0, "tasks": []},
                "afternoon": {"total_count": 0, "tasks": []},
                "night": {"total_count": 0, "tasks": []}
            }
        }
        
        # 2.1 分配检修任务
        for record in maintenance_records:
            allocated = WorkloadAllocator.allocate_maintenance_task(record)
            allocation_results["maintenance"].append(allocated)
            
            # 汇总
            for shift, count in allocated["shift_allocation"].items():
                if count > 0:
                    allocation_results["summary"][shift]["total_count"] += count
                    allocation_results["summary"][shift]["tasks"].append({
                        "category": allocated["task_category"],
                        "name": allocated["task_name"],
                        "count": count
                    })
        
        # 2.2 分配设备投退任务
        for record in equipment_records:
            allocated = WorkloadAllocator.allocate_equipment_task(record)
            allocation_results["equipment"].append(allocated)
            
            # 汇总
            for shift, count in allocated["shift_allocation"].items():
                if count > 0:
                    allocation_results["summary"][shift]["total_count"] += count
                    allocation_results["summary"][shift]["tasks"].append({
                        "category": allocated["task_category"],
                        "name": allocated["task_name"],
                        "count": count
                    })
        
        # 2.3 分配转供电任务
        for record in transfer_records:
            allocated = WorkloadAllocator.allocate_transfer_task(record)
            allocation_results["transfer"].append(allocated)
            
            # 汇总
            for shift, count in allocated["shift_allocation"].items():
                if count > 0:
                    allocation_results["summary"][shift]["total_count"] += count
                    allocation_results["summary"][shift]["tasks"].append({
                        "category": allocated["task_category"],
                        "name": allocated["task_name"],
                        "count": count
                    })
        
        # 2.4 分配周计划任务
        for record in weekly_plan_records:
            allocated = WorkloadAllocator.allocate_weekly_plan_task(record, pre_analyze=pre_analyze)
            allocation_results["weekly_plan"].append(allocated)
            
            # 汇总
            for shift, count in allocated["shift_allocation"].items():
                if count > 0:
                    allocation_results["summary"][shift]["total_count"] += count
                    allocation_results["summary"][shift]["tasks"].append({
                        "category": allocated["task_category"],
                        "name": allocated["task_name"],
                        "count": count,
                        "is_cross_day": record.get("is_cross_day", 0)
                    })
        
        # 3. 计算总计
        total_count = (
            allocation_results["summary"]["morning"]["total_count"] +
            allocation_results["summary"]["afternoon"]["total_count"] +
            allocation_results["summary"]["night"]["total_count"]
        )
        
        allocation_results["summary"]["total_count"] = total_count
        allocation_results["summary"]["record_counts"] = {
            "maintenance": len(maintenance_records),
            "equipment": len(equipment_records),
            "transfer": len(transfer_records),
            "weekly_plan": len(weekly_plan_records)
        }
        
        return json.dumps({
            "success": True,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data": allocation_results
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"计算计划工作量失败: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "计算计划工作量失败"
        }, ensure_ascii=False)
