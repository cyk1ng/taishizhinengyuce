"""
计划工作量统计模块 - 支持手动修改和历史数据自动填写

功能：
1. 计划检修工作量统计（支持手动修改）
2. 转供电工作量统计（支持手动修改）
3. 设备投退工作量统计（支持手动修改）
4. 周计划工作量统计（支持手动修改）

业务规则（新增）：
1. 计划工作数量均可手动更改
2. 基于历史数据自动填写，人工核对后可手动修改
3. 数据反馈：手动修改后返回智能体训练

时间段定义：
- 早班：08:00~14:00
- 中班：14:00~21:00
- 夜班：21:00~次日08:00

业务规则（更新）：
1. 计划检修/设备投退：
   - 若预测当天三值工作量：
     - 批准工作结束时间为21:00前的总数纳入早班、中班时间段内考虑
     - 批准工作结束时间为21:00后的纳入夜班考虑

2. 转供电：
   - 若预测当天三值工作量：
     - 计划转出开始时间为21:00前的总数纳入早班、中班时间段内考虑
     - 批准转出开始时间为21:00至次日08:30的纳入夜班考虑

3. 周计划：
   - 当天批准时间段0:00-23:59状态为执行中的为周计划数量
   - 若预测当天三值工作量：
     - 将周计划总数纳入早班、中班时间段内考虑
     - 夜班周计划工作量暂时忽略不计
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from langchain.tools import tool, ToolRuntime
from coze_coding_utils.runtime_ctx.context import new_context

# 配置日志
logger = logging.getLogger(__name__)


# ============================================================
# 手动修改数据管理
# ============================================================

class ManualWorkloadData:
    """手动修改的工作量数据管理"""
    
    # 存储手动修改的数据
    _manual_adjustments: Dict[str, Dict] = {}
    
    @classmethod
    def load_manual_data(cls, target_date: str) -> Optional[Dict]:
        """加载手动修改的数据"""
        return cls._manual_adjustments.get(target_date)
    
    @classmethod
    def save_manual_data(cls, target_date: str, data: Dict):
        """保存手动修改的数据"""
        cls._manual_adjustments[target_date] = data
        logger.info(f"已保存 {target_date} 的手动修改数据")
    
    @classmethod
    def apply_manual_adjustments(cls, allocation_result: Dict) -> Dict:
        """应用手动修改"""
        target_date = allocation_result.get("target_date")
        if not target_date:
            return allocation_result
        
        manual_data = cls.load_manual_data(target_date)
        if not manual_data:
            return allocation_result
        
        # 应用手动修改
        logger.info(f"应用 {target_date} 的手动修改")
        allocation_result["manual_adjustments_applied"] = True
        allocation_result["manual_adjustments"] = manual_data
        
        # 更新班次分配
        for shift in ["morning", "afternoon", "night"]:
            if shift in manual_data:
                allocation_result["summary"][shift]["total_count"] = manual_data[shift].get("total_count", 0)
                allocation_result["summary"][shift]["manual_override"] = True
        
        return allocation_result


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
        
        业务规则（更新）：
        - 若预测当天三值工作量：
          - 批准工作结束时间为21:00前的总数纳入早班、中班时间段内考虑
          - 批准工作结束时间为21:00后的纳入夜班考虑
        
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
            sql = text("""
                SELECT 
                    RECORD_ID as record_id,
                    WORK_ORDER_NO as work_order_no,
                    OPERATION_TYPE as operation_type,
                    ORDER_TYPE as order_type,
                    EQUIPMENT_NAME as equipment_name,
                    APPROVED_START_TIME as approved_start_time,
                    APPROVED_END_TIME as approved_end_time,
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
                    END as task_name,
                    -- 判断是否跨夜班（21:00后结束）
                    CASE 
                        WHEN HOUR(APPROVED_END_TIME) >= 21 THEN 1
                        ELSE 0
                    END as is_night_shift
                FROM maintenance_records
                WHERE DATE(APPROVED_START_TIME) = :target_date
                  OR DATE(APPROVED_END_TIME) = :target_date
                ORDER BY APPROVED_END_TIME
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
        
        业务规则（更新）：
        - 若预测当天三值工作量：
          - 批准工作结束时间为21:00前的总数纳入早班、中班时间段内考虑
          - 批准工作结束时间为21:00后的纳入夜班考虑
        
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
                    '设备投退' as task_name,
                    -- 判断是否跨夜班（21:00后结束）
                    CASE 
                        WHEN HOUR(APPROVED_END_TIME) >= 21 THEN 1
                        ELSE 0
                    END as is_night_shift
                FROM equipment_operations
                WHERE DATE(APPROVED_START_TIME) = :target_date
                  OR DATE(APPROVED_END_TIME) = :target_date
                ORDER BY APPROVED_END_TIME
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
        
        业务规则（更新）：
        - 若预测当天三值工作量：
          - 计划转出开始时间为21:00前的总数纳入早班、中班时间段内考虑
          - 批准转出开始时间为21:00至次日08:30的纳入夜班考虑
        
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
                    '转供电' as task_name,
                    -- 判断是否跨夜班（21:00至次日08:30）
                    CASE 
                        WHEN HOUR(TRANSFER_OUT_TIME) >= 21 OR HOUR(TRANSFER_OUT_TIME) < 8 THEN 1
                        ELSE 0
                    END as is_night_shift
                FROM transfer_orders
                WHERE DATE(TRANSFER_OUT_TIME) = :target_date
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
        
        业务规则（更新）：
        1. 需自动读取批准工作开始时间为当天的所有周计划（包括跨天工作的周计划）
        2. 当天批准时间段0:00-23:59状态为执行中的为周计划数量
        3. 若预测当天三值工作量：
           - 将周计划总数纳入早班、中班时间段内考虑
           - 夜班周计划工作量暂时忽略不计
        
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
            
            # 查询当天批准时间段0:00-23:59状态为执行中的周计划
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
# 工作量分配类（更新）
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
        分配计划检修任务工作量到各班次（更新规则）
        
        业务规则（更新）：
        - 若预测当天三值工作量：
          - 批准工作结束时间为21:00前的总数纳入早班、中班时间段内考虑
          - 批准工作结束时间为21:00后的纳入夜班考虑
        
        注意：只看批准结束时间，不看开始时间
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
            # 根据批准结束时间分配
            end_time = record["approved_end_time"]
            if end_time:
                hour = end_time.hour
                
                # 新规则：21:00前纳入早班、中班；21:00后纳入夜班
                if hour < 21:
                    # 21:00前，分配到早班或中班（根据实际结束时间）
                    shift = WorkloadAllocator.determine_shift(hour)
                    result["shift_allocation"][shift] = 1
                    result["total_count"] = 1
                else:
                    # 21:00后，纳入夜班
                    result["shift_allocation"]["night"] = 1
                    result["total_count"] = 1
                    
        except Exception as e:
            logger.error(f"分配检修任务失败: {e}")
        
        return result
    
    @staticmethod
    def allocate_equipment_task(record: Dict) -> Dict:
        """
        分配设备投退任务工作量到各班次（更新规则）
        
        业务规则（更新）：
        - 若预测当天三值工作量：
          - 批准工作结束时间为21:00前的总数纳入早班、中班时间段内考虑
          - 批准工作结束时间为21:00后的纳入夜班考虑
        
        注意：只看批准结束时间，不看开始时间
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
            # 根据批准结束时间分配
            end_time = record["approved_end_time"]
            if end_time:
                hour = end_time.hour
                
                # 新规则：21:00前纳入早班、中班；21:00后纳入夜班
                if hour < 21:
                    shift = WorkloadAllocator.determine_shift(hour)
                    result["shift_allocation"][shift] = 1
                    result["total_count"] = 1
                else:
                    result["shift_allocation"]["night"] = 1
                    result["total_count"] = 1
                    
        except Exception as e:
            logger.error(f"分配设备投退任务失败: {e}")
        
        return result
    
    @staticmethod
    def allocate_transfer_task(record: Dict) -> Dict:
        """
        分配转供电任务工作量到各班次（更新规则）
        
        业务规则（更新）：
        - 若预测当天三值工作量：
          - 计划转出开始时间为21:00前的总数纳入早班、中班时间段内考虑
          - 批准转出开始时间为21:00至次日08:30的纳入夜班考虑
        
        注意：只看转出开始时间
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
            # 统一使用转出开始时间分配
            out_time = record["transfer_out_time"]
            if out_time:
                hour = out_time.hour
                
                # 新规则：21:00前纳入早班、中班；21:00至次日08:30纳入夜班
                if hour < 21:
                    shift = WorkloadAllocator.determine_shift(hour)
                    result["shift_allocation"][shift] = 1
                    result["total_count"] = 1
                else:
                    # 21:00至次日08:30纳入夜班
                    result["shift_allocation"]["night"] = 1
                    result["total_count"] = 1
                    
        except Exception as e:
            logger.error(f"分配转供电任务失败: {e}")
        
        return result
    
    @staticmethod
    def allocate_weekly_plan_task(record: Dict, pre_analyze: bool = False) -> Dict:
        """
        分配周计划任务工作量到各班次（更新规则）
        
        业务规则（更新）：
        - 若预测当天三值工作量（pre_analyze=True）：
          - 将周计划总数纳入早班、中班时间段内考虑
          - 夜班周计划工作量暂时忽略不计
        - 正常模式（pre_analyze=False）：
          - 根据批准开始时间分配到对应班次
          - 夜班周计划工作量暂时忽略不计
        """
        result = {
            "record_id": record["record_id"],
            "task_category": record["task_category"],
            "task_name": record["task_name"],
            "approved_start_time": record["approved_start_time"],
            "approved_end_time": record["approved_end_time"],
            "task_count": record.get("task_count", 1),
            "shift_allocation": {
                "morning": 0,
                "afternoon": 0,
                "night": 0
            },
            "total_count": 0
        }
        
        try:
            count = record.get("task_count", 1)
            
            if pre_analyze:
                # 提前分析：周计划总数纳入早班、中班，夜班忽略
                # 简单分配：早班和中班平均分配
                result["shift_allocation"]["morning"] = count // 2
                result["shift_allocation"]["afternoon"] = count - (count // 2)
                result["shift_allocation"]["night"] = 0  # 夜班忽略
                result["total_count"] = count
            else:
                # 正常分析：根据批准开始时间分配，夜班忽略
                start_time = record["approved_start_time"]
                if start_time:
                    hour = start_time.hour
                    # 只分配到早班或中班，夜班忽略
                    if 8 <= hour < 14:
                        result["shift_allocation"]["morning"] = count
                    elif 14 <= hour < 21:
                        result["shift_allocation"]["afternoon"] = count
                    # 夜班忽略
                    
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
    计算计划工作量（按班次分配，支持手动修改）
    
    功能：
    1. 采集计划检修、转供电、设备投退、周计划数据
    2. 按业务规则分配到早班、中班、夜班
    3. 支持提前分析模式（pre_analyze=True）
    4. 支持手动修改后的数据加载
    
    业务规则（更新）：
    1. 计划检修/设备投退：
       - 批准工作结束时间为21:00前的总数纳入早班、中班
       - 批准工作结束时间为21:00后的纳入夜班
    
    2. 转供电：
       - 计划转出开始时间为21:00前的总数纳入早班、中班
       - 批准转出开始时间为21:00至次日08:30的纳入夜班
    
    3. 周计划：
       - 将周计划总数纳入早班、中班
       - 夜班周计划工作量暂时忽略不计
    
    参数：
    - target_date: 目标日期 (YYYY-MM-DD)，默认今天
    - pre_analyze: 是否提前分析（影响分配策略）
    
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
            "manual_adjustments_applied": False,
            "maintenance": [],
            "equipment": [],
            "transfer": [],
            "weekly_plan": [],
            "summary": {
                "morning": {"total_count": 0, "tasks": [], "manual_override": False},
                "afternoon": {"total_count": 0, "tasks": [], "manual_override": False},
                "night": {"total_count": 0, "tasks": [], "manual_override": False}
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
                        "count": count,
                        "record_id": allocated["record_id"]
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
                        "count": count,
                        "record_id": allocated["record_id"]
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
                        "count": count,
                        "record_id": allocated["record_id"]
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
                        "record_id": allocated["record_id"]
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
        
        # 4. 应用手动修改（如果有）
        allocation_results = ManualWorkloadData.apply_manual_adjustments(allocation_results)
        
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


@tool
def manual_adjust_plan_workload(
    target_date: str,
    morning_count: int,
    afternoon_count: int,
    night_count: int,
    feedback_data: Dict = None,
    runtime: ToolRuntime = None
) -> str:
    """
    手动修改计划工作量，并反馈数据用于智能体训练
    
    功能：
    1. 手动修改各班次的工作量数量
    2. 保存手动修改的数据
    3. 反馈数据用于智能体训练
    
    参数：
    - target_date: 目标日期 (YYYY-MM-DD)
    - morning_count: 早班工作量数量
    - afternoon_count: 中班工作量数量
    - night_count: 夜班工作量数量
    - feedback_data: 反馈数据（包含修改原因、实际数据等），用于智能体训练
    
    返回：操作结果JSON字符串
    """
    ctx = runtime.context if runtime else new_context(method="manual_adjust_plan_workload")
    
    try:
        # 准备手动修改数据
        manual_data = {
            "morning": {
                "total_count": morning_count,
                "adjusted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            "afternoon": {
                "total_count": afternoon_count,
                "adjusted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            "night": {
                "total_count": night_count,
                "adjusted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            "feedback": feedback_data or {}
        }
        
        # 保存手动修改数据
        ManualWorkloadData.save_manual_data(target_date, manual_data)
        
        # 返回成功结果
        return json.dumps({
            "success": True,
            "message": f"已保存 {target_date} 的手动修改数据",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data": {
                "target_date": target_date,
                "manual_data": manual_data,
                "ready_for_training": True  # 标记为可用于智能体训练
            }
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"手动修改计划工作量失败: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "手动修改计划工作量失败"
        }, ensure_ascii=False)


@tool
def get_manual_adjustments(target_date: str, runtime: ToolRuntime = None) -> str:
    """
    获取指定日期的手动修改数据
    
    参数：
    - target_date: 目标日期 (YYYY-MM-DD)
    
    返回：手动修改数据JSON字符串
    """
    ctx = runtime.context if runtime else new_context(method="get_manual_adjustments")
    
    try:
        manual_data = ManualWorkloadData.load_manual_data(target_date)
        
        if manual_data:
            return json.dumps({
                "success": True,
                "target_date": target_date,
                "has_manual_adjustments": True,
                "data": manual_data
            }, ensure_ascii=False, indent=2)
        else:
            return json.dumps({
                "success": True,
                "target_date": target_date,
                "has_manual_adjustments": False,
                "message": "该日期无手动修改数据"
            }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"获取手动修改数据失败: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "获取手动修改数据失败"
        }, ensure_ascii=False)
