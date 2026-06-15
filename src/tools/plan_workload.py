"""
计划工作量统计模块 - 更新版（基于最新需求）

功能：
1. 计划检修工作量统计（支持开展中、已终结分类）
2. 转供电工作量统计（支持开展中、已终结分类）
3. 设备投退工作量统计（支持开展中、已终结分类）
4. 周计划工作量统计（支持开展中、已终结分类）

数据来源（最新需求）：
1. 计划检修、转供电、设备投退：根据往年历史数据自动填写，人工核对后手动修改
2. 周计划：自动读取当天的总数（状态为执行中的）

业务规则（最新）：
1. 所有计划工作数量均可手动更改
2. 计划工作量分为：开展中、已终结
3. 基于历史数据自动填写，人工核对后可手动修改
4. 数据反馈：手动修改后返回智能体训练

时间段定义：
- 早班：08:00~14:00
- 中班：14:00~21:00
- 夜班：21:00~次日08:00

计划工作量业务规则（最新）：
1. 计划检修（以批准停电开始时间为准查询）：
   - 数据来源：电网管理平台-综合停电管理-配网停电申请-查询
   - 查询条件：以批准停电开始时间为准
   - 若预测当天三值工作量：
     - 批准工作结束时间为21:00前的总数纳入早班、中班
     - 批准工作结束时间为21:00后的纳入夜班
   - 支持开展中、已终结分类

2. 设备投退（以批准停电开始时间为准查询）：
   - 数据来源：电网管理平台-综合停电管理-配网停电申请-查询
   - 查询条件：以批准停电开始时间为准
   - 若预测当天三值工作量：
     - 批准工作结束时间为21:00前的总数纳入早班、中班
     - 批准工作结束时间为21:00后的纳入夜班
   - 支持开展中、已终结分类

3. 转供电（以计划转出开始时间为准查询）：
   - 数据来源：电网管理平台-运行方式管理-配网方式转供电管理-查询
   - 查询条件：以计划转出开始时间为准
   - 若预测当天三值工作量：
     - 计划转出开始时间为21:00前的总数纳入早班、中班
     - 批准转出开始时间为21:00至次日08:30的纳入夜班
   - 支持开展中、已终结分类

4. 周计划：
   - 数据来源：配网OMS系统-周计划管理流程-筛选工作时间
   - 查询条件：当天批准时间段0:00-23:59状态为执行中的为周计划数量
   - 若预测当天三值工作量：
     - 将周计划总数纳入早班、中班时间段内考虑
     - 夜班周计划工作量暂时忽略不计
   - 支持开展中、已终结分类
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from langchain.tools import tool
from coze_coding_utils.runtime_ctx.context import new_context

# 配置日志
logger = logging.getLogger(__name__)


# ============================================================
# 常量定义
# ============================================================

# 状态常量
STATUS_IN_PROGRESS = ["pending", "executing", "in_progress", "待执行", "执行中"]
STATUS_COMPLETED = ["completed", "finished", "terminated", "terminated", "已终结", "已完成"]
STATUS_NOT_HANDED_OVER = ["not_handed_over", "unhanded", "未交班"]
STATUS_HANDED_OVER = ["handed_over", "handed", "已交班"]

# 时间段定义
SHIFT_MORNING_START = 8   # 早班开始 08:00
SHIFT_MORNING_END = 14    # 早班结束 14:00
SHIFT_AFTERNOON_START = 14 # 中班开始 14:00
SHIFT_AFTERNOON_END = 21   # 中班结束 21:00
SHIFT_NIGHT_START = 21     # 夜班开始 21:00
SHIFT_NIGHT_END = 32       # 夜班结束 次日08:00 (24+8)


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
    def collect_maintenance_workload(target_date: Optional[str] = None) -> List[Dict]:
        """
        采集计划检修工作量
        
        业务规则（最新）：
        - 数据来源：电网管理平台-综合停电管理-配网停电申请-查询
        - 查询条件：以批准停电开始时间为准
        - 若预测当天三值工作量：
          - 批准工作结束时间为21:00前的总数纳入早班、中班
          - 批准工作结束时间为21:00后的纳入夜班
        - 支持开展中、已终结分类
        
        参数：
            target_date: 目标日期 (YYYY-MM-DD)，为空时查询所有记录
        
        返回：检修工作量记录列表
        """
        session = PlanWorkloadDatabase.get_session()
        if not session:
            logger.warning("数据库未连接，返回空列表")
            return []
        
        records = []
        
        try:
            from sqlalchemy import text
            
            # 查询计划检修记录（以批准停电开始时间为准查询）
            sql = text("""
                SELECT 
                    MK_ID as record_id,
                    FILL_PLAN_CODE as work_order_no,
                    FILL_OVERHAUL_TYPE as operation_type,
                    'phone' as order_type,
                    FILL_WORK_BEGIN_DATE as approved_start_time,
                    FILL_WORK_END_DATE as approved_end_time,
                    FORM_STATUS as status,
                    -- 判断任务类别：计划检修=停电
                    'A1_phone' as task_category,
                    '停电' as task_name,
                    -- 判断状态分类
                    --   DJS/DZX/ZX/RB = 开展中
                    --   ZJ/ZF/RC/CL = 已终结
                    CASE 
                        WHEN FORM_STATUS IN ('DJS', 'DZX', 'ZX', 'RB') THEN 'in_progress'
                        WHEN FORM_STATUS IN ('ZJ', 'ZF', 'RC', 'CL') THEN 'completed'
                        ELSE 'unknown'
                    END as status_category,
                    -- 判断是否跨夜班（21:00后结束）
                    CASE 
                        WHEN EXTRACT(HOUR FROM FILL_WORK_END_DATE) >= 21 THEN 1
                        ELSE 0
                    END as is_night_shift
                FROM TD_OUTAGE_REPAIR_APPLY_INFO
                WHERE FILL_OVERHAUL_TYPE IN ('JH', '计划检修')
                ORDER BY FILL_WORK_BEGIN_DATE
            """)
            
            params = {"target_date": target_date} if target_date else {}
            result = session.execute(sql, params)
            for row in result:
                data = dict(row._mapping)
                records.append(data)
            
            logger.info(f"采集计划检修工作量 {len(records)} 条（以批准开始时间为准查询）")
            
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
        
        业务规则（最新）：
        - 数据来源：电网管理平台-综合停电管理-配网停电申请-查询
        - 查询条件：以批准停电开始时间为准
        - 若预测当天三值工作量：
          - 批准工作结束时间为21:00前的总数纳入早班、中班
          - 批准工作结束时间为21:00后的纳入夜班
        - 支持开展中、已终结分类
        
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
            
            # 查询设备投退记录（以批准开始时间为准查询）
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
                    -- 判断状态分类
                    CASE 
                        WHEN STATUS IN ('pending', 'executing', 'in_progress', '待执行', '执行中') THEN 'in_progress'
                        WHEN STATUS IN ('completed', 'finished', 'terminated', '已终结', '已完成') THEN 'completed'
                        ELSE 'unknown'
                    END as status_category,
                    -- 判断是否跨夜班（21:00后结束）
                    CASE 
                        WHEN HOUR(APPROVED_END_TIME) >= 21 THEN 1
                        ELSE 0
                    END as is_night_shift
                FROM equipment_operations
                WHERE DATE(APPROVED_START_TIME) = :target_date
                ORDER BY APPROVED_START_TIME
            """)
            
            result = session.execute(sql, {"target_date": target_date})
            for row in result:
                data = dict(row._mapping)
                records.append(data)
            
            logger.info(f"采集设备投退工作量 {len(records)} 条（以批准开始时间为准查询）")
            
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
        
        业务规则（最新）：
        - 数据来源：电网管理平台-运行方式管理-配网方式转供电管理-查询
        - 查询条件：以计划转出开始时间为准
        - 若预测当天三值工作量：
          - 计划转出开始时间为21:00前的总数纳入早班、中班
          - 批准转出开始时间为21:00至次日08:30的纳入夜班
        - 支持开展中、已终结分类
        
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
            
            # 查询转供电记录（以计划转出开始时间为准查询）
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
                    -- 判断状态分类
                    CASE 
                        WHEN STATUS IN ('pending', 'executing', 'in_progress', '待执行', '执行中') THEN 'in_progress'
                        WHEN STATUS IN ('completed', 'finished', 'terminated', '已终结', '已完成') THEN 'completed'
                        ELSE 'unknown'
                    END as status_category,
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
            
            logger.info(f"采集转供电工作量 {len(records)} 条（以计划转出开始时间为准查询）")
            
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
        
        业务规则（最新）：
        - 数据来源：配网OMS系统-周计划管理流程-筛选工作时间
        - 查询条件：当天批准时间段0:00-23:59状态为执行中的为周计划数量
        - 若预测当天三值工作量：
           - 将周计划总数纳入早班、中班时间段内考虑
           - 夜班周计划工作量暂时忽略不计
        - 支持开展中、已终结分类
        
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
            
            # 查询当天批准时间段0:00-23:59状态为执行中的周计划数量
            # 查询条件：批准开始时间在目标日期的00:00-23:59之间，且状态为执行中
            sql = text("""
                SELECT 
                    COUNT(*) as task_count,
                    -- 统计开展中数量（状态为执行中）
                    SUM(CASE 
                        WHEN STATUS IN ('executing', 'in_progress', '执行中') THEN 1 
                        ELSE 0 
                    END) as in_progress_count,
                    -- 统计已终结数量
                    SUM(CASE 
                        WHEN STATUS IN ('completed', 'finished', 'terminated', '已终结', '已完成') THEN 1 
                        ELSE 0 
                    END) as completed_count,
                    -- 统计跨天工作数量
                    SUM(CASE 
                        WHEN DATE(APPROVED_START_TIME) != DATE(APPROVED_END_TIME) THEN 1 
                        ELSE 0 
                    END) as cross_day_count
                FROM weekly_plans
                WHERE DATE(APPROVED_START_TIME) = :target_date
                    AND STATUS IN ('executing', 'in_progress', '执行中')
            """)
            
            result = session.execute(sql, {"target_date": target_date})
            row = result.fetchone()
            
            if row:
                # 返回统计结果
                records = [{
                    "task_count": row.task_count or 0,
                    "in_progress_count": row.in_progress_count or 0,
                    "completed_count": row.completed_count or 0,
                    "cross_day_count": row.cross_day_count or 0,
                    "task_category": "A4",
                    "task_name": "周计划",
                    "target_date": target_date
                }]
            
            logger.info(f"采集周计划工作量统计: 总数={records[0]['task_count'] if records else 0}, 开展中={records[0]['in_progress_count'] if records else 0}, 已终结={records[0]['completed_count'] if records else 0}")
            
        except Exception as e:
            logger.error(f"采集周计划工作量失败: {e}")
        finally:
            if session:
                session.close()
        
        return records


