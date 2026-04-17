"""
测试计划工作量统计功能的测试数据
"""
from datetime import datetime, timedelta
import json

# 测试数据示例
test_maintenance_records = [
    {
        "record_id": 1,
        "work_order_no": "WO2025012001",
        "operation_type": "power_off",
        "order_type": "phone",
        "equipment_name": "10kV线路A",
        "approved_start_time": "2025-01-20 09:00:00",  # 早班
        "approved_end_time": "2025-01-20 13:00:00",
        "status": "pending",
        "operator_name": "张三"
    },
    {
        "record_id": 2,
        "work_order_no": "WO2025012002",
        "operation_type": "power_on",
        "order_type": "network",
        "equipment_name": "10kV线路B",
        "approved_start_time": "2025-01-20 08:00:00",
        "approved_end_time": "2025-01-20 22:00:00",  # 夜班（21:00后）
        "status": "executing",
        "operator_name": "李四"
    },
    {
        "record_id": 3,
        "work_order_no": "WO2025012003",
        "operation_type": "power_off",
        "order_type": "phone",
        "equipment_name": "10kV线路C",
        "approved_start_time": "2025-01-20 15:00:00",  # 中班
        "approved_end_time": "2025-01-20 19:00:00",
        "status": "pending",
        "operator_name": "王五"
    }
]

test_equipment_operations = [
    {
        "operation_id": 101,
        "operation_no": "EO2025012001",
        "operation_type": "put_into_service",
        "equipment_name": "断路器#1",
        "approved_start_time": "2025-01-20 10:00:00",  # 早班
        "approved_end_time": "2025-01-20 12:00:00",
        "status": "pending",
        "operator_name": "赵六"
    },
    {
        "operation_id": 102,
        "operation_no": "EO2025012002",
        "operation_type": "take_out_of_service",
        "equipment_name": "断路器#2",
        "approved_start_time": "2025-01-20 08:00:00",
        "approved_end_time": "2025-01-20 23:00:00",  # 夜班（21:00后）
        "status": "executing",
        "operator_name": "钱七"
    }
]

test_transfer_orders = [
    {
        "order_id": 201,
        "order_no": "TO2025012001",
        "transfer_type": "normal",
        "equipment_name": "变压器#1",
        "transfer_out_time": "2025-01-20 11:00:00",  # 早班
        "transfer_back_time": "2025-01-20 18:00:00",
        "status": "pending",
        "operator_name": "孙八"
    },
    {
        "order_id": 202,
        "order_no": "TO2025012002",
        "transfer_type": "emergency",
        "equipment_name": "变压器#2",
        "transfer_out_time": "2025-01-20 22:00:00",  # 夜班（21:00后）
        "transfer_back_time": "2025-01-21 07:00:00",  # 次日08:00前
        "status": "executing",
        "operator_name": "周九"
    },
    {
        "order_id": 203,
        "order_no": "TO2025012003",
        "transfer_type": "normal",
        "equipment_name": "变压器#3",
        "transfer_out_time": "2025-01-20 16:00:00",  # 中班
        "transfer_back_time": "2025-01-20 20:00:00",
        "status": "pending",
        "operator_name": "吴十"
    }
]

test_weekly_plans = [
    {
        "plan_id": 301,
        "plan_no": "WP2025012001",
        "plan_type": "live_operation",
        "plan_name": "带电作业计划1",
        "equipment_name": "10kV线路D",
        "approved_start_time": "2025-01-20 09:00:00",  # 早班开始
        "approved_end_time": "2025-01-20 17:00:00",    # 非跨天
        "status": "executing",
        "operator_name": "郑十一",
        "is_live_coop": 1
    },
    {
        "plan_id": 302,
        "plan_no": "WP2025012002",
        "plan_type": "commissioning",
        "plan_name": "投产计划1",
        "equipment_name": "10kV线路E",
        "approved_start_time": "2025-01-20 20:00:00",  # 开始时接近中班结束
        "approved_end_time": "2025-01-21 04:00:00",    # 跨天，纳入夜班
        "status": "executing",
        "operator_name": "王十二",
        "is_live_coop": 1
    },
    {
        "plan_id": 303,
        "plan_no": "WP2025012003",
        "plan_type": "live_operation",
        "plan_name": "带电作业计划2",
        "equipment_name": "10kV线路F",
        "approved_start_time": "2025-01-20 13:00:00",  # 中班开始
        "approved_end_time": "2025-01-20 14:30:00",    # 非跨天
        "status": "executing",
        "operator_name": "李十三",
        "is_live_coop": 0
    }
]

# 保存测试数据到文件
test_data = {
    "maintenance_records": test_maintenance_records,
    "equipment_operations": test_equipment_operations,
    "transfer_orders": test_transfer_orders,
    "weekly_plans": test_weekly_plans
}

with open("assets/plan_workload_test_data.json", "w", encoding="utf-8") as f:
    json.dump(test_data, f, ensure_ascii=False, indent=2)

print("测试数据已保存到 assets/plan_workload_test_data.json")
print("\n预期结果：")
print("-" * 60)

# 计算预期结果
expected = {
    "morning": 0,
    "afternoon": 0,
    "night": 0
}

# 检修任务
expected["morning"] += 1  # record_id=1, 早班09:00开始
expected["night"] += 1    # record_id=2, 22:00结束
expected["afternoon"] += 1  # record_id=3, 15:00开始

# 设备投退
expected["morning"] += 1  # record_id=101, 10:00开始
expected["night"] += 1    # record_id=102, 23:00结束

# 转供电
expected["morning"] += 1  # record_id=201, 11:00开始
expected["night"] += 1    # record_id=202, 22:00开始
expected["afternoon"] += 1  # record_id=203, 16:00开始

# 周计划（非提前分析模式）
expected["morning"] += 2  # record_id=301, 09:00开始, 带电配合投产=2
expected["night"] += 2    # record_id=302, 跨天, 投产配合带电=2
expected["afternoon"] += 1  # record_id=303, 13:00开始, 只带电=1

print(f"早班 (08:00-14:00): {expected['morning']} 项")
print(f"中班 (14:00-21:00): {expected['afternoon']} 项")
print(f"夜班 (21:00-次日08:00): {expected['night']} 项")
print(f"总计: {expected['morning'] + expected['afternoon'] + expected['night']} 项")
print("\n详细分配：")
print("- 计划检修: 早班1项, 中班1项, 夜班1项")
print("- 设备投退: 早班1项, 夜班1项")
print("- 转供电: 早班1项, 中班1项, 夜班1项")
print("- 周计划: 早班2项, 中班1项, 夜班2项")
