"""
工作量自动统计看板模块 - 配网调度业务量智能预测系统

功能：
1. 实时工作量统计（按小时粒度）
2. 计划任务/非计划任务权重计算
3. 工作当量计算
4. 人力资源建议生成
5. 实时工作看板输出

数据来源：
- OMS系统调度工作台数据库
- 检修业务、方式单、周计划、新设备投运
- 故障日志、缺陷记录、重过载、保供电
- 操作票系统

参考文档：
- 潮汐值班-工作量自动统计看板.docx
- 配网调度运行管理工作量实时看板系统-待定稿.doc
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from langchain.tools import tool, ToolRuntime
from coze_coding_utils.runtime_ctx.context import new_context


# ============================================================
# 权重配置
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
        self.task_type = data.get("task_type", "")  # 计划/非计划
        self.task_category = data.get("task_category", "")  # A1_phone, B1_success 等
        self.task_name = data.get("task_name", "")
        self.order_type = data.get("order_type", "")  # 电话令/网络令
        self.module = data.get("module", "")  # OMS模块来源
        self.start_time = data.get("start_time", "")
        self.end_time = data.get("end_time", "")
        self.status = data.get("status", "")  # 待执行/执行中/已终结
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
    - C5 班组人员工作当量: 人均人力资源当量(默认1.3) * 当值人数 * 1.5
    - C6 是否超人员当量: C4 >= C5*1.5 时为"是"
    - C7 需增派人员数: (C4/人均人力资源当量*1.5) - 当值人数，四舍五入取整
    """
    
    def __init__(self, hour: str):
        self.hour = hour  # 格式: "2026-03-26 10:00"
        self.plan_tasks: List[WorkloadRecord] = []
        self.non_plan_tasks: List[WorkloadRecord] = []
        
        # C1-C3 任务计数
        self.plan_count = 0  # C1 计划任务数
        self.non_plan_count = 0  # C2 非计划任务数
        self.total_count = 0  # C3 总任务数
        
        # C4 工作当量
        self.plan_equivalent = 0.0  # 计划工作当量 (A7)
        self.non_plan_equivalent = 0.0  # 非计划工作当量 (B6)
        self.total_equivalent = 0.0  # C4 总工作当量
        
        # C5-C7 人员相关
        self.staff_count = 0  # 当值人数
        self.staff_capacity = 0.0  # C5 人员工作当量
        self.is_overload = False  # C6 是否超负荷
        self.need_extra_staff = 0  # C7 需增派人数
    
    def calculate(self, hr_capacity: float = DEFAULT_HR_CAPACITY):
        """
        计算工作量当量和人力资源建议
        
        公式说明：
        - A7 计划任务当量 = A1*权重 + A2*权重 + A3*权重 + A4*权重 + A5*权重 + A6*权重
        - B6 非计划任务当量 = B1*权重 + B2*权重 + B3*权重 + B4*权重
        - C4 = A7 + B6
        - C5 = 人均当量(1.3) * 当值人数
        - C6: C4 >= C5 * 1.5 时为"是"
        - C7: round(C4 / (人均当量 * 1.5) - 当值人数)
        """
        # C1: 计算计划任务数和当量 (A7)
        self.plan_count = sum(t.count for t in self.plan_tasks)
        self.plan_equivalent = sum(t.count * t.weight for t in self.plan_tasks)
        
        # C2: 计算非计划任务数和当量 (B6)
        self.non_plan_count = sum(t.count for t in self.non_plan_tasks)
        self.non_plan_equivalent = sum(t.count * t.weight for t in self.non_plan_tasks)
        
        # C3: 总任务数
        self.total_count = self.plan_count + self.non_plan_count
        
        # C4: 总工作当量
        self.total_equivalent = self.plan_equivalent + self.non_plan_equivalent
        
        # C5: 人员工作当量 = 人均当量 * 当值人数
        self.staff_capacity = self.staff_count * hr_capacity
        
        # C6: 是否超负荷 (工作当量 >= 人员当量 * 1.5)
        overload_threshold = self.staff_capacity * OVERLOAD_FACTOR
        self.is_overload = self.total_equivalent >= overload_threshold
        
        # C7: 需增派人数
        # 公式: (C4 / 人均当量 * 1.5) - 当值人数，四舍五入取整
        if self.staff_count > 0:
            required_staff = self.total_equivalent / (hr_capacity * OVERLOAD_FACTOR)
            self.need_extra_staff = max(0, round(required_staff - self.staff_count))
        else:
            self.need_extra_staff = round(self.total_equivalent / (hr_capacity * OVERLOAD_FACTOR))
    
    def to_dict(self) -> Dict:
        return {
            "hour": self.hour,
            "plan_count": self.plan_count,  # C1
            "non_plan_count": self.non_plan_count,  # C2
            "total_count": self.total_count,  # C3
            "plan_equivalent": round(self.plan_equivalent, 2),  # A7
            "non_plan_equivalent": round(self.non_plan_equivalent, 2),  # B6
            "total_equivalent": round(self.total_equivalent, 2),  # C4
            "staff_count": self.staff_count,
            "staff_capacity": round(self.staff_capacity, 2),  # C5
            "is_overload": self.is_overload,  # C6
            "need_extra_staff": self.need_extra_staff,  # C7
            "plan_tasks": [t.to_dict() for t in self.plan_tasks],
            "non_plan_tasks": [t.to_dict() for t in self.non_plan_tasks]
        }