# ============================================================
# 非计划工作量数据库操作类
# ============================================================

class NonPlanWorkloadDatabase:
    """非计划工作量数据库操作类"""
    
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
    def collect_fault_workload(target_date: str) -> List[Dict]:
        """
        采集故障日志工作量
        
        业务规则（最新）：
        - 前三天未交班的故障单数
        
        参数：
            target_date: 目标日期 (YYYY-MM-DD)
        
        返回：故障日志记录列表
        """
        session = NonPlanWorkloadDatabase.get_session()
        if not session:
            logger.warning("数据库未连接，返回空列表")
            return []
        
        records = []
        
        try:
            from sqlalchemy import text
            
            # 计算前三天的日期范围
            target_dt = datetime.strptime(target_date, "%Y-%m-%d")
            three_days_ago = target_dt - timedelta(days=3)
            
            # 查询前三天未交班的故障单
            sql = text("""
                SELECT 
                    FAULT_ID as record_id,
                    FAULT_NO as fault_no,
                    FAULT_TYPE as fault_type,
                    EQUIPMENT_NAME as equipment_name,
                    FAULT_TIME as fault_time,
                    EXPECTED_RESTORE_TIME as expected_restore_time,
                    STATUS as status,
                    HANDOVER_STATUS as handover_status,
                    OPERATOR_NAME as operator_name,
                    CASE 
                        WHEN FAULT_TYPE = 'success' THEN '跳闸重合成功'
                        WHEN FAULT_TYPE = 'fail_known' THEN '跳闸重合不成功(确定故障)'
                        WHEN FAULT_TYPE = 'fail_unknown' THEN '跳闸重合不成功(不确定故障)'
                        WHEN FAULT_TYPE = 'bus_ground' THEN '母线接地'
                        ELSE '故障'
                    END as task_name,
                    -- 判断是否未交班
                    CASE 
                        WHEN HANDOVER_STATUS IN ('not_handed_over', 'unhanded', '未交班') THEN 1
                        ELSE 0
                    END as is_not_handed_over
                FROM fault_logs
                WHERE (FAULT_TIME >= :start_date AND FAULT_TIME <= :end_date)
                  AND HANDOVER_STATUS IN ('not_handed_over', 'unhanded', '未交班')
                ORDER BY FAULT_TIME
            """)
            
            result = session.execute(sql, {
                "start_date": three_days_ago.strftime("%Y-%m-%d"),
                "end_date": target_date
            })
            for row in result:
                data = dict(row._mapping)
                records.append(data)
            
            logger.info(f"采集故障日志工作量 {len(records)} 条")
            
        except Exception as e:
            logger.error(f"采集故障日志工作量失败: {e}")
        finally:
            if session:
                session.close()
        
        return records
    
    @staticmethod
    def collect_defect_workload(target_date: str) -> List[Dict]:
        """
        采集异常缺陷工作量
        
        业务规则（最新）：
        - 当值记录未交班的所有缺陷单数
        
        参数：
            target_date: 目标日期 (YYYY-MM-DD)
        
        返回：异常缺陷记录列表
        """
        session = NonPlanWorkloadDatabase.get_session()
        if not session:
            logger.warning("数据库未连接，返回空列表")
            return []
        
        records = []
        
        try:
            from sqlalchemy import text
            
            # 查询当值记录未交班的缺陷单
            sql = text("""
                SELECT 
                    DEFECT_ID as record_id,
                    DEFECT_NO as defect_no,
                    DEFECT_TYPE as defect_type,
                    EQUIPMENT_NAME as equipment_name,
                    FAULT_TIME as fault_time,
                    EXPECTED_RESTORE_TIME as expected_restore_time,
                    STATUS as status,
                    HANDOVER_STATUS as handover_status,
                    OPERATOR_NAME as operator_name,
                    '异常缺陷' as task_name,
                    -- 判断是否未交班
                    CASE 
                        WHEN HANDOVER_STATUS IN ('not_handed_over', 'unhanded', '未交班') THEN 1
                        ELSE 0
                    END as is_not_handed_over
                FROM defect_records
                WHERE DATE(FAULT_TIME) = :target_date
                  AND HANDOVER_STATUS IN ('not_handed_over', 'unhanded', '未交班')
                ORDER BY FAULT_TIME
            """)
            
            result = session.execute(sql, {"target_date": target_date})
            for row in result:
                data = dict(row._mapping)
                records.append(data)
            
            logger.info(f"采集异常缺陷工作量 {len(records)} 条")
            
        except Exception as e:
            logger.error(f"采集异常缺陷工作量失败: {e}")
        finally:
            if session:
                session.close()
        
        return records
    
    @staticmethod
    def collect_overload_workload(target_date: str) -> List[Dict]:
        """
        采集重过载工作量
        
        业务规则（最新）：
        - 当值记录未解决的所有重过载数
        
        参数：
            target_date: 目标日期 (YYYY-MM-DD)
        
        返回：重过载记录列表
        """
        session = NonPlanWorkloadDatabase.get_session()
        if not session:
            logger.warning("数据库未连接，返回空列表")
            return []
        
        records = []
        
        try:
            from sqlalchemy import text
            
            # 查询当值记录未解决的重过载
            sql = text("""
                SELECT 
                    OVERLOAD_ID as record_id,
                    OVERLOAD_NO as overload_no,
                    OVERLOAD_TYPE as overload_type,
                    EQUIPMENT_NAME as equipment_name,
                    RECORD_TIME as record_time,
                    EXPECTED_RESTORE_TIME as expected_restore_time,
                    STATUS as status,
                    OPERATOR_NAME as operator_name,
                    '重过载' as task_name,
                    -- 判断是否未解决
                    CASE 
                        WHEN STATUS IN ('unresolved', 'pending', '未解决', '待处理') THEN 1
                        ELSE 0
                    END as is_unresolved
                FROM overload_records
                WHERE DATE(RECORD_TIME) = :target_date
                  AND STATUS IN ('unresolved', 'pending', '未解决', '待处理')
                ORDER BY RECORD_TIME
            """)
            
            result = session.execute(sql, {"target_date": target_date})
            for row in result:
                data = dict(row._mapping)
                records.append(data)
            
            logger.info(f"采集重过载工作量 {len(records)} 条")
            
        except Exception as e:
            logger.error(f"采集重过载工作量失败: {e}")
        finally:
            if session:
                session.close()
        
        return records


