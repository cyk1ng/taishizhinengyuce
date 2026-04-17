"""
使用SQLite内存数据库测试计划工作量统计功能
"""
import sqlite3
from datetime import datetime, timedelta
import json

def create_sqlite_test_db():
    """创建SQLite测试数据库"""
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    
    # 创建计划检修表
    cursor.execute('''
        CREATE TABLE maintenance_records (
            RECORD_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            WORK_ORDER_NO TEXT NOT NULL,
            OPERATION_TYPE TEXT NOT NULL,
            ORDER_TYPE TEXT NOT NULL,
            EQUIPMENT_NAME TEXT NOT NULL,
            APPROVED_START_TIME TEXT NOT NULL,
            APPROVED_END_TIME TEXT NOT NULL,
            ACTUAL_START_TIME TEXT,
            ACTUAL_END_TIME TEXT,
            STATUS TEXT NOT NULL,
            OPERATOR_NAME TEXT
        )
    ''')
    
    # 创建设备投退表
    cursor.execute('''
        CREATE TABLE equipment_operations (
            OPERATION_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            OPERATION_NO TEXT NOT NULL,
            OPERATION_TYPE TEXT NOT NULL,
            EQUIPMENT_NAME TEXT NOT NULL,
            APPROVED_START_TIME TEXT NOT NULL,
            APPROVED_END_TIME TEXT NOT NULL,
            STATUS TEXT NOT NULL,
            OPERATOR_NAME TEXT
        )
    ''')
    
    # 创建转供电表
    cursor.execute('''
        CREATE TABLE transfer_orders (
            ORDER_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            ORDER_NO TEXT NOT NULL,
            TRANSFER_TYPE TEXT NOT NULL,
            EQUIPMENT_NAME TEXT NOT NULL,
            TRANSFER_OUT_TIME TEXT NOT NULL,
            TRANSFER_BACK_TIME TEXT NOT NULL,
            STATUS TEXT NOT NULL,
            OPERATOR_NAME TEXT
        )
    ''')
    
    # 创建周计划表
    cursor.execute('''
        CREATE TABLE weekly_plans (
            PLAN_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            PLAN_NO TEXT NOT NULL,
            PLAN_TYPE TEXT NOT NULL,
            PLAN_NAME TEXT NOT NULL,
            EQUIPMENT_NAME TEXT NOT NULL,
            APPROVED_START_TIME TEXT NOT NULL,
            APPROVED_END_TIME TEXT NOT NULL,
            WORK_START_TIME TEXT,
            WORK_END_TIME TEXT,
            STATUS TEXT NOT NULL,
            OPERATOR_NAME TEXT,
            IS_LIVE_COOP INTEGER DEFAULT 0
        )
    ''')
    
    # 插入测试数据
    # 1. 计划检修
    cursor.executemany('''
        INSERT INTO maintenance_records (RECORD_ID, WORK_ORDER_NO, OPERATION_TYPE, ORDER_TYPE, 
            EQUIPMENT_NAME, APPROVED_START_TIME, APPROVED_END_TIME, STATUS, OPERATOR_NAME)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', [
        (1, 'WO2025012001', 'power_off', 'phone', '10kV线路A', '2025-01-20 09:00:00', '2025-01-20 13:00:00', 'pending', '张三'),
        (2, 'WO2025012002', 'power_on', 'network', '10kV线路B', '2025-01-20 08:00:00', '2025-01-20 22:00:00', 'executing', '李四'),
        (3, 'WO2025012003', 'power_off', 'phone', '10kV线路C', '2025-01-20 15:00:00', '2025-01-20 19:00:00', 'pending', '王五')
    ])
    
    # 2. 设备投退
    cursor.executemany('''
        INSERT INTO equipment_operations (OPERATION_ID, OPERATION_NO, OPERATION_TYPE, 
            EQUIPMENT_NAME, APPROVED_START_TIME, APPROVED_END_TIME, STATUS, OPERATOR_NAME)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', [
        (101, 'EO2025012001', 'put_into_service', '断路器#1', '2025-01-20 10:00:00', '2025-01-20 12:00:00', 'pending', '赵六'),
        (102, 'EO2025012002', 'take_out_of_service', '断路器#2', '2025-01-20 08:00:00', '2025-01-20 23:00:00', 'executing', '钱七')
    ])
    
    # 3. 转供电
    cursor.executemany('''
        INSERT INTO transfer_orders (ORDER_ID, ORDER_NO, TRANSFER_TYPE, 
            EQUIPMENT_NAME, TRANSFER_OUT_TIME, TRANSFER_BACK_TIME, STATUS, OPERATOR_NAME)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', [
        (201, 'TO2025012001', 'normal', '变压器#1', '2025-01-20 11:00:00', '2025-01-20 18:00:00', 'pending', '孙八'),
        (202, 'TO2025012002', 'emergency', '变压器#2', '2025-01-20 22:00:00', '2025-01-21 07:00:00', 'executing', '周九'),
        (203, 'TO2025012003', 'normal', '变压器#3', '2025-01-20 16:00:00', '2025-01-20 20:00:00', 'pending', '吴十')
    ])
    
    # 4. 周计划
    cursor.executemany('''
        INSERT INTO weekly_plans (PLAN_ID, PLAN_NO, PLAN_TYPE, PLAN_NAME, 
            EQUIPMENT_NAME, APPROVED_START_TIME, APPROVED_END_TIME, 
            WORK_START_TIME, WORK_END_TIME, STATUS, OPERATOR_NAME, IS_LIVE_COOP)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', [
        (301, 'WP2025012001', 'live_operation', '带电作业计划1', '10kV线路D', 
         '2025-01-20 09:00:00', '2025-01-20 17:00:00', '2025-01-20 09:30:00', '2025-01-20 16:00:00', 
         'executing', '郑十一', 1),
        (302, 'WP2025012002', 'commissioning', '投产计划1', '10kV线路E', 
         '2025-01-20 20:00:00', '2025-01-21 04:00:00', '2025-01-20 21:00:00', '2025-01-21 03:00:00', 
         'executing', '王十二', 1),
        (303, 'WP2025012003', 'live_operation', '带电作业计划2', '10kV线路F', 
         '2025-01-20 13:00:00', '2025-01-20 14:30:00', '2025-01-20 13:30:00', '2025-01-20 14:00:00', 
         'executing', '李十三', 0)
    ])
    
    conn.commit()
    return conn

