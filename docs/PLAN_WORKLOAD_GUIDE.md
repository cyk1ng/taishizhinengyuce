# 计划工作量统计功能使用指南

## 功能概述

计划工作量统计模块支持按班次（早班/中班/夜班）统计计划检修、转供电、设备投退、周计划的工作量，为配网调度值班人员配置提供数据支持。

## 时间段定义

| 班次   | 时间段          | 说明           |
|--------|----------------|----------------|
| 早班   | 08:00 ~ 14:00  | 白天高峰时段   |
| 中班   | 14:00 ~ 21:00  | 白天高峰时段   |
| 夜班   | 21:00 ~ 次日08:00 | 夜间值守时段 |

## 业务规则

### 1. 计划检修业务规则

**统计范围：**
- 待执行-批准停电开始时间为当天 → 纳入统计
- 执行中-批准工作结束时间为当天（21:00后的也包括）→ 纳入统计

**分配规则：**
- 白天工作量 = 待执行+执行中两项
- 待执行：根据批准开始时间分配到对应班次
- 执行中：根据批准结束时间分配到对应班次
- 批准工作结束时间为21:00后的工作量纳入夜班

### 2. 设备投退业务规则

**统计范围：**
- 待执行-批准工作开始时间为当天 → 纳入统计
- 执行中-批准工作结束时间为当天（21:00后的也包括）→ 纳入统计

**分配规则：**
- 白天工作量 = 待执行+执行中两项
- 待执行：根据批准开始时间分配到对应班次
- 执行中：根据批准结束时间分配到对应班次
- 批准工作结束时间为21:00后的工作量纳入夜班

### 3. 转供电业务规则

**统计范围：**
- 待执行-批准转出开始时间为当天 → 纳入统计
- 执行中-转出开始时间为当天（21:00后的不包括白天统计）→ 纳入统计

**分配规则：**
- 白天工作量 = 待执行+执行中（非21:00后开始）两项
- 统一使用转出开始时间分配到对应班次
- 批准转出开始时间为21:00至次日08:30的工作量纳入夜班

### 4. 周计划业务规则

**统计范围：**
- 需自动读取批准工作开始时间为当天的所有周计划（包括跨天工作的周计划）

**分配规则：**
- **正常分析模式**（pre_analyze=False）：
  - 跨天工作：纳入夜班
  - 非跨天：根据批准开始时间分配到对应班次
- **提前分析模式**（pre_analyze=True）：
  - 将周计划总数纳入早班、中班时间段内考虑
  - 夜班周计划工作量暂时以跨天工作的周计划总数为准

## 使用方法

### 1. 在Agent中使用

```
用户：请帮我统计2025-01-20的计划工作量，按班次（早/中/夜）分别统计
```

Agent会自动调用 `calculate_plan_workload` 工具进行统计。

### 2. 直接调用工具

```python
from tools.plan_workload import calculate_plan_workload

# 正常分析模式
result = calculate_plan_workload(
    target_date="2025-01-20",
    pre_analyze=False
)

# 提前分析模式（用于前瞻性评估）
result = calculate_plan_workload(
    target_date="2025-01-21",
    pre_analyze=True
)

# 解析结果
import json
data = json.loads(result)
if data["success"]:
    summary = data["data"]["summary"]
    print(f"早班工作量: {summary['morning']['total_count']}")
    print(f"中班工作量: {summary['afternoon']['total_count']}")
    print(f"夜班工作量: {summary['night']['total_count']}")
```

## 返回结果格式

```json
{
  "success": true,
  "generated_at": "2026-04-17 15:06:29",
  "data": {
    "target_date": "2025-01-20",
    "pre_analyze": false,
    "maintenance": [
      {
        "record_id": 1,
        "task_category": "A1_phone",
        "task_name": "停电",
        "approved_start_time": "2025-01-20 09:00:00",
        "approved_end_time": "2025-01-20 13:00:00",
        "status": "pending",
        "shift_allocation": {
          "morning": 1,
          "afternoon": 0,
          "night": 0
        },
        "total_count": 1
      }
    ],
    "equipment": [],
    "transfer": [],
    "weekly_plan": [],
    "summary": {
      "morning": {
        "total_count": 1,
        "tasks": [
          {
            "category": "A1_phone",
            "name": "停电",
            "count": 1
          }
        ]
      },
      "afternoon": {
        "total_count": 0,
        "tasks": []
      },
      "night": {
        "total_count": 0,
        "tasks": []
      },
      "total_count": 1,
      "record_counts": {
        "maintenance": 1,
        "equipment": 0,
        "transfer": 0,
        "weekly_plan": 0
      }
    }
  }
}
```

## 数据库表结构

### 1. 计划检修表 (maintenance_records)

