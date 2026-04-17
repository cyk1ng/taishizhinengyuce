# 非计划工作量统计功能使用指南

## 功能概述

非计划工作量统计模块支持实时分析故障日志、异常缺陷、重过载等非计划任务，为配网调度值班人员配置提供数据支持。

## 数据来源

| 数据来源 | 系统位置 | 说明 |
|---------|---------|------|
| 故障日志 | 配网OMS系统-调度工作台-故障日志-当值记录 | 统计前三天未交班的故障单数 |
| 异常缺陷 | 配网OMS系统-调度工作台-异常缺陷-当值记录 | 统计未交班的所有缺陷单数 |
| 重过载 | 配网OMS系统-调度工作台-重过载-当值记录 | 统计未解决的所有重过载数 |

## 业务规则

### 1. 故障日志业务规则

**统计范围**：
- 配网OMS系统-调度工作台-故障日志-当值记录-前三天未交班的故障单数

**统计条件**：
- 故障时间在目标日期前3天内
- IS_HANDED_OVER = 0（未交班）

**故障类型分类**：
- B1_success：跳闸重合成功（权重：0.1）
- B1_fail_known：跳闸重合不成功（确定故障）（权重：0.3）
- B1_fail_unknown：跳闸重合不成功（不确定故障）（权重：0.5）
- B1_bus_ground：母线接地（权重：0.5）

### 2. 异常缺陷业务规则

**统计范围**：
- 配网OMS系统-调度工作台-异常缺陷-当值记录-未交班的所有缺陷单数

**统计条件**：
- IS_HANDED_OVER = 0（未交班）
- **不限制日期范围**，所有未交班的缺陷单都纳入统计

**缺陷等级**：
- critical：紧急
- major：重大
- general：一般

**权重**：异常缺陷权重统一为 0.5

### 3. 重过载业务规则

**统计范围**：
- 配网OMS系统-调度工作台-重过载-当值记录-未解决的所有重过载数

**统计条件**：
- IS_RESOLVED = 0（未解决）
- **不限制日期范围**，所有未解决的重过载都纳入统计

**过载类型**：
- overload：过载（负载率 > 100%）
- heavy_load：重载（负载率 > 90%）

**权重**：重过载权重统一为 0.1

## 使用方法

### 1. 在Agent中使用

```
用户：请帮我统计今天的非计划工作量
用户：帮我查看前3天的故障日志、异常缺陷和重过载情况
```

Agent会自动调用 `calculate_non_plan_workload` 工具进行统计。

### 2. 直接调用工具

```python
from tools.non_plan_workload import calculate_non_plan_workload
import json

# 统计今天（默认前3天故障日志）
result = calculate_non_plan_workload(
    target_date="",  # 空字符串表示今天
    days_back=3      # 向前追溯天数
)

# 统计指定日期，自定义向前追溯天数
result = calculate_non_plan_workload(
    target_date="2025-01-20",
    days_back=5      # 前5天故障日志
)

# 解析结果
data = json.loads(result)
if data["success"]:
    summary = data["data"]["summary"]
    print(f"总非计划工作量: {summary['total_count']} 项")
    print(f"总工作当量: {summary['total_weight']}")
    
    # 按类别统计
    fault_count = summary["by_category"]["fault_logs"]["count"]
    defect_count = summary["by_category"]["defect_records"]["count"]
    overload_count = summary["by_category"]["overload_records"]["count"]
    
    print(f"故障日志: {fault_count} 项")
    print(f"异常缺陷: {defect_count} 项")
    print(f"重过载: {overload_count} 项")
```

## 返回结果格式