# ============================================================
# 数据采集模块
# ============================================================

class WorkloadDataCollector:
    """
    工作量数据采集器
    
    从数据库采集各类工作量数据
    """
    
    @staticmethod
    def _get_db_session():
        """获取数据库会话"""
        from storage.database.db import get_session, is_database_connected
        if not is_database_connected():
            return None
        return get_session()
    
    @staticmethod
    def collect_plan_tasks(target_date: str) -> List[WorkloadRecord]:
        """
        采集计划任务数据
        
        数据来源表（待确认）：
        - maintenance_records: 检修业务表
        - transfer_orders: 方式单/转供电表
        - weekly_plans: 周计划表
        - equipment_operations: 设备投退表
        """
        session = WorkloadDataCollector._get_db_session()
        records = []
        
        if session:
            try:
                from sqlalchemy import text
                
                # 采集检修业务（停电/复电）
                sql = text("""
                    SELECT 
                        'plan' as task_type,
                        CASE 
                            WHEN order_type = 'phone' THEN 'A1_phone'
                            ELSE 'A1_network'
                        END as task_category,
                        '停电' as task_name,
                        order_type,
                        '停电检修' as module,
                        start_time,
                        end_time,
                        status,
                        1 as count
                    FROM maintenance_records
                    WHERE DATE(start_time) = :target_date
                      AND operation_type = 'power_off'
                    
                    UNION ALL
                    
                    SELECT 
                        'plan' as task_type,
                        CASE 
                            WHEN order_type = 'phone' THEN 'A2_phone'
                            ELSE 'A2_network'
                        END as task_category,
                        '复电' as task_name,
                        order_type,
                        '停电检修' as module,
                        start_time,
                        end_time,
                        status,
                        1 as count
                    FROM maintenance_records
                    WHERE DATE(start_time) = :target_date
                      AND operation_type = 'power_on'
                """)
                result = session.execute(sql, {"target_date": target_date})
                for row in result:
                    data = dict(row._mapping)
                    # 添加权重
                    category = data.get("task_category", "")
                    if category in WORKLOAD_WEIGHTS["plan_task"]["items"]:
                        data["weight"] = WORKLOAD_WEIGHTS["plan_task"]["items"][category]["weight"]
                    records.append(WorkloadRecord(data))
                
            except Exception as e:
                import logging
                logging.error(f"采集计划任务数据失败: {e}")
            finally:
                session.close()
        else:
            # 返回模拟数据用于测试
            records = WorkloadDataCollector._generate_mock_plan_tasks(target_date)
        
        return records
    
    @staticmethod
    def collect_non_plan_tasks(target_date: str) -> List[WorkloadRecord]:
        """
        采集非计划任务数据
        
        数据来源表（待确认）：
        - fault_logs: 故障日志表
        - defect_records: 缺陷记录表
        - overload_records: 重过载记录表
        - power_supply_protection: 保供电记录表
        """
        session = WorkloadDataCollector._get_db_session()
        records = []
        
        if session:
            try:
                from sqlalchemy import text
                
                # 采集故障日志
                sql = text("""
                    SELECT 
                        'non_plan' as task_type,
                        CASE 
                            WHEN reclose_result = 'success' THEN 'B1_success'
                            WHEN fault_type = 'known' THEN 'B1_fail_known'
                            ELSE 'B1_fail_unknown'
                        END as task_category,
                        '跳闸故障' as task_name,
                        '' as order_type,
                        '故障日志' as module,
                        fault_time as start_time,
                        restore_time as end_time,
                        status,
                        1 as count
                    FROM fault_logs
                    WHERE DATE(fault_time) = :target_date
                """)
                result = session.execute(sql, {"target_date": target_date})
                for row in result:
                    data = dict(row._mapping)
                    category = data.get("task_category", "")
                    if category in WORKLOAD_WEIGHTS["non_plan_task"]["items"]:
                        data["weight"] = WORKLOAD_WEIGHTS["non_plan_task"]["items"][category]["weight"]
                    records.append(WorkloadRecord(data))
                
            except Exception as e:
                import logging
                logging.error(f"采集非计划任务数据失败: {e}")
            finally:
                session.close()
        else:
            # 返回模拟数据用于测试
            records = WorkloadDataCollector._generate_mock_non_plan_tasks(target_date)
        
        return records
    
    @staticmethod
    def get_current_staff_count() -> int:
        """
        获取当前当值人数
        
        从交接班记录中获取"交班状态"为当值中的所有人员人数
        """
        session = WorkloadDataCollector._get_db_session()
        
        if session:
            try:
                from sqlalchemy import text
                
                # 从排班记录表获取当前时段的当值人数
                sql = text("""
                    SELECT COUNT(DISTINCT USER_ID) as staff_count
                    FROM work_schedule_recode
                    WHERE SCHEDULE_DATE = CURDATE()
                      AND STATUS IN (1, 2)
                      AND HOUR(NOW()) BETWEEN 
                          CASE SHIFT_TYPE 
                              WHEN 1 THEN 0 WHEN 2 THEN 8 WHEN 3 THEN 16 
                          END
                          AND CASE SHIFT_TYPE 
                              WHEN 1 THEN 8 WHEN 2 THEN 16 WHEN 3 THEN 24 
                          END
                """)
                result = session.execute(sql)
                row = result.fetchone()
                if row:
                    return row[0]
                
            except Exception as e:
                import logging
                logging.error(f"获取当值人数失败: {e}")
            finally:
                session.close()
        
        # 模拟数据
        return 4  # 默认4人当值
    
    @staticmethod
    def _generate_mock_plan_tasks(target_date: str) -> List[WorkloadRecord]:
        """生成模拟计划任务数据"""
        import random
        
        records = []
        base_time = datetime.strptime(target_date, "%Y-%m-%d")
        
        # 模拟停电任务
        for i in range(random.randint(2, 5)):
            hour = random.randint(8, 17)
            category = random.choice(["A1_phone", "A1_network"])
            records.append(WorkloadRecord({
                "task_type": "plan",
                "task_category": category,
                "task_name": "停电",
                "order_type": "phone" if "phone" in category else "network",
                "module": "停电检修",
                "start_time": (base_time + timedelta(hours=hour)).strftime("%Y-%m-%d %H:%M:%S"),
                "status": random.choice(["待执行", "执行中", "已终结"]),
                "weight": WORKLOAD_WEIGHTS["plan_task"]["items"][category]["weight"],
                "count": 1
            }))
        
        # 模拟复电任务
        for i in range(random.randint(1, 4)):
            hour = random.randint(10, 20)
            category = random.choice(["A2_phone", "A2_network"])
            records.append(WorkloadRecord({
                "task_type": "plan",
                "task_category": category,
                "task_name": "复电",
                "order_type": "phone" if "phone" in category else "network",
                "module": "停电检修",
                "start_time": (base_time + timedelta(hours=hour)).strftime("%Y-%m-%d %H:%M:%S"),
                "status": random.choice(["待执行", "执行中", "已终结"]),
                "weight": WORKLOAD_WEIGHTS["plan_task"]["items"][category]["weight"],
                "count": 1
            }))
        
        # 模拟转供电
        for i in range(random.randint(0, 3)):
            hour = random.randint(9, 16)
            records.append(WorkloadRecord({
                "task_type": "plan",
                "task_category": "A3",
                "task_name": "转供电",
                "module": "转供电",
                "start_time": (base_time + timedelta(hours=hour)).strftime("%Y-%m-%d %H:%M:%S"),
                "status": random.choice(["待执行", "执行中", "已终结"]),
                "weight": WORKLOAD_WEIGHTS["plan_task"]["items"]["A3"]["weight"],
                "count": 1
            }))
        
        return records
    
    @staticmethod
    def _generate_mock_non_plan_tasks(target_date: str) -> List[WorkloadRecord]:
        """生成模拟非计划任务数据"""
        import random
        
        records = []
        base_time = datetime.strptime(target_date, "%Y-%m-%d")
        
        # 模拟跳闸故障
        for i in range(random.randint(1, 5)):
            hour = random.randint(0, 23)
            category = random.choice(["B1_success", "B1_fail_known", "B1_fail_unknown"])
            records.append(WorkloadRecord({
                "task_type": "non_plan",
                "task_category": category,
                "task_name": "跳闸故障",
                "module": "故障日志",
                "start_time": (base_time + timedelta(hours=hour)).strftime("%Y-%m-%d %H:%M:%S"),
                "status": random.choice(["处理中", "已终结"]),
                "weight": WORKLOAD_WEIGHTS["non_plan_task"]["items"][category]["weight"],
                "count": 1
            }))
        
        # 模拟故障缺陷
        for i in range(random.randint(0, 3)):
            hour = random.randint(8, 20)
            records.append(WorkloadRecord({
                "task_type": "non_plan",
                "task_category": "B2",
                "task_name": "故障缺陷",
                "module": "缺陷记录",
                "start_time": (base_time + timedelta(hours=hour)).strftime("%Y-%m-%d %H:%M:%S"),
                "status": random.choice(["处理中", "已终结"]),
                "weight": WORKLOAD_WEIGHTS["non_plan_task"]["items"]["B2"]["weight"],
                "count": 1
            }))
        
        return records


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
                task_time = datetime.strptime(task.start_time, "%Y-%m-%d %H:%M:%S")
                if target_hour_start <= task_time < target_hour_end:
                    workload.plan_tasks.append(task)
        
        for task in non_plan_tasks:
            if task.start_time:
                task_time = datetime.strptime(task.start_time, "%Y-%m-%d %H:%M:%S")
                if target_hour_start <= task_time < target_hour_end:
                    workload.non_plan_tasks.append(task)
        
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
            staff_schedule: 各时段当值人数 {8: 4, 9: 4, ...}，如未提供则自动获取
        
        返回:
            全天工作量统计结果
        """
        # 采集任务数据
        plan_tasks = WorkloadDataCollector.collect_plan_tasks(target_date)
        non_plan_tasks = WorkloadDataCollector.collect_non_plan_tasks(target_date)
        
        # 计算各时段工作量
        hourly_workloads = []
        
        # 配网调度一般工作时段 00:00 - 24:00
        for hour in range(24):
            # 获取该时段当值人数
            if staff_schedule and hour in staff_schedule:
                staff_count = staff_schedule[hour]
            else:
                staff_count = WorkloadDataCollector.get_current_staff_count()
            
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
    target_date: str = "",
    runtime: ToolRuntime = None
) -> str:
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
    ctx = runtime.context if runtime else new_context(method="get_realtime_workload_dashboard")
    
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
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "获取工作量看板数据失败"
        }, ensure_ascii=False)


@tool
def get_workload_weights_config(runtime: ToolRuntime = None) -> str:
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
    target_date: str = "",
    runtime: ToolRuntime = None
) -> str:
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
    ctx = runtime.context if runtime else new_context(method="analyze_staff_requirement")
    
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
            
            for i, item in enumerate(shortage_hours[:3]):  # 最多显示前3个
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
                "total_need_extra_staff": sum(s["shortage"] for s in shortage_hours),
                "shortage_details": shortage_hours
            },
            "recommendations": recommendations,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "人力资源分析失败"
        }, ensure_ascii=False)


@tool
def update_hr_capacity_config(
    hr_capacity: float,
    overload_factor: float = 1.5,
    runtime: ToolRuntime = None
) -> str:
    """
    更新人力资源当量配置
    
    参数：
    - hr_capacity: 人均人力资源当量 (建议范围 1.0-2.0)
    - overload_factor: 超负荷阈值系数 (建议范围 1.2-2.0)
    
    返回：配置更新结果
    """
    ctx = runtime.context if runtime else new_context(method="update_hr_capacity_config")
    
    try:
        global DEFAULT_HR_CAPACITY, OVERLOAD_FACTOR
        
        # 参数校验
        if hr_capacity < 0.5 or hr_capacity > 3.0:
            return json.dumps({
                "success": False,
                "error": "人均人力资源当量范围应为 0.5-3.0"
            }, ensure_ascii=False)
        
        if overload_factor < 1.0 or overload_factor > 3.0:
            return json.dumps({
                "success": False,
                "error": "超负荷阈值系数范围应为 1.0-3.0"
            }, ensure_ascii=False)
        
        DEFAULT_HR_CAPACITY = hr_capacity
        OVERLOAD_FACTOR = overload_factor
        
        return json.dumps({
            "success": True,
            "message": "配置更新成功",
            "new_config": {
                "hr_capacity": hr_capacity,
                "overload_factor": overload_factor
            },
            "note": "配置已更新，将应用于后续计算"
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "更新配置失败"
        }, ensure_ascii=False)


# 导出工具
__all__ = [
    "get_realtime_workload_dashboard",
    "get_workload_weights_config",
    "analyze_staff_requirement",
    "update_hr_capacity_config",
    "WORKLOAD_WEIGHTS",
    "DEFAULT_HR_CAPACITY",
    "OVERLOAD_FACTOR"
]
