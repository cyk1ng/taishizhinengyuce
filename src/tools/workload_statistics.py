"""
工作量自动统计看板模块 - 配网调度业务量智能预测系统 V3.0

功能：
1. 实时工作量统计（按早/中/夜班时间段）
2. 计划任务/非计划任务权重计算
3. 工作当量计算
4. 人力资源建议生成
5. 未来预测（基于历史数据和天气信息）
6. 智能体训练（天气与非计划工作量关联）
7. 推荐值班名单
8. 实时工作看板输出

数据来源：
- 实时分析：配网OMS系统
- 未来预测：电网管理平台 + 天气信息

时间段定义：
- 早班：08:00~14:00
- 中班：14:00~21:00
- 夜班：21:00~次日08:00

参考文档：
- 业务态势感知智能预测功能需求清单V3.docx

注意：本模块不使用任何模拟数据，所有数据均从真实数据库读取
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from langchain.tools import tool
from coze_coding_utils.runtime_ctx.context import new_context
from coze_coding_utils.log.write_log import request_context

# 配置日志
logger = logging.getLogger(__name__)


# ============================================================
# 权重配置（完全按照文档实现）
# ============================================================

WORKLOAD_WEIGHTS = {
    "plan_task": {
        "name": "计划任务",
        "description": "A7 计划任务当量 = A1*权重 + A2*权重 + A3*权重 + A4*权重 + A5*权重 + A6*权重",
        "items": {
            "A1_phone": {
                "name": "停电(电话下令)", 
                "weight": 0.5, 
                "module": "停电检修",
                "rule": "批复的停电操作开始时间为当值时段的检修单"
            },
            "A1_network": {
                "name": "停电(网络令)", 
                "weight": 0.2, 
                "module": "停电检修",
                "rule": "批复的停电操作开始时间为当值时段的检修单"
            },
            "A2_phone": {
                "name": "复电(电话令)", 
                "weight": 0.75, 
                "module": "停电检修",
                "rule": "批复的复电操作开始时间为当值时段的检修单"
            },
            "A2_network": {
                "name": "复电(网络令)", 
                "weight": 0.3, 
                "module": "停电检修",
                "rule": "批复的复电电操作开始时间为当值时段的检修单"
            },
            "A3": {
                "name": "转供电", 
                "weight": 0.2, 
                "module": "转供电",
                "rules": [
                    "批复的转出时间为当值时段",
                    "批复的恢复时间为当值时段（如果需要恢复）",
                    "如果同时满足1和2，那么任务数计为2"
                ]
            },
            "A4": {
                "name": "周计划(只带电)", 
                "weight": 0.2, 
                "module": "周计划",
                "rules": [
                    "批复的退出时间为当值时段",
                    "批复的投入时间为当值时段（如果需要投入）",
                    "如果同时满足1和2，那么任务数计为2"
                ]
            },
            "A5": {
                "name": "周计划(只投产)", 
                "weight": 0.3, 
                "module": "周计划",
                "rules": [
                    "工作开始时间及结束时间为当值时段",
                    "若周计划为带电配合投产则任务数为2"
                ]
            },
            "A6": {
                "name": "设备投退", 
                "weight": 0.75, 
                "module": "设备投退",
                "rule": "设备投退操作时间"
            },
        }
    },
    "non_plan_task": {
        "name": "非计划任务",
        "description": "B6 非计划任务当量 = B1*权重 + B2*权重 + B3*权重 + B4*权重",
        "items": {
            "B1_success": {
                "name": "跳闸重合成功", 
                "weight": 0.1, 
                "module": "故障日志",
                "rule": "跳闸时间为当值时段的故障"
            },
            "B1_fail_known": {
                "name": "跳闸重合不成功(确定故障)", 
                "weight": 0.3, 
                "module": "故障日志",
                "rules": [
                    "跳闸时间为当值时段的故障",
                    "预计恢复送电时间为当值时段的故障",
                    "如果同时满足1和2，那么任务数计算为2"
                ]
            },
            "B1_fail_unknown": {
                "name": "跳闸重合不成功(不确定故障)", 
                "weight": 0.3, 
                "module": "故障日志",
                "rules": [
                    "跳闸时间为当值时段的故障",
                    "故障不确定（无复电时间）时，此故障一直加入当值工作量",
                    "确定故障后填写预计恢复送电时间为当值的故障",
                    "如果同时满足1和2，那么任务数计算为2"
                ]
            },
            "B1_bus_ground": {
                "name": "母线接地", 
                "weight": 0.3, 
                "module": "故障日志",
                "rules": [
                    "母线接地时间为当值时段的故障",
                    "检跳后（无复电时间），此接地故障一直加入当值工作量",
                    "确定故障后填写预计恢复送电时间为当值的故障",
                    "如果同时满足1和2，那么任务数计算为2"
                ]
            },
            "B2": {
                "name": "异常缺陷", 
                "weight": 0.6, 
                "module": "缺陷记录",
                "rules": [
                    "停电时间为当值时段的任务数",
                    "预计恢复送电时间为当值时段的缺陷"
                ]
            },
            "B3": {
                "name": "重过载", 
                "weight": 0.6, 
                "module": "重过载",
                "rule": "重过载记录时间为当值时段"
            },
            "B4": {
                "name": "保电任务", 
                "weight": 0.1, 
                "module": "保供电",
                "rule": "保电记录时间为当值时段"
            },
        }
    }
}

# 人均人力资源当量（默认值，可根据实际情况调整）
DEFAULT_HR_CAPACITY = 1.3
# 超负荷阈值系数
OVERLOAD_FACTOR = 1.5


# ============================================================
# 工作量数据模型
# ============================================================

class WorkloadRecord:
    """工作量记录"""
    
    def __init__(self, data: Dict):
        self.record_id = data.get("record_id", "")
        self.task_type = data.get("task_type", "")  # plan/non_plan
        self.task_category = data.get("task_category", "")  # A1_phone, B1_success 等
        self.task_name = data.get("task_name", "")
        self.order_type = data.get("order_type", "")  # phone/network
        self.module = data.get("module", "")  # OMS模块来源
        self.start_time = data.get("start_time", "")
        self.end_time = data.get("end_time", "")
        self.status = data.get("status", "")
        self.weight = data.get("weight", 0.0)
        self.count = data.get("count", 1)
    
    def to_dict(self) -> Dict:
        return {
            "record_id": self.record_id,
            "task_type": self.task_type,
            "task_category": self.task_category,
            "task_name": self.task_name,
            "order_type": self.order_type,
            "module": self.module,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "status": self.status,
            "weight": self.weight,
            "count": self.count
        }


class HourlyWorkload:
    """小时级工作量统计
    
    统计指标说明：
    - C1 计划工作: 计算计划任务（A1至A6）该时段的任务数
    - C2 非计划工作: 计算非计划任务（B1至B4）该时段的任务数
    - C3 任务总计: C1+C2
    - C4 工作任务总当量: 各任务值*各自指标当量权重系数
    - C5 班组人员工作当量: 人均人力资源当量(默认1.3) * 当值人数
    - C6 是否超人员当量: C4 >= C5 * 1.5 时为"是"
    - C7 需增派人员数: (C4/人均人力资源当量*1.5) - 当值人数，四舍五入取整
    """
    
    def __init__(self, hour: str):
        self.hour = hour
        self.plan_tasks: List[WorkloadRecord] = []
        self.non_plan_tasks: List[WorkloadRecord] = []
        
        # C1-C3 任务计数
        self.plan_count = 0
        self.non_plan_count = 0
        self.total_count = 0
        
        # C4 工作当量
        self.plan_equivalent = 0.0
        self.non_plan_equivalent = 0.0
        self.total_equivalent = 0.0
        
        # C5-C7 人员相关
        self.staff_count = 0
        self.staff_capacity = 0.0
        self.is_overload = False
        self.need_extra_staff = 0
    
    def calculate(self, hr_capacity: float = DEFAULT_HR_CAPACITY):
        """计算工作量当量和人力资源建议"""
        # C1: 计算计划任务数和当量
        self.plan_count = sum(t.count for t in self.plan_tasks)
        self.plan_equivalent = sum(t.count * t.weight for t in self.plan_tasks)
        
        # C2: 计算非计划任务数和当量
        self.non_plan_count = sum(t.count for t in self.non_plan_tasks)
        self.non_plan_equivalent = sum(t.count * t.weight for t in self.non_plan_tasks)
        
        # C3: 总任务数
        self.total_count = self.plan_count + self.non_plan_count
        
        # C4: 总工作当量
        self.total_equivalent = self.plan_equivalent + self.non_plan_equivalent
        
        # C5: 人员工作当量
        self.staff_capacity = self.staff_count * hr_capacity
        
        # C6: 是否超负荷（只有当人员数>0且工作当量>0时才判断）
        overload_threshold = self.staff_capacity * OVERLOAD_FACTOR
        if self.staff_count > 0 and self.total_equivalent > 0:
            self.is_overload = self.total_equivalent >= overload_threshold
        else:
            self.is_overload = False
        
        # C7: 需增派人数（只有当人员数>0且工作当量>0时才计算）
        if self.staff_count > 0 and self.total_equivalent > 0:
            required_staff = self.total_equivalent / (hr_capacity * OVERLOAD_FACTOR)
            self.need_extra_staff = max(0, round(required_staff - self.staff_count))
        elif self.total_equivalent > 0 and self.staff_count == 0:
            # 无人值班但有工作，需要全部增派
            self.need_extra_staff = round(self.total_equivalent / (hr_capacity * OVERLOAD_FACTOR))
        else:
            # 无工作，不需要增派
            self.need_extra_staff = 0
    
    def to_dict(self) -> Dict:
        return {
            "hour": self.hour,
            "plan_count": self.plan_count,
            "non_plan_count": self.non_plan_count,
            "total_count": self.total_count,
            "plan_equivalent": round(self.plan_equivalent, 2),
            "non_plan_equivalent": round(self.non_plan_equivalent, 2),
            "total_equivalent": round(self.total_equivalent, 2),
            "staff_count": self.staff_count,
            "staff_capacity": round(self.staff_capacity, 2),
            "is_overload": self.is_overload,
            "need_extra_staff": self.need_extra_staff,
            "plan_tasks": [t.to_dict() for t in self.plan_tasks],
            "non_plan_tasks": [t.to_dict() for t in self.non_plan_tasks]
        }


# ============================================================
# 数据库操作模块
# ============================================================

class WorkloadDatabase:
    """工作量统计数据库操作类"""
    
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
    def collect_plan_tasks(target_date: str) -> List[WorkloadRecord]:
        """
        从数据库采集计划任务数据
        
        数据来源表（需根据实际表名调整）：
        - maintenance_records: 检修业务表
        - transfer_orders: 方式单/转供电表
        - weekly_plans: 周计划表
        - equipment_operations: 设备投退表
        """
        session = WorkloadDatabase.get_session()
        if not session:
            logger.warning("数据库未连接，返回空列表")
            return []
        
        records = []
        
        try:
            from sqlalchemy import text
            
            # 1. 采集检修业务（停电/复电）- Oracle 表 TD_OUTAGE_REPAIR_APPLY_INFO
            sql_maintenance = text("""
                SELECT 
                    MK_ID as record_id,
                    'plan' as task_type,
                    'A1_phone' as task_category,
                    '计划检修' as task_name,
                    'phone' as order_type,
                    '停电检修' as module,
                    FILL_WORK_BEGIN_DATE as start_time,
                    FILL_WORK_END_DATE as end_time,
                    FORM_STATUS as status,
                    1 as count
                FROM TD_OUTAGE_REPAIR_APPLY_INFO
                WHERE TRUNC(FILL_WORK_BEGIN_DATE) = TO_DATE(:target_date, 'YYYY-MM-DD')
                  AND FILL_OVERHAUL_TYPE IN ('JH', '计划检修')
                
                UNION ALL
                
                -- 2. 采集转供电任务
                SELECT 
                    record_id,
                    'plan' as task_type,
                    'A3' as task_category,
                    '转供电' as task_name,
                    '' as order_type,
                    '转供电' as module,
                    transfer_out_time as start_time,
                    restore_time as end_time,
                    status,
                    CASE WHEN DATE(transfer_out_time) = :target_date 
                              AND DATE(restore_time) = :target_date THEN 2 ELSE 1 END as count
                FROM transfer_orders
                WHERE DATE(transfer_out_time) = :target_date
                
                UNION ALL
                
                -- 3. 采集周计划任务
                SELECT 
                    record_id,
                    'plan' as task_type,
                    CASE WHEN plan_type = 'live_operation' THEN 'A4' ELSE 'A5' END as task_category,
                    CASE WHEN plan_type = 'live_operation' THEN '周计划(只带电)' ELSE '周计划(只投产)' END as task_name,
                    '' as order_type,
                    '周计划' as module,
                    CASE WHEN plan_type = 'live_operation' THEN quit_time ELSE work_start_time END as start_time,
                    CASE WHEN plan_type = 'live_operation' THEN restore_time ELSE work_end_time END as end_time,
                    status,
                    CASE WHEN plan_type = 'live_operation' AND DATE(quit_time) = :target_date 
                              AND DATE(restore_time) = :target_date THEN 2 
                         WHEN plan_type = 'commissioning' AND is_live_required = 1 THEN 2 
                         ELSE 1 END as count
                FROM weekly_plans
                WHERE DATE(work_start_time) = :target_date
                
                UNION ALL
                
                -- 4. 采集设备投退任务
                SELECT 
                    record_id,
                    'plan' as task_type,
                    'A6' as task_category,
                    '设备投退' as task_name,
                    '' as order_type,
                    '设备投退' as module,
                    operation_time as start_time,
                    operation_time as end_time,
                    status,
                    1 as count
                FROM equipment_operations
                WHERE DATE(operation_time) = :target_date
            """)
            
            result = session.execute(sql_maintenance, {"target_date": target_date})
            for row in result:
                data = dict(row._mapping)
                category = data.get("task_category", "")
                if category in WORKLOAD_WEIGHTS["plan_task"]["items"]:
                    data["weight"] = WORKLOAD_WEIGHTS["plan_task"]["items"][category]["weight"]
                else:
                    data["weight"] = 0.0
                records.append(WorkloadRecord(data))
            
            logger.info(f"从数据库采集计划任务 {len(records)} 条")
            
        except Exception as e:
            logger.error(f"采集计划任务数据失败: {e}")
        finally:
            if session:
                session.close()
        
        return records
    
    @staticmethod
    def collect_non_plan_tasks(target_date: str) -> List[WorkloadRecord]:
        """
        从数据库采集非计划任务数据
        
        数据来源表（需根据实际表名调整）：
        - fault_logs: 故障日志表
        - defect_records: 缺陷记录表
        - overload_records: 重过载记录表
        - power_supply_protection: 保供电记录表
        """
        session = WorkloadDatabase.get_session()
        if not session:
            logger.warning("数据库未连接，返回空列表")
            return []
        
        records = []
        
        try:
            from sqlalchemy import text
            
            # 1. 采集故障日志（跳闸）
            sql_fault = text("""
                SELECT 
                    record_id,
                    'non_plan' as task_type,
                    CASE 
                        WHEN reclose_result = 'success' THEN 'B1_success'
                        WHEN reclose_result = 'fail' AND fault_type = 'known' THEN 'B1_fail_known'
                        WHEN reclose_result = 'fail' AND fault_type = 'unknown' THEN 'B1_fail_unknown'
                        WHEN fault_type = 'bus_ground' THEN 'B1_bus_ground'
                    END as task_category,
                    CASE 
                        WHEN reclose_result = 'success' THEN '跳闸重合成功'
                        WHEN reclose_result = 'fail' AND fault_type = 'known' THEN '跳闸重合不成功(确定故障)'
                        WHEN reclose_result = 'fail' AND fault_type = 'unknown' THEN '跳闸重合不成功(不确定故障)'
                        WHEN fault_type = 'bus_ground' THEN '母线接地'
                    END as task_name,
                    '故障日志' as module,
                    fault_time as start_time,
                    expected_restore_time as end_time,
                    status,
                    CASE WHEN DATE(fault_time) = :target_date 
                              AND DATE(expected_restore_time) = :target_date THEN 2 ELSE 1 END as count
                FROM fault_logs
                WHERE DATE(fault_time) = :target_date
                   OR DATE(expected_restore_time) = :target_date
            """)
            
            result = session.execute(sql_fault, {"target_date": target_date})
            for row in result:
                data = dict(row._mapping)
                category = data.get("task_category", "")
                if category in WORKLOAD_WEIGHTS["non_plan_task"]["items"]:
                    data["weight"] = WORKLOAD_WEIGHTS["non_plan_task"]["items"][category]["weight"]
                else:
                    data["weight"] = 0.0
                records.append(WorkloadRecord(data))
            
            # 2. 采集异常缺陷
            sql_defect = text("""
                SELECT 
                    record_id,
                    'non_plan' as task_type,
                    'B2' as task_category,
                    '异常缺陷' as task_name,
                    '缺陷记录' as module,
                    fault_time as start_time,
                    expected_restore_time as end_time,
                    status,
                    CASE WHEN DATE(fault_time) = :target_date 
                              AND DATE(expected_restore_time) = :target_date THEN 2 ELSE 1 END as count
                FROM defect_records
                WHERE DATE(fault_time) = :target_date
                   OR DATE(expected_restore_time) = :target_date
            """)
            
            result = session.execute(sql_defect, {"target_date": target_date})
            for row in result:
                data = dict(row._mapping)
                data["weight"] = WORKLOAD_WEIGHTS["non_plan_task"]["items"]["B2"]["weight"]
                records.append(WorkloadRecord(data))
            
            # 3. 采集重过载记录
            sql_overload = text("""
                SELECT 
                    record_id,
                    'non_plan' as task_type,
                    'B3' as task_category,
                    '重过载' as task_name,
                    '重过载' as module,
                    record_time as start_time,
                    record_time as end_time,
                    status,
                    1 as count
                FROM overload_records
                WHERE DATE(record_time) = :target_date
            """)
            
            result = session.execute(sql_overload, {"target_date": target_date})
            for row in result:
                data = dict(row._mapping)
                data["weight"] = WORKLOAD_WEIGHTS["non_plan_task"]["items"]["B3"]["weight"]
                records.append(WorkloadRecord(data))
            
            # 4. 采集保电任务
            sql_protection = text("""
                SELECT 
                    record_id,
                    'non_plan' as task_type,
                    'B4' as task_category,
                    '保电任务' as task_name,
                    '保供电' as module,
                    start_time,
                    end_time,
                    status,
                    1 as count
                FROM power_supply_protection
                WHERE DATE(start_time) = :target_date
            """)
            
            result = session.execute(sql_protection, {"target_date": target_date})
            for row in result:
                data = dict(row._mapping)
                data["weight"] = WORKLOAD_WEIGHTS["non_plan_task"]["items"]["B4"]["weight"]
                records.append(WorkloadRecord(data))
            
            logger.info(f"从数据库采集非计划任务 {len(records)} 条")
            
        except Exception as e:
            logger.error(f"采集非计划任务数据失败: {e}")
        finally:
            if session:
                session.close()
        
        return records
    
    @staticmethod
    def get_current_staff_count() -> int:
        """
        获取当前当值人数
        
        从排班记录表获取当前时段的当值人数
        """
        session = WorkloadDatabase.get_session()
        if not session:
            logger.warning("数据库未连接，无法获取当值人数")
            return 0
        
        try:
            from sqlalchemy import text
            
            # 从排班记录表获取当前时段的当值人数
            sql = text("""
                SELECT COUNT(DISTINCT USER_ID) as staff_count
                FROM work_schedule_recode
                WHERE SCHEDULE_DATE = CURDATE()
                  AND STATUS IN (1, 2)
                  AND HOUR(NOW()) >= CASE SHIFT_TYPE 
                                      WHEN 1 THEN 0 WHEN 2 THEN 8 WHEN 3 THEN 16 
                                  END
                  AND HOUR(NOW()) < CASE SHIFT_TYPE 
                                      WHEN 1 THEN 8 WHEN 2 THEN 16 WHEN 3 THEN 24 
                                  END
            """)
            result = session.execute(sql)
            row = result.fetchone()
            if row:
                count = row[0]
                logger.info(f"获取当值人数: {count}")
                return count
            
        except Exception as e:
            logger.error(f"获取当值人数失败: {e}")
        finally:
            if session:
                session.close()
        
        return 0
    
    @staticmethod
    def get_hourly_staff_count(target_date: str, hour: int) -> int:
        """
        获取指定时段当值人数
        """
        session = WorkloadDatabase.get_session()
        if not session:
            return 0
        
        try:
            from sqlalchemy import text
            
            sql = text("""
                SELECT COUNT(DISTINCT USER_ID) as staff_count
                FROM work_schedule_recode
                WHERE SCHEDULE_DATE = :target_date
                  AND STATUS IN (1, 2)
                  AND :hour >= CASE SHIFT_TYPE 
                                  WHEN 1 THEN 0 WHEN 2 THEN 8 WHEN 3 THEN 16 
                              END
                  AND :hour < CASE SHIFT_TYPE 
                                  WHEN 1 THEN 8 WHEN 2 THEN 16 WHEN 3 THEN 24 
                              END
            """)
            result = session.execute(sql, {"target_date": target_date, "hour": hour})
            row = result.fetchone()
            if row:
                return row[0]
            
        except Exception as e:
            logger.error(f"获取时段({hour})当值人数失败: {e}")
        finally:
            if session:
                session.close()
        
        return 0


# ============================================================
# 工作量计算引擎
# ============================================================

class WorkloadCalculator:
    """工作量计算引擎"""
    
    def __init__(self, hr_capacity: float = DEFAULT_HR_CAPACITY):
        self.hr_capacity = hr_capacity
    
    def calculate_hourly_workload(
        self,
        target_date: str,
        hour: int,
        plan_tasks: List[WorkloadRecord],
        non_plan_tasks: List[WorkloadRecord],
        staff_count: int
    ) -> HourlyWorkload:
        """计算指定小时的工作量"""
        
        hour_str = f"{target_date} {hour:02d}:00"
        workload = HourlyWorkload(hour_str)
        workload.staff_count = staff_count
        
        # 过滤该小时段内的任务
        target_hour_start = datetime.strptime(f"{target_date} {hour:02d}:00:00", "%Y-%m-%d %H:%M:%S")
        target_hour_end = target_hour_start + timedelta(hours=1)
        
        for task in plan_tasks:
            if task.start_time:
                try:
                    task_time = datetime.strptime(task.start_time, "%Y-%m-%d %H:%M:%S")
                    if target_hour_start <= task_time < target_hour_end:
                        workload.plan_tasks.append(task)
                except:
                    pass
        
        for task in non_plan_tasks:
            if task.start_time:
                try:
                    task_time = datetime.strptime(task.start_time, "%Y-%m-%d %H:%M:%S")
                    if target_hour_start <= task_time < target_hour_end:
                        workload.non_plan_tasks.append(task)
                except:
                    pass
        
        # 计算当量和人力资源建议
        workload.calculate(self.hr_capacity)
        
        return workload
    
    def calculate_daily_workload(
        self,
        target_date: str,
        staff_schedule: Optional[Dict[int, int]] = None
    ) -> Dict:
        """
        计算全天工作量统计
        
        参数:
            target_date: 目标日期 (YYYY-MM-DD)
            staff_schedule: 各时段当值人数 {8: 4, 9: 4, ...}，如未提供则从数据库获取
        
        返回:
            全天工作量统计结果
        """
        # 从数据库采集任务数据
        plan_tasks = WorkloadDatabase.collect_plan_tasks(target_date)
        non_plan_tasks = WorkloadDatabase.collect_non_plan_tasks(target_date)
        
        # 计算各时段工作量
        hourly_workloads = []
        
        # 24小时统计
        for hour in range(24):
            # 获取该时段当值人数
            if staff_schedule and hour in staff_schedule:
                staff_count = staff_schedule[hour]
            else:
                staff_count = WorkloadDatabase.get_hourly_staff_count(target_date, hour)
            
            hourly = self.calculate_hourly_workload(
                target_date, hour, plan_tasks, non_plan_tasks, staff_count
            )
            hourly_workloads.append(hourly)
        
        # 汇总统计
        total_plan_count = sum(h.plan_count for h in hourly_workloads)
        total_non_plan_count = sum(h.non_plan_count for h in hourly_workloads)
        total_plan_equivalent = sum(h.plan_equivalent for h in hourly_workloads)
        total_non_plan_equivalent = sum(h.non_plan_equivalent for h in hourly_workloads)
        
        # 找出超负荷时段
        overload_hours = [h.hour for h in hourly_workloads if h.is_overload]
        total_need_extra = sum(h.need_extra_staff for h in hourly_workloads if h.is_overload)
        
        # 找出峰值时段
        peak_hour = max(hourly_workloads, key=lambda h: h.total_equivalent)
        
        return {
            "target_date": target_date,
            "summary": {
                "total_plan_count": total_plan_count,
                "total_non_plan_count": total_non_plan_count,
                "total_count": total_plan_count + total_non_plan_count,
                "total_plan_equivalent": round(total_plan_equivalent, 2),
                "total_non_plan_equivalent": round(total_non_plan_equivalent, 2),
                "total_equivalent": round(total_plan_equivalent + total_non_plan_equivalent, 2),
                "overload_hours": overload_hours,
                "overload_count": len(overload_hours),
                "total_need_extra_staff": total_need_extra,
                "peak_hour": peak_hour.hour,
                "peak_equivalent": round(peak_hour.total_equivalent, 2)
            },
            "hourly_details": [h.to_dict() for h in hourly_workloads],
            "hr_capacity_config": {
                "default_hr_capacity": self.hr_capacity,
                "overload_factor": OVERLOAD_FACTOR
            }
        }


# ============================================================
# 工具函数
# ============================================================

@tool
def get_realtime_workload_dashboard(
    target_date: str = "") -> str:
    """
    获取实时工作量看板数据
    
    功能：
    - 统计各时段的计划/非计划任务数
    - 计算工作任务当量
    - 判断是否超人员当量
    - 给出需增派人员建议
    
    参数：
    - target_date: 目标日期 (YYYY-MM-DD)，默认今天
    
    返回：工作量看板数据JSON字符串
    """
    ctx = request_context.get() or new_context(method="get_realtime_workload_dashboard")
    
    try:
        if not target_date:
            target_date = datetime.now().strftime("%Y-%m-%d")
        
        calculator = WorkloadCalculator()
        result = calculator.calculate_daily_workload(target_date)
        
        # 添加生成时间
        result["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        result["success"] = True
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"获取工作量看板数据失败: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "获取工作量看板数据失败"
        }, ensure_ascii=False)


@tool
def get_workload_weights_config() -> str:
    """
    获取工作量权重配置
    
    返回计划任务和非计划任务的权重配置信息
    """
    return json.dumps({
        "success": True,
        "weights": WORKLOAD_WEIGHTS,
        "hr_capacity": {
            "default": DEFAULT_HR_CAPACITY,
            "overload_factor": OVERLOAD_FACTOR,
            "description": {
                "default_hr_capacity": "人均人力资源当量，默认1.3",
                "overload_factor": "超负荷阈值系数，当工作当量 >= 人员当量 * 1.5 时判定超负荷"
            }
        }
    }, ensure_ascii=False, indent=2)


@tool
def analyze_staff_requirement(
    target_date: str = "") -> str:
    """
    分析人力资源需求
    
    基于工作量预测分析各时段人力资源需求：
    - 计算各时段所需人员数
    - 识别人员不足时段
    - 给出增派人员建议
    
    参数：
    - target_date: 目标日期 (YYYY-MM-DD)
    
    返回：人力资源分析报告JSON字符串
    """
    ctx = request_context.get() or new_context(method="analyze_staff_requirement")
    
    try:
        if not target_date:
            target_date = datetime.now().strftime("%Y-%m-%d")
        
        calculator = WorkloadCalculator()
        workload_result = calculator.calculate_daily_workload(target_date)
        
        # 分析人力资源需求
        hourly_details = workload_result["hourly_details"]
        
        # 找出需要增派人员的时段
        shortage_hours = []
        for hour_data in hourly_details:
            if hour_data["is_overload"]:
                shortage_hours.append({
                    "hour": hour_data["hour"],
                    "current_staff": hour_data["staff_count"],
                    "workload_equivalent": hour_data["total_equivalent"],
                    "staff_capacity": hour_data["staff_capacity"],
                    "shortage": hour_data["need_extra_staff"],
                    "recommendation": f"建议增派 {hour_data['need_extra_staff']} 人"
                })
        
        # 生成建议
        recommendations = []
        if shortage_hours:
            recommendations.append(f"今日共有 {len(shortage_hours)} 个时段人员不足")
            
            # 按短缺程度排序
            shortage_hours.sort(key=lambda x: x["shortage"], reverse=True)
            
            for i, item in enumerate(shortage_hours[:3]):
                recommendations.append(
                    f"【紧急】{item['hour']} 时段需增派 {item['shortage']} 人，"
                    f"当前{item['current_staff']}人，工作当量{item['workload_equivalent']}"
                )
        else:
            recommendations.append("今日各时段人力资源充足")
        
        result = {
            "success": True,
            "target_date": target_date,
            "analysis": {
                "total_shortage_hours": len(shortage_hours),
                "shortage_hours": shortage_hours,
                "recommendations": recommendations
            },
            "workload_summary": workload_result["summary"]
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"人力资源需求分析失败: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "人力资源需求分析失败"
        }, ensure_ascii=False)


@tool
def get_workload_by_module(
    target_date: str = "",
    module: str = "") -> str:
    """
    按业务模块统计工作量
    
    参数：
    - target_date: 目标日期 (YYYY-MM-DD)
    - module: 业务模块名称 (检修业务/周计划/方式单/故障日志/缺陷记录/重过载/保供电)
    
    返回：按模块分类的工作量统计
    """
    try:
        if not target_date:
            target_date = datetime.now().strftime("%Y-%m-%d")
        
        # 采集数据
        plan_tasks = WorkloadDatabase.collect_plan_tasks(target_date)
        non_plan_tasks = WorkloadDatabase.collect_non_plan_tasks(target_date)
        
        # 按模块分组统计
        module_stats = {}
        
        for task in plan_tasks + non_plan_tasks:
            mod = task.module
            if module and mod != module:
                continue
                
            if mod not in module_stats:
                module_stats[mod] = {
                    "module": mod,
                    "task_count": 0,
                    "equivalent": 0.0,
                    "tasks": []
                }
            
            module_stats[mod]["task_count"] += task.count
            module_stats[mod]["equivalent"] += task.count * task.weight
            module_stats[mod]["tasks"].append(task.to_dict())
        
        # 计算总计
        total_count = sum(s["task_count"] for s in module_stats.values())
        total_equivalent = sum(s["equivalent"] for s in module_stats.values())
        
        result = {
            "success": True,
            "target_date": target_date,
            "module": module if module else "全部",
            "summary": {
                "total_task_count": total_count,
                "total_equivalent": round(total_equivalent, 2)
            },
            "modules": {k: {
                "module": v["module"],
                "task_count": v["task_count"],
                "equivalent": round(v["equivalent"], 2),
                "task_count": v["task_count"]
            } for k, v in module_stats.items()}
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"按模块统计工作量失败: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "按模块统计工作量失败"
        }, ensure_ascii=False)