# ============================================================
# 工作量分配类
# ============================================================

class WorkloadAllocator:
    """工作量按时间段分配"""
    
    @staticmethod
    def determine_shift(hour: int) -> str:
        """判断所属班次"""
        if hour >= SHIFT_MORNING_START and hour < SHIFT_MORNING_END:
            return "morning"
        elif hour >= SHIFT_AFTERNOON_START and hour < SHIFT_AFTERNOON_END:
            return "afternoon"
        elif hour >= SHIFT_NIGHT_START or hour < 8:
            return "night"
        else:
            return "night"  # 默认夜班
    
    @staticmethod
    def allocate_maintenance_task(record: Dict) -> Dict:
        """
        分配计划检修任务工作量到各班次
        
        业务规则（最新）：
        - 「待执行-批准停电开始时间为当天」+「执行中-批准工作结束时间为当天（21:00后的也包括）」= 白天工作量（早班+中班）
        - 「批准工作结束时间为21:00后」= 夜班工作量
        
        注意：同时支持开展中、已终结分类
        """
        result = {
            "record_id": record["record_id"],
            "task_category": record["task_category"],
            "task_name": record["task_name"],
            "approved_start_time": record["approved_start_time"],
            "approved_end_time": record["approved_end_time"],
            "status": record["status"],
            "status_category": record.get("status_category", "unknown"),
            "shift_allocation": {
                "morning": 0,
                "afternoon": 0,
                "night": 0
            },
            "total_count": 0,
            "in_progress_count": 0,
            "completed_count": 0
        }
        
        try:
            # 判断状态分类
            status_category = record.get("status_category", "unknown")
            
            # 根据批准结束时间分配
            end_time = record["approved_end_time"]
            if end_time:
                hour = end_time.hour
                
                # 新规则：21:00前纳入早班、中班；21:00后纳入夜班
                if hour < 21:
                    shift = WorkloadAllocator.determine_shift(hour)
                    result["shift_allocation"][shift] = 1
                    result["total_count"] = 1
                    
                    # 统计状态分类
                    if status_category == "in_progress":
                        result["in_progress_count"] = 1
                    elif status_category == "completed":
                        result["completed_count"] = 1
                else:
                    result["shift_allocation"]["night"] = 1
                    result["total_count"] = 1
                    
                    # 统计状态分类
                    if status_category == "in_progress":
                        result["in_progress_count"] = 1
                    elif status_category == "completed":
                        result["completed_count"] = 1
                    
        except Exception as e:
            logger.error(f"分配检修任务失败: {e}")
        
        return result
    
    @staticmethod
    def allocate_equipment_task(record: Dict) -> Dict:
        """
        分配设备投退任务工作量到各班次
        
        业务规则（最新）：
        - 「待执行-批准工作开始时间为当天」+「执行中-批准工作结束时间为当天（21:00后的也包括）」= 白天工作量（早班+中班）
        - 「批准工作结束时间为21:00后」= 夜班工作量
        
        注意：同时支持开展中、已终结分类
        """
        result = {
            "record_id": record["record_id"],
            "task_category": record["task_category"],
            "task_name": record["task_name"],
            "approved_start_time": record["approved_start_time"],
            "approved_end_time": record["approved_end_time"],
            "status": record["status"],
            "status_category": record.get("status_category", "unknown"),
            "shift_allocation": {
                "morning": 0,
                "afternoon": 0,
                "night": 0
            },
            "total_count": 0,
            "in_progress_count": 0,
            "completed_count": 0
        }
        
        try:
            status_category = record.get("status_category", "unknown")
            
            # 根据批准结束时间分配
            end_time = record["approved_end_time"]
            if end_time:
                hour = end_time.hour
                
                # 新规则：21:00前纳入早班、中班；21:00后纳入夜班
                if hour < 21:
                    shift = WorkloadAllocator.determine_shift(hour)
                    result["shift_allocation"][shift] = 1
                    result["total_count"] = 1
                    
                    # 统计状态分类
                    if status_category == "in_progress":
                        result["in_progress_count"] = 1
                    elif status_category == "completed":
                        result["completed_count"] = 1
                else:
                    result["shift_allocation"]["night"] = 1
                    result["total_count"] = 1
                    
                    # 统计状态分类
                    if status_category == "in_progress":
                        result["in_progress_count"] = 1
                    elif status_category == "completed":
                        result["completed_count"] = 1
                    
        except Exception as e:
            logger.error(f"分配设备投退任务失败: {e}")
        
        return result
    
    @staticmethod
    def allocate_transfer_task(record: Dict) -> Dict:
        """
        分配转供电任务工作量到各班次
        
        业务规则（最新）：
        - 「待执行-批准转出开始时间为当天」+「执行中-转出开始时间为当天（21:00后的不包括）」= 白天工作量（早班+中班）
        - 「批准转出开始时间为21:00至次日08:30」= 夜班工作量
        
        注意：同时支持开展中、已终结分类
        """
        result = {
            "record_id": record["record_id"],
            "task_category": record["task_category"],
            "task_name": record["task_name"],
            "transfer_out_time": record["transfer_out_time"],
            "transfer_back_time": record["transfer_back_time"],
            "status": record["status"],
            "status_category": record.get("status_category", "unknown"),
            "shift_allocation": {
                "morning": 0,
                "afternoon": 0,
                "night": 0
            },
            "total_count": 0,
            "in_progress_count": 0,
            "completed_count": 0
        }
        
        try:
            status_category = record.get("status_category", "unknown")
            
            # 统一使用转出开始时间分配
            out_time = record["transfer_out_time"]
            if out_time:
                hour = out_time.hour
                
                # 新规则：21:00前纳入早班、中班；21:00至次日08:30纳入夜班
                if hour < 21:
                    shift = WorkloadAllocator.determine_shift(hour)
                    result["shift_allocation"][shift] = 1
                    result["total_count"] = 1
                    
                    # 统计状态分类
                    if status_category == "in_progress":
                        result["in_progress_count"] = 1
                    elif status_category == "completed":
                        result["completed_count"] = 1
                else:
                    # 21:00至次日08:30纳入夜班
                    result["shift_allocation"]["night"] = 1
                    result["total_count"] = 1
                    
                    # 统计状态分类
                    if status_category == "in_progress":
                        result["in_progress_count"] = 1
                    elif status_category == "completed":
                        result["completed_count"] = 1
                    
        except Exception as e:
            logger.error(f"分配转供电任务失败: {e}")
        
        return result
    
    @staticmethod
    def allocate_weekly_plan_task(record: Dict, pre_analyze: bool = False) -> Dict:
        """
        分配周计划任务工作量到各班次
        
        业务规则（最新）：
        - 需自动读取批准工作开始时间为当天的所有周计划（包括跨天工作的周计划）
        - 将周计划总数纳入早班、中班时间段内考虑
        - 夜班周计划工作量暂时以跨天工作的周计划总数为准
        - 支持开展中、已终结分类
        """
        result = {
            "record_id": record["record_id"],
            "task_category": record["task_category"],
            "task_name": record["task_name"],
            "approved_start_time": record["approved_start_time"],
            "approved_end_time": record["approved_end_time"],
            "task_count": record.get("task_count", 1),
            "status": record["status"],
            "status_category": record.get("status_category", "unknown"),
            "is_cross_day": record.get("is_cross_day", 0),
            "shift_allocation": {
                "morning": 0,
                "afternoon": 0,
                "night": 0
            },
            "total_count": 0,
            "in_progress_count": 0,
            "completed_count": 0
        }
        
        try:
            count = record.get("task_count", 1)
            status_category = record.get("status_category", "unknown")
            is_cross_day = record.get("is_cross_day", 0)
            
            if pre_analyze:
                # 提前分析：周计划总数纳入早班、中班，夜班暂时忽略
                result["shift_allocation"]["morning"] = count // 2
                result["shift_allocation"]["afternoon"] = count - (count // 2)
                result["shift_allocation"]["night"] = 0  # 夜班忽略
                result["total_count"] = count
                
                # 统计状态分类
                if status_category == "in_progress":
                    result["in_progress_count"] = count
                elif status_category == "completed":
                    result["completed_count"] = count
            else:
                # 正常分析：将周计划总数纳入早班、中班
                result["shift_allocation"]["morning"] = count // 2
                result["shift_allocation"]["afternoon"] = count - (count // 2)
                
                # 如果是跨天工作，夜班纳入跨天工作总数
                if is_cross_day:
                    result["shift_allocation"]["night"] = count
                else:
                    result["shift_allocation"]["night"] = 0
                
                result["total_count"] = count
                
                # 统计状态分类
                if status_category == "in_progress":
                    result["in_progress_count"] = count
                elif status_category == "completed":
                    result["completed_count"] = count
                    
        except Exception as e:
            logger.error(f"分配周计划任务失败: {e}")
        
        return result


# ============================================================
# 工具函数
# ============================================================

@tool
def calculate_plan_workload(
    target_date: str = "",
    pre_analyze: bool = False
) -> str:
    """
    计算计划工作量（按班次分配，支持开展中、已终结分类）
    
    功能：
    1. 采集计划检修、转供电、设备投退、周计划数据
    2. 按业务规则分配到早班、中班、夜班
    3. 支持开展中、已终结分类
    4. 支持提前分析模式（pre_analyze=True）
    
    业务规则（最新）：
    1. 计划检修：
       - 「待执行-批准停电开始时间为当天」+「执行中-批准工作结束时间为当天（21:00后的也包括）」= 白天工作量（早班+中班）
       - 「批准工作结束时间为21:00后」= 夜班工作量
       - 支持开展中、已终结分类
    
    2. 设备投退：
       - 「待执行-批准工作开始时间为当天」+「执行中-批准工作结束时间为当天（21:00后的也包括）」= 白天工作量（早班+中班）
       - 「批准工作结束时间为21:00后」= 夜班工作量
       - 支持开展中、已终结分类
    
    3. 转供电：
       - 「待执行-批准转出开始时间为当天」+「执行中-转出开始时间为当天（21:00后的不包括）」= 白天工作量（早班+中班）
       - 「批准转出开始时间为21:00至次日08:30」= 夜班工作量
       - 支持开展中、已终结分类
    
    4. 周计划：
       - 将周计划总数纳入早班、中班
       - 夜班周计划工作量暂时以跨天工作的周计划总数为准
       - 支持开展中、已终结分类
    
    参数：
    - target_date: 目标日期 (YYYY-MM-DD)，默认今天
    - pre_analyze: 是否提前分析（影响分配策略）
    
    返回：计划工作量统计结果JSON字符串
    """
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
            "maintenance": {
                "records": [],
                "summary": {
                    "total": 0,
                    "in_progress": 0,
                    "completed": 0,
                    "morning": 0,
                    "afternoon": 0,
                    "night": 0
                }
            },
            "equipment": {
                "records": [],
                "summary": {
                    "total": 0,
                    "in_progress": 0,
                    "completed": 0,
                    "morning": 0,
                    "afternoon": 0,
                    "night": 0
                }
            },
            "transfer": {
                "records": [],
                "summary": {
                    "total": 0,
                    "in_progress": 0,
                    "completed": 0,
                    "morning": 0,
                    "afternoon": 0,
                    "night": 0
                }
            },
            "weekly_plan": {
                "records": [],
                "summary": {
                    "total": 0,
                    "in_progress": 0,
                    "completed": 0,
                    "morning": 0,
                    "afternoon": 0,
                    "night": 0
                }
            },
            "total_summary": {
                "morning": {"total_count": 0, "tasks": []},
                "afternoon": {"total_count": 0, "tasks": []},
                "night": {"total_count": 0, "tasks": []}
            }
        }
        
        # 2.1 分配检修任务
        for record in maintenance_records:
            allocated = WorkloadAllocator.allocate_maintenance_task(record)
            allocation_results["maintenance"]["records"].append(allocated)
            
            # 更新检修汇总
            allocation_results["maintenance"]["summary"]["total"] += allocated["total_count"]
            allocation_results["maintenance"]["summary"]["in_progress"] += allocated["in_progress_count"]
            allocation_results["maintenance"]["summary"]["completed"] += allocated["completed_count"]
            allocation_results["maintenance"]["summary"]["morning"] += allocated["shift_allocation"]["morning"]
            allocation_results["maintenance"]["summary"]["afternoon"] += allocated["shift_allocation"]["afternoon"]
            allocation_results["maintenance"]["summary"]["night"] += allocated["shift_allocation"]["night"]
            
            # 更新总计
            for shift, count in allocated["shift_allocation"].items():
                if count > 0:
                    allocation_results["total_summary"][shift]["total_count"] += count
                    allocation_results["total_summary"][shift]["tasks"].append({
                        "category": allocated["task_category"],
                        "name": allocated["task_name"],
                        "count": count,
                        "record_id": allocated["record_id"]
                    })
        
        # 2.2 分配设备投退任务
        for record in equipment_records:
            allocated = WorkloadAllocator.allocate_equipment_task(record)
            allocation_results["equipment"]["records"].append(allocated)
            
            # 更新设备投退汇总
            allocation_results["equipment"]["summary"]["total"] += allocated["total_count"]
            allocation_results["equipment"]["summary"]["in_progress"] += allocated["in_progress_count"]
            allocation_results["equipment"]["summary"]["completed"] += allocated["completed_count"]
            allocation_results["equipment"]["summary"]["morning"] += allocated["shift_allocation"]["morning"]
            allocation_results["equipment"]["summary"]["afternoon"] += allocated["shift_allocation"]["afternoon"]
            allocation_results["equipment"]["summary"]["night"] += allocated["shift_allocation"]["night"]
            
            # 更新总计
            for shift, count in allocated["shift_allocation"].items():
                if count > 0:
                    allocation_results["total_summary"][shift]["total_count"] += count
                    allocation_results["total_summary"][shift]["tasks"].append({
                        "category": allocated["task_category"],
                        "name": allocated["task_name"],
                        "count": count,
                        "record_id": allocated["record_id"]
                    })
        
        # 2.3 分配转供电任务
        for record in transfer_records:
            allocated = WorkloadAllocator.allocate_transfer_task(record)
            allocation_results["transfer"]["records"].append(allocated)
            
            # 更新转供电汇总
            allocation_results["transfer"]["summary"]["total"] += allocated["total_count"]
            allocation_results["transfer"]["summary"]["in_progress"] += allocated["in_progress_count"]
            allocation_results["transfer"]["summary"]["completed"] += allocated["completed_count"]
            allocation_results["transfer"]["summary"]["morning"] += allocated["shift_allocation"]["morning"]
            allocation_results["transfer"]["summary"]["afternoon"] += allocated["shift_allocation"]["afternoon"]
            allocation_results["transfer"]["summary"]["night"] += allocated["shift_allocation"]["night"]
            
            # 更新总计
            for shift, count in allocated["shift_allocation"].items():
                if count > 0:
                    allocation_results["total_summary"][shift]["total_count"] += count
                    allocation_results["total_summary"][shift]["tasks"].append({
                        "category": allocated["task_category"],
                        "name": allocated["task_name"],
                        "count": count,
                        "record_id": allocated["record_id"]
                    })
        
        # 2.4 分配周计划任务
        for record in weekly_plan_records:
            allocated = WorkloadAllocator.allocate_weekly_plan_task(record, pre_analyze=pre_analyze)
            allocation_results["weekly_plan"]["records"].append(allocated)
            
            # 更新周计划汇总
            allocation_results["weekly_plan"]["summary"]["total"] += allocated["total_count"]
            allocation_results["weekly_plan"]["summary"]["in_progress"] += allocated["in_progress_count"]
            allocation_results["weekly_plan"]["summary"]["completed"] += allocated["completed_count"]
            allocation_results["weekly_plan"]["summary"]["morning"] += allocated["shift_allocation"]["morning"]
            allocation_results["weekly_plan"]["summary"]["afternoon"] += allocated["shift_allocation"]["afternoon"]
            allocation_results["weekly_plan"]["summary"]["night"] += allocated["shift_allocation"]["night"]
            
            # 更新总计
            for shift, count in allocated["shift_allocation"].items():
                if count > 0:
                    allocation_results["total_summary"][shift]["total_count"] += count
                    allocation_results["total_summary"][shift]["tasks"].append({
                        "category": allocated["task_category"],
                        "name": allocated["task_name"],
                        "count": count,
                        "record_id": allocated["record_id"]
                    })
        
        # 3. 计算总计数
        total_count = (
            allocation_results["total_summary"]["morning"]["total_count"] +
            allocation_results["total_summary"]["afternoon"]["total_count"] +
            allocation_results["total_summary"]["night"]["total_count"]
        )
        
        allocation_results["total_summary"]["total_count"] = total_count
        
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
def calculate_non_plan_workload(
    target_date: str = ""
) -> str:
    """
    计算非计划工作量（支持故障日志、异常缺陷、重过载）
    
    功能：
    1. 采集故障日志（前三天未交班的故障单数）
    2. 采集异常缺陷（当值记录未交班的缺陷单数）
    3. 采集重过载（当值记录未解决的重过载数）
    
    业务规则（最新）：
    1. 故障日志：前三天未交班的故障单数
    2. 异常缺陷：当值记录未交班的缺陷单数
    3. 重过载：当值记录未解决的重过载数
    
    参数：
    - target_date: 目标日期 (YYYY-MM-DD)，默认今天
    
    返回：非计划工作量统计结果JSON字符串
    """
    try:
        if not target_date:
            target_date = datetime.now().strftime("%Y-%m-%d")
        
        # 1. 采集各类非计划任务
        fault_records = NonPlanWorkloadDatabase.collect_fault_workload(target_date)
        defect_records = NonPlanWorkloadDatabase.collect_defect_workload(target_date)
        overload_records = NonPlanWorkloadDatabase.collect_overload_workload(target_date)
        
        # 2. 统计结果
        allocation_results = {
            "target_date": target_date,
            "fault_logs": {
                "records": fault_records,
                "count": len(fault_records)
            },
            "defect_records": {
                "records": defect_records,
                "count": len(defect_records)
            },
            "overload_records": {
                "records": overload_records,
                "count": len(overload_records)
            },
            "total_count": len(fault_records) + len(defect_records) + len(overload_records)
        }
        
        return json.dumps({
            "success": True,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data": allocation_results
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"计算非计划工作量失败: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "计算非计划工作量失败"
        }, ensure_ascii=False)


@tool
def get_workload_dashboard(
    target_date: str = "",
    pre_analyze: bool = False
) -> str:
    """
    获取工作量看板数据（计划工作量 + 非计划工作量）
    
    功能：
    1. 计划工作量统计（计划检修、转供电、设备投退、周计划）
    2. 非计划工作量统计（故障日志、异常缺陷、重过载）
    3. 支持开展中、已终结分类
    4. 按早班、中班、夜班分配
    
    参数：
    - target_date: 目标日期 (YYYY-MM-DD)，默认今天
    - pre_analyze: 是否提前分析
    
    返回：工作量看板数据JSON字符串
    """
    try:
        # 仪表盘：target_date为空时检修单查所有记录（不限日期），其他表仍按当天
        if not target_date:
            all_records_mode = True
            today_str = datetime.now().strftime("%Y-%m-%d")
        else:
            all_records_mode = False
            today_str = target_date
        
        maintenance_records = PlanWorkloadDatabase.collect_maintenance_workload(
            None if all_records_mode else target_date
        )
        equipment_records = PlanWorkloadDatabase.collect_equipment_workload(today_str)
        transfer_records = PlanWorkloadDatabase.collect_transfer_workload(today_str)
        weekly_plan_records = PlanWorkloadDatabase.collect_weekly_plan_workload(today_str)
        
        # 2. 采集非计划工作量数据
        fault_records = NonPlanWorkloadDatabase.collect_fault_workload(today_str)
        defect_records = NonPlanWorkloadDatabase.collect_defect_workload(today_str)
        overload_records = NonPlanWorkloadDatabase.collect_overload_workload(today_str)
        
        # 3. 分配计划工作量到各班次
        plan_allocation_results = {
            "maintenance": {
                "records": [],
                "summary": {
                    "total": 0,
                    "in_progress": 0,
                    "completed": 0,
                    "morning": 0,
                    "afternoon": 0,
                    "night": 0
                }
            },
            "equipment": {
                "records": [],
                "summary": {
                    "total": 0,
                    "in_progress": 0,
                    "completed": 0,
                    "morning": 0,
                    "afternoon": 0,
                    "night": 0
                }
            },
            "transfer": {
                "records": [],
                "summary": {
                    "total": 0,
                    "in_progress": 0,
                    "completed": 0,
                    "morning": 0,
                    "afternoon": 0,
                    "night": 0
                }
            },
            "weekly_plan": {
                "records": [],
                "summary": {
                    "total": 0,
                    "in_progress": 0,
                    "completed": 0,
                    "morning": 0,
                    "afternoon": 0,
                    "night": 0
                }
            },
            "total_summary": {
                "morning": {"total_count": 0, "tasks": []},
                "afternoon": {"total_count": 0, "tasks": []},
                "night": {"total_count": 0, "tasks": []},
                "total_count": 0
            }
        }
        
        # 分配检修任务
        for record in maintenance_records:
            allocated = WorkloadAllocator.allocate_maintenance_task(record)
            plan_allocation_results["maintenance"]["records"].append(allocated)
            
            # 更新汇总
            plan_allocation_results["maintenance"]["summary"]["total"] += allocated["total_count"]
            plan_allocation_results["maintenance"]["summary"]["in_progress"] += allocated["in_progress_count"]
            plan_allocation_results["maintenance"]["summary"]["completed"] += allocated["completed_count"]
            plan_allocation_results["maintenance"]["summary"]["morning"] += allocated["shift_allocation"]["morning"]
            plan_allocation_results["maintenance"]["summary"]["afternoon"] += allocated["shift_allocation"]["afternoon"]
            plan_allocation_results["maintenance"]["summary"]["night"] += allocated["shift_allocation"]["night"]
            
            # 更新总计
            for shift, count in allocated["shift_allocation"].items():
                if count > 0:
                    plan_allocation_results["total_summary"][shift]["total_count"] += count
                    plan_allocation_results["total_summary"][shift]["tasks"].append({
                        "category": allocated["task_category"],
                        "name": allocated["task_name"],
                        "count": count,
                        "record_id": allocated["record_id"]
                    })
        
        # 分配设备投退任务
        for record in equipment_records:
            allocated = WorkloadAllocator.allocate_equipment_task(record)
            plan_allocation_results["equipment"]["records"].append(allocated)
            
            # 更新汇总
            plan_allocation_results["equipment"]["summary"]["total"] += allocated["total_count"]
            plan_allocation_results["equipment"]["summary"]["in_progress"] += allocated["in_progress_count"]
            plan_allocation_results["equipment"]["summary"]["completed"] += allocated["completed_count"]
            plan_allocation_results["equipment"]["summary"]["morning"] += allocated["shift_allocation"]["morning"]
            plan_allocation_results["equipment"]["summary"]["afternoon"] += allocated["shift_allocation"]["afternoon"]
            plan_allocation_results["equipment"]["summary"]["night"] += allocated["shift_allocation"]["night"]
            
            # 更新总计
            for shift, count in allocated["shift_allocation"].items():
                if count > 0:
                    plan_allocation_results["total_summary"][shift]["total_count"] += count
                    plan_allocation_results["total_summary"][shift]["tasks"].append({
                        "category": allocated["task_category"],
                        "name": allocated["task_name"],
                        "count": count,
                        "record_id": allocated["record_id"]
                    })
        
        # 分配转供电任务
        for record in transfer_records:
            allocated = WorkloadAllocator.allocate_transfer_task(record)
            plan_allocation_results["transfer"]["records"].append(allocated)
            
            # 更新汇总
            plan_allocation_results["transfer"]["summary"]["total"] += allocated["total_count"]
            plan_allocation_results["transfer"]["summary"]["in_progress"] += allocated["in_progress_count"]
            plan_allocation_results["transfer"]["summary"]["completed"] += allocated["completed_count"]
            plan_allocation_results["transfer"]["summary"]["morning"] += allocated["shift_allocation"]["morning"]
            plan_allocation_results["transfer"]["summary"]["afternoon"] += allocated["shift_allocation"]["afternoon"]
            plan_allocation_results["transfer"]["summary"]["night"] += allocated["shift_allocation"]["night"]
            
            # 更新总计
            for shift, count in allocated["shift_allocation"].items():
                if count > 0:
                    plan_allocation_results["total_summary"][shift]["total_count"] += count
                    plan_allocation_results["total_summary"][shift]["tasks"].append({
                        "category": allocated["task_category"],
                        "name": allocated["task_name"],
                        "count": count,
                        "record_id": allocated["record_id"]
                    })
        
        # 分配周计划任务
        for record in weekly_plan_records:
            allocated = WorkloadAllocator.allocate_weekly_plan_task(record, pre_analyze=pre_analyze)
            plan_allocation_results["weekly_plan"]["records"].append(allocated)
            
            # 更新汇总
            plan_allocation_results["weekly_plan"]["summary"]["total"] += allocated["total_count"]
            plan_allocation_results["weekly_plan"]["summary"]["in_progress"] += allocated["in_progress_count"]
            plan_allocation_results["weekly_plan"]["summary"]["completed"] += allocated["completed_count"]
            plan_allocation_results["weekly_plan"]["summary"]["morning"] += allocated["shift_allocation"]["morning"]
            plan_allocation_results["weekly_plan"]["summary"]["afternoon"] += allocated["shift_allocation"]["afternoon"]
            plan_allocation_results["weekly_plan"]["summary"]["night"] += allocated["shift_allocation"]["night"]
            
            # 更新总计
            for shift, count in allocated["shift_allocation"].items():
                if count > 0:
                    plan_allocation_results["total_summary"][shift]["total_count"] += count
                    plan_allocation_results["total_summary"][shift]["tasks"].append({
                        "category": allocated["task_category"],
                        "name": allocated["task_name"],
                        "count": count,
                        "record_id": allocated["record_id"]
                    })
        
        # 计算总计数
        total_count = (
            plan_allocation_results["total_summary"]["morning"]["total_count"] +
            plan_allocation_results["total_summary"]["afternoon"]["total_count"] +
            plan_allocation_results["total_summary"]["night"]["total_count"]
        )
        
        plan_allocation_results["total_summary"]["total_count"] = total_count
        
        # 4. 统计非计划工作量
        non_plan_allocation_results = {
            "fault_logs": {
                "records": fault_records,
                "count": len(fault_records)
            },
            "defect_records": {
                "records": defect_records,
                "count": len(defect_records)
            },
            "overload_records": {
                "records": overload_records,
                "count": len(overload_records)
            },
            "total_count": len(fault_records) + len(defect_records) + len(overload_records)
        }
        
        # 5. 合并结果
        dashboard_data = {
            "target_date": target_date,
            "pre_analyze": pre_analyze,
            "plan_workload": plan_allocation_results,
            "non_plan_workload": non_plan_allocation_results,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return json.dumps({
            "success": True,
            "data": dashboard_data
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"获取工作量看板数据失败: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "获取工作量看板数据失败"
        }, ensure_ascii=False)


@tool
def manual_adjust_plan_workload(
    target_date: str,
    morning_count: int,
    afternoon_count: int,
    night_count: int,
    feedback_data: Dict = None
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
def get_manual_adjustments(target_date: str) -> str:
    """
    获取指定日期的手动修改数据
    
    参数：
    - target_date: 目标日期 (YYYY-MM-DD)
    
    返回：手动修改数据JSON字符串
    """
    try:
        manual_data = ManualWorkloadData.load_manual_data(target_date)
        
        if manual_data:
            return json.dumps({
                "success": True,
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "data": {
                    "target_date": target_date,
                    "manual_data": manual_data
                }
            }, ensure_ascii=False, indent=2)
        else:
            return json.dumps({
                "success": True,
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "data": {
                    "target_date": target_date,
                    "message": "该日期无手动修改数据"
                }
            }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"获取手动修改数据失败: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "获取手动修改数据失败"
        }, ensure_ascii=False)