```json
{
  "success": true,
  "generated_at": "2026-04-17 15:42:09",
  "data": {
    "target_date": "2025-01-20",
    "days_back": 3,
    "fault_logs": [
      {
        "record_id": 1,
        "fault_id": "FLT20250120002",
        "task_category": "B1_fail_unknown",
        "task_name": "跳闸重合不成功(不确定故障)",
        "equipment_name": "10kV线路D",
        "fault_time": "2025-01-20 14:30:00",
        "weight": 0.5
      }
    ],
    "defect_records": [
      {
        "record_id": 1,
        "defect_id": "DEF20250120001",
        "task_category": "B2",
        "task_name": "异常缺陷",
        "equipment_name": "电缆接头#1",
        "defect_time": "2025-01-20 09:00:00",
        "weight": 0.5
      }
    ],
    "overload_records": [
      {
        "record_id": 1,
        "overload_id": "OVL20250120001",
        "task_category": "B3",
        "task_name": "重过载",
        "equipment_name": "变压器#3",
        "load_rate": 110.0,
        "record_time": "2025-01-20 12:00:00",
        "weight": 0.1
      }
    ],
    "summary": {
      "total_count": 11,
      "total_weight": 3.3,
      "by_category": {
        "fault_logs": {
          "count": 5,
          "weight": 1.5,
          "description": "前3天未交班故障单"
        },
        "defect_records": {
          "count": 3,
          "weight": 1.5,
          "description": "未交班缺陷单"
        },
        "overload_records": {
          "count": 3,
          "weight": 0.3,
          "description": "未解决重过载"
        }
      },
      "record_counts": {
        "fault_logs": 5,
        "defect_records": 3,
        "overload_records": 3
      }
    }
  }
}
```

## 数据库表结构

### 1. 故障日志表 (fault_logs)

| 字段名              | 类型        | 说明               |
|---------------------|-------------|--------------------|
| RECORD_ID           | INT         | 记录ID（主键）     |
| FAULT_ID            | VARCHAR(50) | 故障编号           |
| FAULT_TYPE          | VARCHAR(50) | 故障类型           |
| RECLOSER_RESULT     | VARCHAR(20) | 重合闸结果         |
| EQUIPMENT_NAME      | VARCHAR(100)| 设备名称           |
| VOLTAGE_LEVEL       | VARCHAR(20) | 电压等级           |
| FAULT_TIME          | DATETIME    | 故障发生时间       |
| EXPECTED_RESTORE_TIME | DATETIME  | 预计恢复时间       |
| ACTUAL_RESTORE_TIME | DATETIME    | 实际恢复时间       |
| IS_HANDED_OVER      | TINYINT     | 是否已交班         |
| STATUS              | VARCHAR(20) | 状态               |
| DUTY_OFFICER        | VARCHAR(50) | 当值人员           |

### 2. 缺陷记录表 (defect_records)

| 字段名              | 类型        | 说明               |
|---------------------|-------------|--------------------|
| RECORD_ID           | INT         | 记录ID（主键）     |
| DEFECT_ID           | VARCHAR(50) | 缺陷编号           |
| DEFECT_TYPE         | VARCHAR(50) | 缺陷类型           |
| DEFECT_LEVEL        | VARCHAR(20) | 缺陷等级           |
| EQUIPMENT_NAME      | VARCHAR(100)| 设备名称           |
| DEFECT_TIME         | DATETIME    | 缺陷发现时间       |
| EXPECTED_FIX_TIME   | DATETIME    | 预计修复时间       |
| ACTUAL_FIX_TIME     | DATETIME    | 实际修复时间       |
| IS_HANDED_OVER      | TINYINT     | 是否已交班         |
| STATUS              | VARCHAR(20) | 状态               |
| REPORTER            | VARCHAR(50) | 上报人             |

### 3. 重过载记录表 (overload_records)

| 字段名              | 类型        | 说明               |
|---------------------|-------------|--------------------|
| RECORD_ID           | INT         | 记录ID（主键）     |
| OVERLOAD_ID         | VARCHAR(50) | 过载编号           |
| OVERLOAD_TYPE       | VARCHAR(20) | 过载类型           |
| EQUIPMENT_NAME      | VARCHAR(100)| 设备名称           |
| LOAD_RATE           | DECIMAL(5,2)| 负载率（百分比）   |
| RATED_CAPACITY      | DECIMAL(10,2)| 额定容量          |
| ACTUAL_LOAD         | DECIMAL(10,2)| 实际负载          |
| RECORD_TIME         | DATETIME    | 记录时间           |
| EXPECTED_RESOLVE_TIME | DATETIME  | 预计解决时间       |
| ACTUAL_RESOLVE_TIME | DATETIME    | 实际解决时间       |
| IS_RESOLVED         | TINYINT     | 是否已解决         |
| STATUS              | VARCHAR(20) | 状态               |
| MONITOR_PERSON      | VARCHAR(50) | 监控人员           |

## 权重配置

### 非计划任务权重