def test_plan_workload_statistics():
    """测试计划工作量统计功能"""
    print("=" * 80)
    print("计划工作量统计功能测试")
    print("=" * 80)
    
    # 创建测试数据库
    conn = create_sqlite_test_db()
    cursor = conn.cursor()
    
    print("\n1. 数据准备")
    print("-" * 80)
    
    # 查询数据
    tables = [
        ('maintenance_records', 'RECORD_ID'),
        ('equipment_operations', 'OPERATION_ID'),
        ('transfer_orders', 'ORDER_ID'),
        ('weekly_plans', 'PLAN_ID')
    ]
    
    for table_name, pk in tables:
        cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
        count = cursor.fetchone()[0]
        print(f"✅ {table_name}: {count} 条记录")
    
    print("\n2. 统计计划检修工作量")
    print("-" * 80)
    
    # 计划检修业务规则：
    # 1. 待执行-批准停电开始时间为当天 → 纳入统计
    # 2. 执行中-批准工作结束时间为当天（21:00后的也包括）→ 纳入统计
    # 3. 白天工作量 = 上述两项
    # 4. 批准工作结束时间为21:00后的工作量纳入夜班
    
    cursor.execute('''
        SELECT RECORD_ID, OPERATION_TYPE, ORDER_TYPE, APPROVED_START_TIME, 
               APPROVED_END_TIME, STATUS, OPERATOR_NAME
        FROM maintenance_records
        WHERE (STATUS = 'pending' AND DATE(APPROVED_START_TIME) = '2025-01-20')
           OR (STATUS = 'executing' AND DATE(APPROVED_END_TIME) = '2025-01-20')
        ORDER BY APPROVED_START_TIME
    ''')
    
    maintenance_records = cursor.fetchall()
    print(f"采集到 {len(maintenance_records)} 条计划检修记录:")
    
    maintenance_allocation = {"morning": 0, "afternoon": 0, "night": 0}
    
    for record in maintenance_records:
        record_id, op_type, order_type, start_time, end_time, status, operator = record
        start_hour = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S").hour
        end_hour = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S").hour
        
        # 根据业务规则分配
        if status == 'pending':
            # 待执行：根据批准开始时间分配
            if 8 <= start_hour < 14:
                shift = "morning"
            elif 14 <= start_hour < 21:
                shift = "afternoon"
            else:
                shift = "night"
            maintenance_allocation[shift] += 1
        elif status == 'executing':
            # 执行中：根据批准结束时间分配
            if 8 <= end_hour < 14:
                shift = "morning"
            elif 14 <= end_hour < 21:
                shift = "afternoon"
            else:
                shift = "night"  # 21:00后纳入夜班
            maintenance_allocation[shift] += 1
        
        print(f"  - {operator}: {op_type}({order_type}), 开始:{start_time}, 结束:{end_time}, 班次:{shift}")
    
    print(f"\n分配结果: 早班={maintenance_allocation['morning']}, 中班={maintenance_allocation['afternoon']}, 夜班={maintenance_allocation['night']}")
    
    print("\n3. 统计设备投退工作量")
    print("-" * 80)
    
    cursor.execute('''
        SELECT OPERATION_ID, OPERATION_TYPE, EQUIPMENT_NAME, APPROVED_START_TIME, 
               APPROVED_END_TIME, STATUS, OPERATOR_NAME
        FROM equipment_operations
        WHERE (STATUS = 'pending' AND DATE(APPROVED_START_TIME) = '2025-01-20')
           OR (STATUS = 'executing' AND DATE(APPROVED_END_TIME) = '2025-01-20')
        ORDER BY APPROVED_START_TIME
    ''')
    
    equipment_records = cursor.fetchall()
    print(f"采集到 {len(equipment_records)} 条设备投退记录:")
    
    equipment_allocation = {"morning": 0, "afternoon": 0, "night": 0}
    
    for record in equipment_records:
        op_id, op_type, equipment, start_time, end_time, status, operator = record
        start_hour = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S").hour
        end_hour = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S").hour
        
        # 根据业务规则分配
        if status == 'pending':
            # 待执行：根据批准开始时间分配
            if 8 <= start_hour < 14:
                shift = "morning"
            elif 14 <= start_hour < 21:
                shift = "afternoon"
            else:
                shift = "night"
            equipment_allocation[shift] += 1
        elif status == 'executing':
            # 执行中：根据批准结束时间分配
            if 8 <= end_hour < 14:
                shift = "morning"
            elif 14 <= end_hour < 21:
                shift = "afternoon"
            else:
                shift = "night"  # 21:00后纳入夜班
            equipment_allocation[shift] += 1
        
        print(f"  - {operator}: {equipment}, 开始:{start_time}, 结束:{end_time}, 班次:{shift}")
    
    print(f"\n分配结果: 早班={equipment_allocation['morning']}, 中班={equipment_allocation['afternoon']}, 夜班={equipment_allocation['night']}")
    
    print("\n4. 统计转供电工作量")
    print("-" * 80)
    
    cursor.execute('''
        SELECT ORDER_ID, TRANSFER_TYPE, EQUIPMENT_NAME, TRANSFER_OUT_TIME, 
               TRANSFER_BACK_TIME, STATUS, OPERATOR_NAME
        FROM transfer_orders
        WHERE (STATUS = 'pending' AND DATE(TRANSFER_OUT_TIME) = '2025-01-20')
           OR (STATUS = 'executing' AND DATE(TRANSFER_OUT_TIME) = '2025-01-20')
        ORDER BY TRANSFER_OUT_TIME
    ''')
    
    transfer_records = cursor.fetchall()
    print(f"采集到 {len(transfer_records)} 条转供电记录:")
    
    transfer_allocation = {"morning": 0, "afternoon": 0, "night": 0}
    
    for record in transfer_records:
        order_id, transfer_type, equipment, out_time, back_time, status, operator = record
        out_hour = datetime.strptime(out_time, "%Y-%m-%d %H:%M:%S").hour
        
        # 统一使用转出开始时间分配
        if 8 <= out_hour < 14:
            shift = "morning"
        elif 14 <= out_hour < 21:
            shift = "afternoon"
        else:
            shift = "night"  # 21:00至次日08:30纳入夜班
        transfer_allocation[shift] += 1
        
        print(f"  - {operator}: {equipment}, 转出:{out_time}, 转回:{back_time}, 班次:{shift}")
    
    print(f"\n分配结果: 早班={transfer_allocation['morning']}, 中班={transfer_allocation['afternoon']}, 夜班={transfer_allocation['night']}")
    
    print("\n5. 统计周计划工作量")
    print("-" * 80)
    
    cursor.execute('''
        SELECT PLAN_ID, PLAN_TYPE, PLAN_NAME, EQUIPMENT_NAME, APPROVED_START_TIME, 
               APPROVED_END_TIME, STATUS, OPERATOR_NAME, IS_LIVE_COOP,
               CASE WHEN DATE(APPROVED_START_TIME) != DATE(APPROVED_END_TIME) THEN 1 ELSE 0 END as is_cross_day,
               CASE WHEN PLAN_TYPE = 'live_operation' AND IS_LIVE_COOP = 1 THEN 2
                    WHEN PLAN_TYPE = 'live_operation' THEN 1
                    WHEN PLAN_TYPE = 'commissioning' AND IS_LIVE_COOP = 1 THEN 2
                    ELSE 1 END as task_count
        FROM weekly_plans
        WHERE STATUS = 'executing' AND DATE(APPROVED_START_TIME) = '2025-01-20'
        ORDER BY APPROVED_START_TIME
    ''')
    
    weekly_plan_records = cursor.fetchall()
    print(f"采集到 {len(weekly_plan_records)} 条周计划记录:")
    
    weekly_plan_allocation = {"morning": 0, "afternoon": 0, "night": 0}
    pre_analyze = False  # 正常分析模式
    
    for record in weekly_plan_records:
        plan_id, plan_type, plan_name, equipment, start_time, end_time, status, operator, is_live_coop, is_cross_day, task_count = record
        start_hour = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S").hour
        
        # 根据业务规则分配
        if pre_analyze:
            # 提前分析：周计划总数纳入早班、中班
            weekly_plan_allocation["morning"] += task_count // 2
            weekly_plan_allocation["afternoon"] += task_count - (task_count // 2)
            shift = "提前分析(早班+中班)"
        else:
            # 正常分析：根据跨天情况分配
            if is_cross_day == 1:
                # 跨天工作：纳入夜班
                weekly_plan_allocation["night"] += task_count
                shift = "night"
            else:
                # 非跨天：根据批准开始时间分配
                if 8 <= start_hour < 14:
                    shift = "morning"
                elif 14 <= start_hour < 21:
                    shift = "afternoon"
                else:
                    shift = "night"
                weekly_plan_allocation[shift] += task_count
        
        print(f"  - {operator}: {plan_name}, 开始:{start_time}, 结束:{end_time}, 数量:{task_count}, 跨天:{is_cross_day}, 班次:{shift}")
    
    print(f"\n分配结果: 早班={weekly_plan_allocation['morning']}, 中班={weekly_plan_allocation['afternoon']}, 夜班={weekly_plan_allocation['night']}")
    
    print("\n6. 汇总统计")
    print("-" * 80)
    
    summary = {
        "morning": maintenance_allocation["morning"] + equipment_allocation["morning"] + transfer_allocation["morning"] + weekly_plan_allocation["morning"],
        "afternoon": maintenance_allocation["afternoon"] + equipment_allocation["afternoon"] + transfer_allocation["afternoon"] + weekly_plan_allocation["afternoon"],
        "night": maintenance_allocation["night"] + equipment_allocation["night"] + transfer_allocation["night"] + weekly_plan_allocation["night"]
    }
    
    total = summary["morning"] + summary["afternoon"] + summary["night"]
    
    print(f"\n📊 2025-01-20 计划工作量统计汇总")
    print("-" * 80)
    print(f"{'班次':<15} {'计划检修':<10} {'设备投退':<10} {'转供电':<10} {'周计划':<10} {'总计':<10}")
    print("-" * 80)
    print(f"{'早班':<15} {maintenance_allocation['morning']:<10} {equipment_allocation['morning']:<10} {transfer_allocation['morning']:<10} {weekly_plan_allocation['morning']:<10} {summary['morning']:<10}")
    print(f"{'中班':<15} {maintenance_allocation['afternoon']:<10} {equipment_allocation['afternoon']:<10} {transfer_allocation['afternoon']:<10} {weekly_plan_allocation['afternoon']:<10} {summary['afternoon']:<10}")
    print(f"{'夜班':<15} {maintenance_allocation['night']:<10} {equipment_allocation['night']:<10} {transfer_allocation['night']:<10} {weekly_plan_allocation['night']:<10} {summary['night']:<10}")
    print("-" * 80)
    print(f"{'总计':<15} {maintenance_allocation['morning']+maintenance_allocation['afternoon']+maintenance_allocation['night']:<10} {equipment_allocation['morning']+equipment_allocation['afternoon']+equipment_allocation['night']:<10} {transfer_allocation['morning']+transfer_allocation['afternoon']+transfer_allocation['night']:<10} {weekly_plan_allocation['morning']+weekly_plan_allocation['afternoon']+weekly_plan_allocation['night']:<10} {total:<10}")
    print("=" * 80)
    
    # 验证结果
    expected = {"morning": 6, "afternoon": 2, "night": 5}
    print("\n✅ 测试验证:")
    print(f"预期结果: 早班={expected['morning']}, 中班={expected['afternoon']}, 夜班={expected['night']}, 总计={expected['morning']+expected['afternoon']+expected['night']}")
    print(f"实际结果: 早班={summary['morning']}, 中班={summary['afternoon']}, 夜班={summary['night']}, 总计={total}")
    
    if summary == expected and total == 13:
        print("\n🎉 测试通过！计划工作量统计功能工作正常！")
    else:
        print("\n❌ 测试失败！请检查业务规则实现。")
    
    conn.close()
    return summary

if __name__ == "__main__":
    test_plan_workload_statistics()
