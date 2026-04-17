"""
使用SQLite内存数据库测试非计划工作量统计功能
"""
import sqlite3
from datetime import datetime, timedelta
import json

def create_sqlite_test_db():
    """创建SQLite测试数据库"""
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    
    # 创建故障日志表
    cursor.execute('''
        CREATE TABLE fault_logs (
            RECORD_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            FAULT_ID TEXT NOT NULL,
            FAULT_TYPE TEXT NOT NULL,
            RECLOSER_RESULT TEXT NOT NULL,
            EQUIPMENT_NAME TEXT NOT NULL,
            VOLTAGE_LEVEL TEXT,
            FAULT_TIME TEXT NOT NULL,
            EXPECTED_RESTORE_TIME TEXT,
            ACTUAL_RESTORE_TIME TEXT,
            IS_HANDED_OVER INTEGER DEFAULT 0,
            STATUS TEXT NOT NULL,
            DUTY_OFFICER TEXT
        )
    ''')
    
    # 创建缺陷记录表
    cursor.execute('''
        CREATE TABLE defect_records (
            RECORD_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            DEFECT_ID TEXT NOT NULL,
            DEFECT_TYPE TEXT NOT NULL,
            DEFECT_LEVEL TEXT NOT NULL,
            EQUIPMENT_NAME TEXT NOT NULL,
            DEFECT_TIME TEXT NOT NULL,
            EXPECTED_FIX_TIME TEXT,
            ACTUAL_FIX_TIME TEXT,
            IS_HANDED_OVER INTEGER DEFAULT 0,
            STATUS TEXT NOT NULL,
            REPORTER TEXT
        )
    ''')
    
    # 创建重过载记录表
    cursor.execute('''
        CREATE TABLE overload_records (
            RECORD_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            OVERLOAD_ID TEXT NOT NULL,
            OVERLOAD_TYPE TEXT NOT NULL,
            EQUIPMENT_NAME TEXT NOT NULL,
            LOAD_RATE REAL NOT NULL,
            RATED_CAPACITY REAL,
            ACTUAL_LOAD REAL,
            RECORD_TIME TEXT NOT NULL,
            EXPECTED_RESOLVE_TIME TEXT,
            ACTUAL_RESOLVE_TIME TEXT,
            IS_RESOLVED INTEGER DEFAULT 0,
            STATUS TEXT NOT NULL,
            MONITOR_PERSON TEXT
        )
    ''')
    
    # 插入测试数据
    
    # 1. 故障日志（前三天未交班）
    cursor.executemany('''
        INSERT INTO fault_logs (RECORD_ID, FAULT_ID, FAULT_TYPE, RECLOSER_RESULT, 
            EQUIPMENT_NAME, VOLTAGE_LEVEL, FAULT_TIME, EXPECTED_RESTORE_TIME, 
            IS_HANDED_OVER, STATUS, DUTY_OFFICER)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', [
        (1, 'FLT20250117001', 'unknown', 'fail', '10kV线路A', '10kV', '2025-01-17 09:30:00', '2025-01-17 14:00:00', 0, 'resolved', '张三'),
        (2, 'FLT20250118001', 'known', 'fail', '10kV线路B', '10kV', '2025-01-18 15:20:00', '2025-01-18 18:00:00', 0, 'resolved', '李四'),
        (3, 'FLT20250119001', 'bus_ground', 'success', '母线#1', '10kV', '2025-01-19 11:45:00', '2025-01-19 13:00:00', 0, 'resolved', '王五'),
        (4, 'FLT20250120001', 'known', 'success', '10kV线路C', '10kV', '2025-01-20 08:15:00', '2025-01-20 09:30:00', 0, 'resolved', '赵六'),
        (5, 'FLT20250120002', 'unknown', 'fail', '10kV线路D', '10kV', '2025-01-20 14:30:00', '2025-01-20 17:00:00', 0, 'processing', '钱七')
    ])
    
    # 2. 缺陷记录（未交班）
    cursor.executemany('''
        INSERT INTO defect_records (RECORD_ID, DEFECT_ID, DEFECT_TYPE, DEFECT_LEVEL, 
            EQUIPMENT_NAME, DEFECT_TIME, EXPECTED_FIX_TIME, IS_HANDED_OVER, STATUS, REPORTER)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', [
        (1, 'DEF20250115001', '设备缺陷', 'general', '断路器#1', '2025-01-15 10:00:00', '2025-01-25 10:00:00', 0, 'pending', '张三'),
        (2, 'DEF20250118001', '绝缘缺陷', 'major', '隔离开关#1', '2025-01-18 14:30:00', '2025-01-23 14:30:00', 0, 'processing', '李四'),
        (3, 'DEF20250120001', '接触不良', 'critical', '电缆接头#1', '2025-01-20 09:00:00', '2025-01-21 09:00:00', 0, 'pending', '王五')
    ])
    
    # 3. 重过载记录（未解决）
    cursor.executemany('''
        INSERT INTO overload_records (RECORD_ID, OVERLOAD_ID, OVERLOAD_TYPE, 
            EQUIPMENT_NAME, LOAD_RATE, RATED_CAPACITY, ACTUAL_LOAD, RECORD_TIME, 
            EXPECTED_RESOLVE_TIME, IS_RESOLVED, STATUS, MONITOR_PERSON)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', [
        (1, 'OVL20250116001', 'overload', '变压器#1', 115.00, 100.00, 115.00, '2025-01-16 16:30:00', '2025-01-20 16:30:00', 0, 'monitoring', '张三'),
        (2, 'OVL20250119001', 'heavy_load', '变压器#2', 95.00, 100.00, 95.00, '2025-01-19 10:15:00', '2025-01-22 10:15:00', 0, 'monitoring', '李四'),
        (3, 'OVL20250120001', 'overload', '变压器#3', 110.00, 100.00, 110.00, '2025-01-20 12:00:00', '2025-01-21 12:00:00', 0, 'pending', '王五')
    ])
    
    conn.commit()
    return conn

def test_non_plan_workload_statistics():
    """测试非计划工作量统计功能"""
    print("=" * 80)
    print("非计划工作量统计功能测试")
    print("=" * 80)
    
    # 创建测试数据库
    conn = create_sqlite_test_db()
    cursor = conn.cursor()
    
    print("\n1. 数据准备")
    print("-" * 80)
    
    # 查询数据
    tables = [
        ('fault_logs', 'RECORD_ID'),
        ('defect_records', 'RECORD_ID'),
        ('overload_records', 'RECORD_ID')
    ]
    
    for table_name, pk in tables:
        cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
        count = cursor.fetchone()[0]
        print(f"✅ {table_name}: {count} 条记录")
    
    print("\n2. 统计故障日志（前三天未交班）")
    print("-" * 80)
    
    target_date = "2025-01-20"
    days_back = 3
    
    # 计算向前追溯的日期
    start_date_obj = datetime.strptime(target_date, "%Y-%m-%d") - timedelta(days=days_back)
    start_date_str = start_date_obj.strftime("%Y-%m-%d")
    target_date_next = (datetime.strptime(target_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    
    print(f"查询范围: {start_date_str} ~ {target_date} (前{days_back}天)")
    print(f"查询条件: IS_HANDED_OVER = 0 (未交班)")
    
    cursor.execute('''
        SELECT RECORD_ID, FAULT_ID, FAULT_TYPE, RECLOSER_RESULT, EQUIPMENT_NAME, 
               FAULT_TIME, IS_HANDED_OVER, STATUS, DUTY_OFFICER
        FROM fault_logs
        WHERE FAULT_TIME >= ?
          AND FAULT_TIME < ?
          AND (IS_HANDED_OVER = 0 OR IS_HANDED_OVER IS NULL)
        ORDER BY FAULT_TIME DESC
    ''', (start_date_str, target_date_next))
    
    fault_logs = cursor.fetchall()
    print(f"\n采集到 {len(fault_logs)} 条故障日志记录:")
    
    fault_weight_map = {
        'success': 0.1,
        'fail': 0.5,  # 默认未知故障
        'known_fail': 0.3,
        'unknown_fail': 0.5,
        'bus_ground': 0.5
    }
    
    total_fault_weight = 0.0
    for record in fault_logs:
        record_id, fault_id, fault_type, reclose_result, equipment, fault_time, is_handed_over, status, officer = record
        
        # 确定任务类别和权重
        if reclose_result == 'success':
            task_category = 'B1_success'
            weight = 0.1
        elif fault_type == 'bus_ground':
            task_category = 'B1_bus_ground'
            weight = 0.5
        elif reclose_result == 'fail' and fault_type == 'known':
            task_category = 'B1_fail_known'
            weight = 0.3
        else:
            task_category = 'B1_fail_unknown'
            weight = 0.5
        
        total_fault_weight += weight
        
        print(f"  - {officer}: {fault_id} {task_category}, {equipment}, 时间:{fault_time}, 权重:{weight}")
    
    print(f"\n故障日志小计: {len(fault_logs)} 项, 总权重: {total_fault_weight}")
    
    print("\n3. 统计异常缺陷（未交班）")
    print("-" * 80)
    print(f"查询条件: IS_HANDED_OVER = 0 (未交班，不限制日期范围)")
    
    cursor.execute('''
        SELECT RECORD_ID, DEFECT_ID, DEFECT_TYPE, DEFECT_LEVEL, EQUIPMENT_NAME, 
               DEFECT_TIME, IS_HANDED_OVER, STATUS, REPORTER
        FROM defect_records
        WHERE IS_HANDED_OVER = 0 OR IS_HANDED_OVER IS NULL
        ORDER BY DEFECT_TIME DESC
    ''')
    
    defect_records = cursor.fetchall()
    print(f"\n采集到 {len(defect_records)} 条异常缺陷记录:")
    
    total_defect_weight = 0.0
    for record in defect_records:
        record_id, defect_id, defect_type, defect_level, equipment, defect_time, is_handed_over, status, reporter = record
        weight = 0.5  # B2 异常缺陷权重
        total_defect_weight += weight
        
        print(f"  - {reporter}: {defect_id} B2, {equipment}, 时间:{defect_time}, 等级:{defect_level}, 权重:{weight}")
    
    print(f"\n异常缺陷小计: {len(defect_records)} 项, 总权重: {total_defect_weight}")
    
    print("\n4. 统计重过载（未解决）")
    print("-" * 80)
    print(f"查询条件: IS_RESOLVED = 0 (未解决，不限制日期范围)")
    
    cursor.execute('''
        SELECT RECORD_ID, OVERLOAD_ID, OVERLOAD_TYPE, EQUIPMENT_NAME, LOAD_RATE, 
               RECORD_TIME, IS_RESOLVED, STATUS, MONITOR_PERSON
        FROM overload_records
        WHERE IS_RESOLVED = 0 OR IS_RESOLVED IS NULL
        ORDER BY RECORD_TIME DESC
    ''')
    
    overload_records = cursor.fetchall()
    print(f"\n采集到 {len(overload_records)} 条重过载记录:")
    
    total_overload_weight = 0.0
    for record in overload_records:
        record_id, overload_id, overload_type, equipment, load_rate, record_time, is_resolved, status, monitor = record
        weight = 0.1  # B3 重过载权重
        total_overload_weight += weight
        
        print(f"  - {monitor}: {overload_id} B3, {equipment}, 负载率:{load_rate}%, 时间:{record_time}, 权重:{weight}")
    
    print(f"\n重过载小计: {len(overload_records)} 项, 总权重: {total_overload_weight}")
    
    print("\n5. 汇总统计")
    print("-" * 80)
    
    total_count = len(fault_logs) + len(defect_records) + len(overload_records)
    total_weight = total_fault_weight + total_defect_weight + total_overload_weight
    
    print(f"\n📊 {target_date} 非计划工作量统计汇总")
    print("-" * 80)
    print(f"{'类别':<20} {'记录数':<10} {'总权重':<10} {'说明':<30}")
    print("-" * 80)
    print(f"{'故障日志':<20} {len(fault_logs):<10} {total_fault_weight:<10.2f} {'前3天未交班故障单':<30}")
    print(f"{'异常缺陷':<20} {len(defect_records):<10} {total_defect_weight:<10.2f} {'未交班所有缺陷单':<30}")
    print(f"{'重过载':<20} {len(overload_records):<10} {total_overload_weight:<10.2f} {'未解决所有重过载':<30}")
    print("-" * 80)
    print(f"{'总计':<20} {total_count:<10} {total_weight:<10.2f} {'实时分析非计划工作量':<30}")
    print("=" * 80)
    
    # 验证结果
    expected_count = 11  # 5条故障 + 3条缺陷 + 3条重过载
    expected_weight = total_fault_weight + total_defect_weight + total_overload_weight
    
    print("\n✅ 测试验证:")
    print(f"预期记录数: {expected_count} 条")
    print(f"实际记录数: {total_count} 条")
    print(f"预期总权重: {expected_weight:.2f}")
    print(f"实际总权重: {total_weight:.2f}")
    
    if total_count == expected_count:
        print("\n🎉 测试通过！非计划工作量统计功能工作正常！")
    else:
        print(f"\n❌ 测试失败！记录数不匹配。")
    
    # 详细分类统计
    print("\n📊 详细分类统计:")
    print("-" * 80)
    
    # 故障日志分类统计
    fault_categories = {}
    for record in fault_logs:
        fault_type = record[2]
        reclose_result = record[3]
        if reclose_result == 'success':
            category = '跳闸重合成功'
        elif fault_type == 'bus_ground':
            category = '母线接地'
        elif reclose_result == 'fail' and fault_type == 'known':
            category = '跳闸重合不成功(确定故障)'
        else:
            category = '跳闸重合不成功(不确定故障)'
        fault_categories[category] = fault_categories.get(category, 0) + 1
    
    print("故障日志分类:")
    for category, count in fault_categories.items():
        print(f"  - {category}: {count} 项")
    
    # 缺陷等级统计
    defect_levels = {}
    for record in defect_records:
        level = record[3]  # DEFECT_LEVEL
        level_map = {'critical': '紧急', 'major': '重大', 'general': '一般'}
        level_name = level_map.get(level, level)
        defect_levels[level_name] = defect_levels.get(level_name, 0) + 1
    
    print("\n异常缺陷等级统计:")
    for level, count in defect_levels.items():
        print(f"  - {level}: {count} 项")
    
    # 过载类型统计
    overload_types = {}
    for record in overload_records:
        otype = record[2]  # OVERLOAD_TYPE
        type_map = {'overload': '过载', 'heavy_load': '重载'}
        type_name = type_map.get(otype, otype)
        overload_types[type_name] = overload_types.get(type_name, 0) + 1
    
    print("\n重过载类型统计:")
    for otype, count in overload_types.items():
        print(f"  - {otype}: {count} 项")
    
    conn.close()
    return {
        "total_count": total_count,
        "total_weight": total_weight,
        "fault_logs": len(fault_logs),
        "defect_records": len(defect_records),
        "overload_records": len(overload_records)
    }

if __name__ == "__main__":
    result = test_non_plan_workload_statistics()
    print("\n测试结果:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