| 任务类型                       | 权重 | 说明               |
|--------------------------------|------|--------------------|
| 跳闸重合成功 (B1_success)      | 0.1  | 重合闸成功         |
| 跳闸重合不成功(确定故障) (B1_fail_known) | 0.3  | 故障类型明确       |
| 跳闸重合不成功(不确定故障) (B1_fail_unknown) | 0.5  | 故障类型不明确     |
| 母线接地 (B1_bus_ground)      | 0.5  | 母线接地故障       |
| 异常缺陷 (B2)                  | 0.5  | 各等级缺陷统一权重 |
| 重过载 (B3)                    | 0.1  | 过载和重载统一权重 |

## 测试数据

项目提供了完整的测试数据和测试脚本：

1. **测试数据生成**：已在 `test_non_plan_workload_sqlite.py` 中集成
2. **SQLite测试**：
   ```bash
   python scripts/test_non_plan_workload_sqlite.py
   ```
3. **MySQL表创建脚本**：
   - 文件路径：`scripts/create_non_plan_workload_tables.sql`
   - 包含3张表的完整DDL和测试数据

## 测试验证结果

使用SQLite测试数据库进行验证，测试结果如下：

### 测试数据
- 故障日志：5条（前3天未交班）
- 异常缺陷：3条（未交班，不限制日期）
- 重过载：3条（未解决，不限制日期）

### 测试结果
```
📊 2025-01-20 非计划工作量统计汇总
--------------------------------------------------------------------------------
类别                   记录数        总权重        说明
--------------------------------------------------------------------------------
故障日志                 5          1.50       前3天未交班故障单
异常缺陷                 3          1.50       未交班所有缺陷单
重过载                  3          0.30       未解决所有重过载
--------------------------------------------------------------------------------
总计                   11         3.30       实时分析非计划工作量
```

### 详细分类统计
- **故障日志分类**：
  - 跳闸重合不成功(不确定故障): 2项
  - 跳闸重合成功: 2项
  - 跳闸重合不成功(确定故障): 1项

- **异常缺陷等级**：
  - 紧急: 1项
  - 重大: 1项
  - 一般: 1项

- **重过载类型**：
  - 过载: 2项
  - 重载: 1项

✅ 测试通过！非计划工作量统计功能工作正常！

## 智能体训练数据

非计划工作量统计结果可以用作智能体的训练数据，完善智能体后续的预测功能：

1. **历史数据积累**：定期记录非计划工作量数据
2. **趋势分析**：分析非计划工作量的时间分布规律
3. **预测模型训练**：使用历史数据训练预测模型
4. **风险预警**：基于预测结果提前预警高风险时段

## 注意事项

1. **数据库连接**：
   - 确保MySQL数据库配置正确（.env文件）
   - 确保数据库表已创建
   - 确保有足够的数据访问权限

2. **时间格式**：
   - 所有时间字段使用DATETIME类型
   - 查询时使用YYYY-MM-DD格式

3. **状态枚举值**：
   - 故障日志：pending-待处理, processing-处理中, resolved-已解决
   - 缺陷记录：pending-待处理, processing-处理中, fixed-已修复
   - 重过载：pending-待处理, monitoring-监控中, resolved-已解决

4. **功能特点**：
   - 实时统计非计划任务工作量
   - 支持自定义向前追溯天数
   - 详细的分类统计和权重计算
   - 可用作智能体训练数据

## 集成到现有系统

非计划工作量统计功能已集成到Agent中，可以通过以下方式调用：

1. **自然语言对话**：
   ```
   用户：请统计今天的非计划工作量
   用户：帮我查看前3天的故障日志和异常缺陷
   ```

2. **API调用**：
   通过Agent工具接口直接调用 `calculate_non_plan_workload` 工具

3. **前端集成**：
   可以通过API获取数据，在前端展示统计结果

## 技术支持

如遇问题，请检查：
1. 数据库连接是否正常
2. 表结构是否正确
3. 数据格式是否符合要求
4. 环境变量配置是否正确

## 更新日志

### v1.0.0 (2026-04-17)
- ✅ 实现故障日志统计：前三天未交班故障单数
- ✅ 实现异常缺陷统计：未交班所有缺陷单数
- ✅ 实现重过载统计：未解决所有重过载数
- ✅ 完整的权重配置体系
- ✅ 支持自定义向前追溯天数
- ✅ 完整的测试数据集
- ✅ 集成到Agent系统
- ✅ 可用作智能体训练数据
