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
import os
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
        if os.environ.get("SKIP_DB", "").lower() in ("true", "1", "yes"):
            return None
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
            
            result = session.execute(sql)
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
    def collect_equipment_workload(target_date: str = None) -> List[Dict]:
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
            
            # 查询设备投退记录（TD_OUTAGE_REPAIR_APPLY_INFO 中 FILL_OVERHAUL_TYPE='新设备投产'）
            date_condition = ""
            params = {}
            if target_date:
                date_condition = "AND TRUNC(FILL_WORK_BEGIN_DATE) = TO_DATE(:target_date, 'YYYY-MM-DD')"
                params["target_date"] = target_date
            
            sql = text(f"""
                SELECT 
                    MK_ID as record_id,
                    FILL_PLAN_CODE as operation_no,
                    FILL_OVERHAUL_TYPE as operation_type,
                    FILL_WORK_BEGIN_DATE as approved_start_time,
                    FILL_WORK_END_DATE as approved_end_time,
                    FORM_STATUS as status,
                    'A6' as task_category,
                    '设备投退' as task_name,
                    CASE 
                        WHEN FORM_STATUS IN ('DJS', 'DZX', 'ZX', 'RB') THEN 'in_progress'
                        WHEN FORM_STATUS IN ('ZJ', 'ZF', 'RC', 'CL') THEN 'completed'
                        ELSE 'unknown'
                    END as status_category,
                    CASE 
                        WHEN EXTRACT(HOUR FROM FILL_WORK_END_DATE) >= 21 THEN 1
                        ELSE 0
                    END as is_night_shift
                FROM TD_OUTAGE_REPAIR_APPLY_INFO
                WHERE FILL_OVERHAUL_TYPE = '新设备投产'
                {date_condition}
                ORDER BY FILL_WORK_BEGIN_DATE
            """)
            
            result = session.execute(sql, params)
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
    def collect_transfer_workload(target_date: str = "") -> List[Dict]:
        """
        采集转供电工作量
        
        业务规则（最新）：
        - 数据来源：OC_POWER_SUPPLY_MODE（转供电表）
        - 查询条件：以申请时间 APPLY_TIME 为准
        - 若预测当天三值工作量：
          - 申请时间为21:00前的总数纳入早班、中班
          - 申请时间为21:00至次日08:30的纳入夜班
        - 支持开展中、已终结分类
        - EXE/CAN/REC/INE = 开展中，END/CLO = 已终结
        
        参数：
            target_date: 目标日期 (YYYY-MM-DD)，为空时不限制日期
        
        返回：转供电工作量记录列表
        """
        session = PlanWorkloadDatabase.get_session()
        if not session:
            logger.warning("数据库未连接，返回空列表")
            return []
        
        records = []
        
        try:
            from sqlalchemy import text
            
            # 构建日期过滤条件
            date_condition = ""
            if target_date:
                date_condition = "AND TRUNC(APPLY_TIME) = TO_DATE(:target_date, 'YYYY-MM-DD')"
            
            sql = text(f"""
                SELECT 
                    MK_ID as record_id,
                    MODE_CODE as order_no,
                    APPLY_TIME as transfer_out_time,
                    EXECUTE_STATE as status,
                    'A3' as task_category,
                    '转供电' as task_name,
                    -- 判断状态分类
                    CASE 
                        WHEN EXECUTE_STATE IN ('EXE', 'CAN', 'REC', 'INE') THEN 'in_progress'
                        WHEN EXECUTE_STATE IN ('END', 'CLO') THEN 'completed'
                        ELSE 'unknown'
                    END as status_category,
                    -- 判断是否跨夜班（21:00至次日08:30）
                    CASE 
                        WHEN EXTRACT(HOUR FROM APPLY_TIME) >= 21 OR EXTRACT(HOUR FROM APPLY_TIME) < 8 THEN 1
                        ELSE 0
                    END as is_night_shift
                FROM OC_POWER_SUPPLY_MODE
                WHERE 1=1 {date_condition}
                ORDER BY APPLY_TIME
            """)
            
            params = {}
            if target_date:
                params["target_date"] = target_date
            
            result = session.execute(sql, params)
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
    def collect_weekly_plan_workload(target_date: str = "") -> List[Dict]:
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
            target_date: 目标日期 (YYYY-MM-DD)，空字符串时不限制日期
        
        返回：周计划工作量记录列表
        """
        session = PlanWorkloadDatabase.get_session()
        if not session:
            logger.warning("数据库未连接，返回空列表")
            return []
        
        records = []
        
        try:
            from sqlalchemy import text
            
            # 构建日期过滤条件
            date_condition = ""
            params = {}
            if target_date:
                date_condition = "AND TRUNC(WORK_BEGIN_TIME) = TO_DATE(:target_date, 'YYYY-MM-DD')"
                params["target_date"] = target_date
            
            sql = text(f"""
                SELECT 
                    COUNT(*) as task_count,
                    -- 统计开展中数量
                    SUM(CASE 
                        WHEN PLAN_SATE IN ('C', 'S', 'Z') THEN 1 
                        ELSE 0 
                    END) as in_progress_count,
                    -- 统计已终结数量
                    SUM(CASE 
                        WHEN PLAN_SATE IN ('G', 'F') THEN 1 
                        ELSE 0 
                    END) as completed_count,
                    -- 统计跨天工作数量
                    SUM(CASE 
                        WHEN TRUNC(WORK_BEGIN_TIME) != TRUNC(WROK_END_TIME) THEN 1 
                        ELSE 0 
                    END) as cross_day_count
                FROM OP_WEEKLY_PLAN_MAIN
                WHERE PLAN_SATE IN ('C', 'S', 'Z', 'G', 'F')
                    {date_condition}
            """)
            
            result = session.execute(sql, params)
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
    
    @staticmethod
    def collect_protect_feeder_workload(target_date: str = "") -> List[Dict]:
        """
        采集保供电工作量
        
        业务规则：
        - 数据来源：OP_PROTECT_FEEDER
        - EXECUTE_STATE IN ('REC', 'EXE', 'SQ', 'SP') → 开展中
        - EXECUTE_STATE IN ('CAN', 'END') → 已终结
        - 时间以 APP_TIME 为准
        
        参数：
            target_date: 目标日期 (YYYY-MM-DD)，空字符串时不限制日期
        
        返回：保供电工作量记录列表
        """
        session = PlanWorkloadDatabase.get_session()
        if not session:
            logger.warning("数据库未连接，返回空列表")
            return []
        
        records = []
        
        try:
            from sqlalchemy import text
            
            # 构建日期过滤条件
            date_condition = ""
            params = {}
            if target_date:
                date_condition = "AND TRUNC(APP_TIME) = TO_DATE(:target_date, 'YYYY-MM-DD')"
                params["target_date"] = target_date
            
            sql = text(f"""
                SELECT 
                    MK_ID as record_id,
                    WORK_NO as task_no,
                    EXECUTE_STATE as status,
                    APP_TIME as task_time,
                    DIS_ORG_ID,
                    DIS_ORG_NAME,
                    COUNTY_DEPT_ID,
                    COUNTY_DEPT_NAME,
                    CASE 
                        WHEN EXECUTE_STATE IN ('REC', 'EXE', 'SQ', 'SP') THEN 'in_progress'
                        WHEN EXECUTE_STATE IN ('CAN', 'END') THEN 'completed'
                        ELSE 'unknown'
                    END as status_category,
                    'A5' as task_category,
                    '保供电' as task_name,
                    1 as count
                FROM OP_PROTECT_FEEDER
                WHERE EXECUTE_STATE IN ('REC', 'EXE', 'SQ', 'SP', 'CAN', 'END')
                    {date_condition}
                ORDER BY APP_TIME DESC
            """)
            
            result = session.execute(sql, params)
            
            for row in result.fetchall():
                records.append({
                    "record_id": row.record_id,
                    "task_no": row.task_no,
                    "status": row.status,
                    "task_time": str(row.task_time) if row.task_time else "",
                    "status_category": row.status_category,
                    "task_category": row.task_category,
                    "task_name": row.task_name,
                    "count": row.count,
                    "total_count": 1,
                    "in_progress_count": 1 if row.status_category == "in_progress" else 0,
                    "completed_count": 1 if row.status_category == "completed" else 0
                })
            
            logger.info(f"采集保供电工作量完成: {len(records)}条")
            
        except Exception as e:
            logger.error(f"采集保供电工作量失败: {e}")
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
            
            # 查询未归档的故障日志（OC_GZ_TRIP_REPORT）
            sql = text("""
                SELECT 
                    MK_ID as record_id,
                    DDBZ_CODE as fault_no,
                    '' as fault_type,
                    '' as equipment_name,
                    DIS_TD_TIME as fault_time,
                    DIS_TD_TIME as expected_restore_time,
                    IS_PLACE_FILE as status,
                    IS_PLACE_FILE as handover_status,
                    '' as operator_name,
                    '故障跳闸' as task_name,
                    1 as is_not_handed_over
                FROM OC_GZ_TRIP_REPORT
                WHERE IS_PLACE_FILE = 'N'
                ORDER BY DIS_TD_TIME
            """)
            
            result = session.execute(sql)
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
            
            # 查询未归档的异常缺陷（OP_EXCEPTION_RECORD，状态1/2/3为开展中）
            sql = text("""
                SELECT 
                    MK_ID as record_id,
                    RECORD_CODE as defect_no,
                    '' as defect_type,
                    '' as equipment_name,
                    RECORD_TIME as fault_time,
                    RECORD_TIME as expected_restore_time,
                    EXCEPTION_STATUS as status,
                    EXCEPTION_STATUS as handover_status,
                    '' as operator_name,
                    '异常缺陷' as task_name,
                    1 as is_not_handed_over
                FROM OP_EXCEPTION_RECORD
                WHERE EXCEPTION_STATUS IN ('1', '2', '3')
                ORDER BY RECORD_TIME
            """)
            
            result = session.execute(sql)
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
            
            # 查询开展中的重过载（OC_OVER_LOAD_LINE_LOG，FEEDER_STATUS 0/1为开展中）
            sql = text("""
                SELECT 
                    MK_ID as record_id,
                    WORK_NO as overload_no,
                    '' as overload_type,
                    '' as equipment_name,
                    LOAD_TIME as record_time,
                    LOAD_TIME as expected_restore_time,
                    FEEDER_STATUS as status,
                    '' as operator_name,
                    '重过载' as task_name,
                    1 as is_unresolved
                FROM OC_OVER_LOAD_LINE_LOG
                WHERE FEEDER_STATUS IN ('0', '1')
                ORDER BY RECORD_TIME
            """)
            
            result = session.execute(sql)
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
    
    @staticmethod
    def allocate_protect_task(record: Dict) -> Dict:
        """
        分配保供电任务工作量到各班次
        
        业务规则：
        - 保供电任务按日统计，统一计入早班
        - 开展中/已终结各统计为1单
        
        参数：
            record: 保供电记录字典
            
        返回：分配结果字典
        """
        try:
            in_progress_count = 1 if record.get("status_category") == "in_progress" else 0
            completed_count = 1 if record.get("status_category") == "completed" else 0
            
            result = {
                "record_id": record.get("record_id", ""),
                "task_no": record.get("task_no", ""),
                "task_name": record.get("task_name", "保供电"),
                "task_category": record.get("task_category", "A5"),
                "status_category": record.get("status_category", "unknown"),
                "total_count": 1,
                "in_progress_count": in_progress_count,
                "completed_count": completed_count,
                "shift_allocation": {
                    "morning": 1,
                    "afternoon": 0,
                    "night": 0
                },
                "equivalent": 0.0
            }
            
            return result
            
        except Exception as e:
            logger.error(f"分配保供电任务失败: {e}")
            return {
                "record_id": record.get("record_id", ""),
                "task_name": "保供电",
                "task_category": "A5",
                "total_count": 0,
                "in_progress_count": 0,
                "completed_count": 0,
                "shift_allocation": {"morning": 0, "afternoon": 0, "night": 0},
                "equivalent": 0.0
            }


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
        protect_records = PlanWorkloadDatabase.collect_protect_feeder_workload(target_date)
        
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
            "protect": {
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
        
        # 2.5 分配保供电任务
        for record in protect_records:
            allocated = WorkloadAllocator.allocate_protect_task(record)
            allocation_results["protect"]["records"].append(allocated)
            
            # 更新保供电汇总
            allocation_results["protect"]["summary"]["total"] += allocated["total_count"]
            allocation_results["protect"]["summary"]["in_progress"] += allocated["in_progress_count"]
            allocation_results["protect"]["summary"]["completed"] += allocated["completed_count"]
            allocation_results["protect"]["summary"]["morning"] += allocated["shift_allocation"]["morning"]
            allocation_results["protect"]["summary"]["afternoon"] += allocated["shift_allocation"]["afternoon"]
            allocation_results["protect"]["summary"]["night"] += allocated["shift_allocation"]["night"]
            
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
        protect_records = PlanWorkloadDatabase.collect_protect_feeder_workload(today_str)
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
            "protect": {
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
        
        # 分配保供电任务
        for record in protect_records:
            allocated = WorkloadAllocator.allocate_protect_task(record)
            plan_allocation_results["protect"]["records"].append(allocated)
            
            # 更新汇总
            plan_allocation_results["protect"]["summary"]["total"] += allocated["total_count"]
            plan_allocation_results["protect"]["summary"]["in_progress"] += allocated["in_progress_count"]
            plan_allocation_results["protect"]["summary"]["completed"] += allocated["completed_count"]
            plan_allocation_results["protect"]["summary"]["morning"] += allocated["shift_allocation"]["morning"]
            plan_allocation_results["protect"]["summary"]["afternoon"] += allocated["shift_allocation"]["afternoon"]
            plan_allocation_results["protect"]["summary"]["night"] += allocated["shift_allocation"]["night"]
            
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
        
        # 5. 计算各模块业务量
        module_business = {
            "labels": ["周计划", "设备投退", "跳闸", "缺陷", "重过载", "保供电", "检修业务", "方式单"],
            "values": [
                len(weekly_plan_records),
                len(equipment_records),
                len(fault_records),
                len(defect_records),
                len(overload_records),
                len(protect_records),
                len(maintenance_records),
                len(transfer_records)
            ]
        }
        
        # 6. 合并结果
        dashboard_data = {
            "target_date": target_date,
            "pre_analyze": pre_analyze,
            "plan_workload": plan_allocation_results,
            "non_plan_workload": non_plan_allocation_results,
            "moduleBusiness": module_business,
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