| 字段名              | 类型        | 说明               |
|---------------------|-------------|--------------------|
| RECORD_ID           | INT         | 记录ID（主键）     |
| WORK_ORDER_NO       | VARCHAR(50) | 工作票号           |
| OPERATION_TYPE      | VARCHAR(20) | 操作类型           |
| ORDER_TYPE          | VARCHAR(20) | 令票类型           |
| EQUIPMENT_NAME      | VARCHAR(100)| 设备名称           |
| APPROVED_START_TIME | DATETIME    | 批准开始时间       |
| APPROVED_END_TIME   | DATETIME    | 批准结束时间       |
| ACTUAL_START_TIME   | DATETIME    | 实际开始时间       |
| ACTUAL_END_TIME     | DATETIME    | 实际结束时间       |
| STATUS              | VARCHAR(20) | 状态               |
| OPERATOR_NAME       | VARCHAR(50) | 操作人             |

### 2. 设备投退表 (equipment_operations)

| 字段名              | 类型        | 说明               |
|---------------------|-------------|--------------------|
| OPERATION_ID        | INT         | 操作ID（主键）     |
| OPERATION_NO        | VARCHAR(50) | 操作票号           |
| OPERATION_TYPE      | VARCHAR(50) | 操作类型           |
| EQUIPMENT_NAME      | VARCHAR(100)| 设备名称           |
| APPROVED_START_TIME | DATETIME    | 批准开始时间       |
| APPROVED_END_TIME   | DATETIME    | 批准结束时间       |
| STATUS              | VARCHAR(20) | 状态               |
| OPERATOR_NAME       | VARCHAR(50) | 操作人             |

### 3. 转供电表 (transfer_orders)

| 字段名              | 类型        | 说明               |
|---------------------|-------------|--------------------|
| ORDER_ID            | INT         | 订单ID（主键）     |
| ORDER_NO            | VARCHAR(50) | 转供电订单号       |
| TRANSFER_TYPE       | VARCHAR(20) | 转供电类型         |
| EQUIPMENT_NAME      | VARCHAR(100)| 设备名称           |
| TRANSFER_OUT_TIME   | DATETIME    | 转出开始时间       |
| TRANSFER_BACK_TIME  | DATETIME    | 转回时间           |
| STATUS              | VARCHAR(20) | 状态               |
| OPERATOR_NAME       | VARCHAR(50) | 操作人             |

### 4. 周计划表 (weekly_plans)

| 字段名              | 类型        | 说明               |
|---------------------|-------------|--------------------|
| PLAN_ID             | INT         | 计划ID（主键）     |
| PLAN_NO             | VARCHAR(50) | 周计划编号         |
| PLAN_TYPE           | VARCHAR(20) | 计划类型           |
| PLAN_NAME           | VARCHAR(100)| 计划名称           |
| EQUIPMENT_NAME      | VARCHAR(100)| 设备名称           |
| APPROVED_START_TIME | DATETIME    | 批准开始时间       |
| APPROVED_END_TIME   | DATETIME    | 批准结束时间       |
| WORK_START_TIME     | DATETIME    | 工作开始时间       |
| WORK_END_TIME       | DATETIME    | 工作结束时间       |
| STATUS              | VARCHAR(20) | 状态               |
| OPERATOR_NAME       | VARCHAR(50) | 操作人             |
| IS_LIVE_COOP        | TINYINT     | 是否带电配合       |

## 测试数据

项目提供了完整的测试数据和测试脚本：

1. **生成测试数据**：
   ```bash
   python scripts/generate_plan_workload_test_data.py
   ```

2. **SQLite测试**：
   ```bash
   python scripts/test_plan_workload_sqlite.py
   ```

3. **MySQL表创建脚本**：
   - 文件路径：`scripts/create_plan_workload_tables.sql`
   - 包含表创建和测试数据插入

## 注意事项

1. **数据库连接**：
   - 确保MySQL数据库配置正确（.env文件）
   - 确保数据库表已创建
   - 确保有足够的数据访问权限

2. **时间格式**：
   - 所有时间字段使用DATETIME类型
   - 查询时使用YYYY-MM-DD格式

3. **状态枚举值**：
   - pending: 待执行
   - executing: 执行中
   - completed: 已完成

4. **功能特点**：
   - 所有计划工作数量均可手动更改
   - 支持提前分析模式进行前瞻性评估
   - 严格按业务规则分配工作量到各班次

## 集成到现有系统

计划工作量统计功能已集成到Agent中，可以通过以下方式调用：

1. **自然语言对话**：
   ```
   用户：请统计今天的计划工作量
   用户：帮我查看明天的计划工作量，按班次分类
   ```

2. **API调用**：
   通过Agent工具接口直接调用 `calculate_plan_workload` 工具

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
- ✅ 实现计划检修工作量统计
- ✅ 实现设备投退工作量统计
- ✅ 实现转供电工作量统计
- ✅ 实现周计划工作量统计
- ✅ 支持正常分析和提前分析两种模式
- ✅ 完整的测试数据集
- ✅ 集成到Agent系统
