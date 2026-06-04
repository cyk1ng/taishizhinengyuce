# 配网调度业务量智能预测系统 - 数据表清单

## 📋 数据表总览

系统共包含 **12张数据表**，分为三大类：
- **排班管理相关表**（3张）
- **工作量统计相关表**（9张）

---

## 🔧 一、排班管理相关表（3张）

### 文件位置
`/workspace/projects/assets/sql/schedule_tables.sql`

### 1. 上班人员表 (working_user)

**用途**：存储值班人员基本信息和角色配置

**字段说明**：

| 字段名 | 类型 | 说明 | 备注 |
|--------|------|------|------|
| MK_ID | VARCHAR(36) | 主键ID | 必填 |
| USER_ID | VARCHAR(36) | 用户ID | - |
| USER_NAME | VARCHAR(255) | 用户名 | - |
| GROUP | VARCHAR(255) | 所属班组 | 关联 working_groups 表 |
| ID_LEADER | INT | 值班类型 | **枚举值**：0=其他值班人员, 1=副值, 2=正值, 3=值班长 |
| CITY_DEPT_ID | VARCHAR(36) | 所属地市ID | - |
| CITY_DEPT_NAME | VARCHAR(255) | 所属地市名称 | - |
| CREATE_TIME | DATETIME | 创建时间 | 自动填充 |
| UPDATE_TIME | DATETIME | 更新时间 | 自动更新 |

**索引**：
- PRIMARY KEY (MK_ID)
- INDEX idx_user_id (USER_ID)
- INDEX idx_group (GROUP)
- INDEX idx_leader (ID_LEADER)
- INDEX idx_city_dept (CITY_DEPT_ID)

---

### 2. 班组表 (working_groups)

**用途**：存储班组信息和生效状态

**字段说明**：

| 字段名 | 类型 | 说明 | 备注 |
|--------|------|------|------|
| GROUP_ID | VARCHAR(36) | 班组ID | 主键 |
| GROUP_NAME | VARCHAR(255) | 班组名称 | 必填 |
| IS_ACTIVE | VARCHAR(10) | 是否生效 | **重要**：只有'是'的班组才会被排班 |
| CITY_DEPT_ID | VARCHAR(36) | 所属地市ID | - |
| CITY_DEPT_NAME | VARCHAR(255) | 所属地市名称 | - |
| CREATE_TIME | DATETIME | 创建时间 | 自动填充 |
| UPDATE_TIME | DATETIME | 更新时间 | 自动更新 |

**索引**：
- PRIMARY KEY (GROUP_ID)
- INDEX idx_group_name (GROUP_NAME)
- INDEX idx_is_active (IS_ACTIVE)
- INDEX idx_city_dept (CITY_DEPT_ID)

**注意**：IS_ACTIVE字段是关键字段，只有设置为'是'的班组才会参与排班。

---

### 3. 排班记录表 (work_schedule_recode)

**用途**：存储排班记录和班次信息

**字段说明**：

| 字段名 | 类型 | 说明 | 备注 |
|--------|------|------|------|
| RECORD_ID | VARCHAR(36) | 记录ID | 主键 |
| USER_ID | VARCHAR(36) | 用户ID | - |
| USER_NAME | VARCHAR(255) | 用户名 | - |
| GROUP_NAME | VARCHAR(255) | 班组名称 | - |
| SCHEDULE_DATE | DATE | 排班日期 | - |
| SHIFT_TYPE | INT | 班次类型 | **枚举值**：1=晚班(00:00-08:00), 2=早班(08:00-16:00), 3=中班(16:00-24:00) |
| STATUS | INT | 状态 | **枚举值**：1=计划, 2=执行中, 3=已完成, 4=取消 |
| ID_LEADER | INT | 值班类型 | **枚举值**：0=其他, 1=副值, 2=正值, 3=值班长 |
| CITY_DEPT_ID | VARCHAR(36) | 所属地市ID | - |
| CITY_DEPT_NAME | VARCHAR(255) | 所属地市名称 | - |
| CREATE_TIME | DATETIME | 创建时间 | 自动填充 |
| UPDATE_TIME | DATETIME | 更新时间 | 自动更新 |

**索引**：
- PRIMARY KEY (RECORD_ID)
- INDEX idx_user_id (USER_ID)
- INDEX idx_schedule_date (SCHEDULE_DATE)
- INDEX idx_group_name (GROUP_NAME)
- INDEX idx_city_dept (CITY_DEPT_ID)
- INDEX idx_date_shift (SCHEDULE_DATE, SHIFT_TYPE)

**重要约束**：
- 一个班组一天只能排一次班（早/中/晚三选一）

---

## 📊 二、工作量统计相关表（9张）

### 文件位置
`/workspace/projects/assets/sql/workload_tables.sql`

### 1. 检修业务表 (maintenance_records)

**用途**：记录停电检修、复电等业务

**字段说明**：

| 字段名 | 类型 | 说明 | 备注 |
|--------|------|------|------|
| RECORD_ID | VARCHAR(36) | 记录ID | 主键 |
| WORK_ORDER_NO | VARCHAR(64) | 工单编号 | - |
| OPERATION_TYPE | VARCHAR(20) | 操作类型 | power_off=停电, power_on=复电 |
| ORDER_TYPE | VARCHAR(20) | 下令方式 | phone=电话令, network=网络令 |
| EQUIPMENT_NAME | VARCHAR(255) | 设备名称 | - |
| EQUIPMENT_ID | VARCHAR(64) | 设备ID | - |
| VOLTAGE_LEVEL | VARCHAR(20) | 电压等级 | - |
| MAINTENANCE_CONTENT | TEXT | 检修内容 | - |
| PLAN_START_TIME | DATETIME | 计划开始时间 | - |
| PLAN_END_TIME | DATETIME | 计划结束时间 | - |
| ACTUAL_START_TIME | DATETIME | 实际开始时间（批复停电时间） | - |
| ACTUAL_END_TIME | DATETIME | 实际结束时间（复电时间） | - |
| START_TIME | DATETIME | 操作开始时间（用于工作量统计） | **关键字段** |
| END_TIME | DATETIME | 操作结束时间 | **关键字段** |
| STATUS | VARCHAR(20) | 状态 | pending/executing/completed |
| OPERATOR_ID | VARCHAR(64) | 操作人ID | - |
| OPERATOR_NAME | VARCHAR(64) | 操作人姓名 | - |
| CITY_DEPT_ID | VARCHAR(36) | 所属地市ID | - |
| CITY_DEPT_NAME | VARCHAR(255) | 所属地市名称 | - |
| CREATE_TIME | DATETIME | 创建时间 | 自动填充 |
| UPDATE_TIME | DATETIME | 更新时间 | 自动更新 |

**权重**（用于工作当量计算）：
- 停电(电话下令): 0.5
- 停电(网络令): 0.2
- 复电(电话下令): 0.75
- 复电(网络令): 0.3

---

### 2. 转供电/方式单表 (transfer_orders)

**用途**：记录转供电操作

**字段说明**：

| 字段名 | 类型 | 说明 | 备注 |
|--------|------|------|------|
| ORDER_ID | VARCHAR(36) | 方式单ID | 主键 |
| ORDER_NO | VARCHAR(64) | 方式单编号 | - |
| TRANSFER_TYPE | VARCHAR(20) | 类型 | transfer=转出, restore=恢复 |
| EQUIPMENT_NAME | VARCHAR(255) | 设备名称 | - |
| EQUIPMENT_ID | VARCHAR(64) | 设备ID | - |
| TRANSFER_REASON | TEXT | 转供电原因 | - |
| TRANSFER_OUT_TIME | DATETIME | 批复转出时间 | - |
| TRANSFER_BACK_TIME | DATETIME | 批复恢复时间 | - |
| START_TIME | DATETIME | 操作开始时间（用于工作量统计） | **关键字段** |
| END_TIME | DATETIME | 操作结束时间 | - |
| STATUS | VARCHAR(20) | 状态 | - |
| OPERATOR_ID | VARCHAR(64) | 操作人ID | - |
| OPERATOR_NAME | VARCHAR(64) | 操作人姓名 | - |
| CITY_DEPT_ID | VARCHAR(36) | 所属地市ID | - |
| CITY_DEPT_NAME | VARCHAR(255) | 所属地市名称 | - |
| CREATE_TIME | DATETIME | 创建时间 | 自动填充 |
| UPDATE_TIME | DATETIME | 更新时间 | 自动更新 |

**权重**：转供电 = 0.2

---

### 3. 周计划表 (weekly_plans)

**用途**：记录周计划任务

**字段说明**：

| 字段名 | 类型 | 说明 | 备注 |
|--------|------|------|------|
| PLAN_ID | VARCHAR(36) | 计划ID | 主键 |
| PLAN_NO | VARCHAR(64) | 计划编号 | - |
| PLAN_TYPE | VARCHAR(20) | 计划类型 | live_work=带电, commissioning=投产 |
| PLAN_NAME | VARCHAR(255) | 计划名称 | - |
| WORK_CONTENT | TEXT | 工作内容 | - |
| EQUIPMENT_NAME | VARCHAR(255) | 设备名称 | - |
| EQUIPMENT_ID | VARCHAR(64) | 设备ID | - |
| PLAN_START_TIME | DATETIME | 计划开始时间 | - |
| PLAN_END_TIME | DATETIME | 计划结束时间 | - |
| ACTUAL_START_TIME | DATETIME | 实际开始时间 | - |
| ACTUAL_END_TIME | DATETIME | 实际结束时间 | - |
| START_TIME | DATETIME | 操作开始时间（用于工作量统计） | **关键字段** |
| END_TIME | DATETIME | 操作结束时间 | - |
| STATUS | VARCHAR(20) | 状态 | pending/executing/archived |
| IS_LIVE_COOP | TINYINT | 是否带电配合投产 | 0=否, 1=是 |
| OPERATOR_ID | VARCHAR(64) | 操作人ID | - |
| OPERATOR_NAME | VARCHAR(64) | 操作人姓名 | - |
| CITY_DEPT_ID | VARCHAR(36) | 所属地市ID | - |
| CITY_DEPT_NAME | VARCHAR(255) | 所属地市名称 | - |
| CREATE_TIME | DATETIME | 创建时间 | 自动填充 |
| UPDATE_TIME | DATETIME | 更新时间 | 自动更新 |

**权重**：
- 周计划(只带电): 0.2
- 周计划(只投产): 0.3
- 周计划(带电配合投产): 0.5（0.2+0.3）

---

### 4. 设备投退表 (equipment_operations)

**用途**：记录新设备投退运

**字段说明**：

| 字段名 | 类型 | 说明 | 备注 |
|--------|------|------|------|
| OPERATION_ID | VARCHAR(36) | 操作ID | 主键 |
| OPERATION_NO | VARCHAR(64) | 操作编号 | - |
| OPERATION_TYPE | VARCHAR(20) | 操作类型 | commissioning=投运, decommissioning=退运 |
| EQUIPMENT_NAME | VARCHAR(255) | 设备名称 | - |
| EQUIPMENT_ID | VARCHAR(64) | 设备ID | - |
| EQUIPMENT_TYPE | VARCHAR(50) | 设备类型 | - |
| VOLTAGE_LEVEL | VARCHAR(20) | 电压等级 | - |
| OPERATION_REASON | TEXT | 投退原因 | - |
| APPROVED_START_TIME | DATETIME | 批复开始时间 | - |
| APPROVED_END_TIME | DATETIME | 批复结束时间 | - |
| START_TIME | DATETIME | 操作开始时间（用于工作量统计） | **关键字段** |
| END_TIME | DATETIME | 操作结束时间 | - |
| STATUS | VARCHAR(20) | 状态 | - |
| OPERATOR_ID | VARCHAR(64) | 操作人ID | - |
| OPERATOR_NAME | VARCHAR(64) | 操作人姓名 | - |
| CITY_DEPT_ID | VARCHAR(36) | 所属地市ID | - |
| CITY_DEPT_NAME | VARCHAR(255) | 所属地市名称 | - |
| CREATE_TIME | DATETIME | 创建时间 | 自动填充 |
| UPDATE_TIME | DATETIME | 更新时间 | 自动更新 |

**权重**：设备投退 = 0.75

---

### 5. 故障日志表 (fault_logs)

**用途**：记录跳闸故障

**字段说明**：

| 字段名 | 类型 | 说明 | 备注 |
|--------|------|------|------|
| FAULT_ID | VARCHAR(36) | 故障ID | 主键 |
| FAULT_NO | VARCHAR(64) | 故障编号 | - |
| FAULT_TYPE | VARCHAR(20) | 故障类型 | known=确定, unknown=不确定 |
| FAULT_LEVEL | VARCHAR(20) | 故障等级 | - |
| EQUIPMENT_NAME | VARCHAR(255) | 故障设备名称 | - |
| EQUIPMENT_ID | VARCHAR(64) | 故障设备ID | - |
| FAULT_LOCATION | VARCHAR(255) | 故障位置 | - |
| FAULT_TIME | DATETIME | 跳闸时间 | **关键字段** |
| RESTORE_TIME | DATETIME | 预计恢复送电时间 | - |
| ACTUAL_RESTORE_TIME | DATETIME | 实际恢复时间 | - |
| RECLOSE_RESULT | VARCHAR(20) | 重合结果 | success=成功, fail=失败 |
| FAULT_REASON | TEXT | 故障原因 | - |
| HANDLE_MEASURE | TEXT | 处理措施 | - |
| STATUS | VARCHAR(20) | 状态 | handling, resolved |
| HANDLER_ID | VARCHAR(64) | 处理人ID | - |
| HANDLER_NAME | VARCHAR(64) | 处理人姓名 | - |
| CITY_DEPT_ID | VARCHAR(36) | 所属地市ID | - |
| CITY_DEPT_NAME | VARCHAR(255) | 所属地市名称 | - |
| CREATE_TIME | DATETIME | 创建时间 | 自动填充 |
| UPDATE_TIME | DATETIME | 更新时间 | 自动更新 |

**权重**：
- 跳闸重合成功: 0.1
- 跳闸重合不成功(确定故障): 0.3
- 跳闸重合不成功(不确定故障): 0.5

---

### 6. 缺陷记录表 (defect_records)

**用途**：记录设备缺陷

**字段说明**：

| 字段名 | 类型 | 说明 | 备注 |
|--------|------|------|------|
| DEFECT_ID | VARCHAR(36) | 缺陷ID | 主键 |
| DEFECT_NO | VARCHAR(64) | 缺陷编号 | - |
| DEFECT_TYPE | VARCHAR(50) | 缺陷类型 | - |
| DEFECT_LEVEL | VARCHAR(20) | 缺陷等级 | critical=紧急, major=重大, minor=一般 |
| EQUIPMENT_NAME | VARCHAR(255) | 设备名称 | - |
| EQUIPMENT_ID | VARCHAR(64) | 设备ID | - |
| DEFECT_DESCRIPTION | TEXT | 缺陷描述 | - |
| DISCOVERY_TIME | DATETIME | 发现时间 | **关键字段** |
| REPORT_TIME | DATETIME | 上报时间 | - |
| PLAN_HANDLE_TIME | DATETIME | 计划处理时间 | - |
| ACTUAL_HANDLE_TIME | DATETIME | 实际处理时间 | - |
| EXPECTED_DURATION | INT | 预计处理时长（分钟） | - |
| HANDLE_METHOD | TEXT | 处理方法 | - |
| STATUS | VARCHAR(20) | 状态 | pending, handling, resolved |
| HANDLER_ID | VARCHAR(64) | 处理人ID | - |
| HANDLER_NAME | VARCHAR(64) | 处理人姓名 | - |
| CITY_DEPT_ID | VARCHAR(36) | 所属地市ID | - |
| CITY_DEPT_NAME | VARCHAR(255) | 所属地市名称 | - |
| CREATE_TIME | DATETIME | 创建时间 | 自动填充 |
| UPDATE_TIME | DATETIME | 更新时间 | 自动更新 |

**权重**：故障缺陷 = 0.5

---

### 7. 重过载记录表 (overload_records)

**用途**：记录设备重过载情况

**字段说明**：

| 字段名 | 类型 | 说明 | 备注 |
|--------|------|------|------|
| RECORD_ID | VARCHAR(36) | 记录ID | 主键 |
| EQUIPMENT_NAME | VARCHAR(255) | 设备名称 | - |
| EQUIPMENT_ID | VARCHAR(64) | 设备ID | - |
| EQUIPMENT_TYPE | VARCHAR(50) | 设备类型 | transformer=变压器, line=线路 |
| RATED_CAPACITY | DECIMAL(10,2) | 额定容量 | - |
| ACTUAL_LOAD | DECIMAL(10,2) | 实际负载 | - |
| LOAD_RATE | DECIMAL(5,2) | 负载率（%） | - |
| OVERLOAD_START_TIME | DATETIME | 过载开始时间 | **关键字段** |
| OVERLOAD_END_TIME | DATETIME | 过载结束时间 | - |
| OVERLOAD_DURATION | INT | 过载持续时间（分钟） | - |
| OVERLOAD_REASON | TEXT | 过载原因 | - |
| MEASURE_TAKEN | TEXT | 采取措施 | - |
| STATUS | VARCHAR(20) | 状态 | active=活动中, resolved=已结束 |
| CITY_DEPT_ID | VARCHAR(36) | 所属地市ID | - |
| CITY_DEPT_NAME | VARCHAR(255) | 所属地市名称 | - |
| CREATE_TIME | DATETIME | 创建时间 | 自动填充 |
| UPDATE_TIME | DATETIME | 更新时间 | 自动更新 |

**权重**：重过载 = 0.1

---

### 8. 保供电记录表 (power_supply_protection)

**用途**：记录保供电任务

**字段说明**：

| 字段名 | 类型 | 说明 | 备注 |
|--------|------|------|------|
| PROTECTION_ID | VARCHAR(36) | 保供电ID | 主键 |
| PROTECTION_NAME | VARCHAR(255) | 保供电名称 | - |
| PROTECTION_LEVEL | VARCHAR(20) | 保供电等级 | - |
| PROTECTION_TYPE | VARCHAR(50) | 保供电类型 | - |
| LOCATION | VARCHAR(255) | 保供电地点 | - |
| START_TIME | DATETIME | 保供电开始时间 | **关键字段** |
| END_TIME | DATETIME | 保供电结束时间 | - |
| KEY_EQUIPMENT | TEXT | 关键设备清单 | - |
| REQUIREMENTS | TEXT | 保供电要求 | - |
| RESPONSIBLE_PERSON | VARCHAR(64) | 负责人 | - |
| RESPONSIBLE_PHONE | VARCHAR(20) | 负责人电话 | - |
| STATUS | VARCHAR(20) | 状态 | planned, executing, completed |
| CITY_DEPT_ID | VARCHAR(36) | 所属地市ID | - |
| CITY_DEPT_NAME | VARCHAR(255) | 所属地市名称 | - |
| CREATE_TIME | DATETIME | 创建时间 | 自动填充 |
| UPDATE_TIME | DATETIME | 更新时间 | 自动更新 |

**权重**：保供电 = 0.1

---

### 9. 操作票表 (operation_tickets)

**用途**：记录各类操作票

**字段说明**：

| 字段名 | 类型 | 说明 | 备注 |
|--------|------|------|------|
| TICKET_ID | VARCHAR(36) | 票据ID | 主键 |
| TICKET_NO | VARCHAR(64) | 票据编号 | - |
| TICKET_TYPE | VARCHAR(30) | 票据类型 | step_by_step=逐项操作命令票, instruction=指令记录, comprehensive=综合操作命令票, permit=调度操作许可令 |
| OPERATION_CONTENT | TEXT | 操作内容 | - |
| EQUIPMENT_NAME | VARCHAR(255) | 操作设备 | - |
| EQUIPMENT_ID | VARCHAR(64) | 设备ID | - |
| ISSUE_TIME | DATETIME | 发令时间 | - |
| EXECUTE_START_TIME | DATETIME | 执行开始时间 | - |
| EXECUTE_END_TIME | DATETIME | 执行结束时间 | - |
| STATUS | VARCHAR(20) | 状态 | draft, issued, executing, completed |
| ISSUER_ID | VARCHAR(64) | 发令人ID | - |
| ISSUER_NAME | VARCHAR(64) | 发令人姓名 | - |
| EXECUTOR_ID | VARCHAR(64) | 执行人ID | - |
| EXECUTOR_NAME | VARCHAR(64) | 执行人姓名 | - |
| CITY_DEPT_ID | VARCHAR(36) | 所属地市ID | - |
| CITY_DEPT_NAME | VARCHAR(255) | 所属地市名称 | - |
| CREATE_TIME | DATETIME | 创建时间 | 自动填充 |
| UPDATE_TIME | DATETIME | 更新时间 | 自动更新 |

---

### 10. 小时工作量统计表 (hourly_workload_stats)

**用途**：存储每小时工作量统计结果

**字段说明**：

| 字段名 | 类型 | 说明 | 备注 |
|--------|------|------|------|
| STAT_ID | VARCHAR(36) | 统计ID | 主键 |
| STAT_DATE | DATE | 统计日期 | - |
| STAT_HOUR | TINYINT | 统计小时（0-23） | - |
| PLAN_TASK_COUNT | INT | 计划任务数 | - |
| NON_PLAN_TASK_COUNT | INT | 非计划任务数 | - |
| TOTAL_TASK_COUNT | INT | 总任务数 | - |
| PLAN_EQUIVALENT | DECIMAL(10,2) | 计划工作当量 | - |
| NON_PLAN_EQUIVALENT | DECIMAL(10,2) | 非计划工作当量 | - |
| TOTAL_EQUIVALENT | DECIMAL(10,2) | 总工作当量 | - |
| STAFF_COUNT | INT | 当值人数 | - |
| STAFF_CAPACITY | DECIMAL(10,2) | 人员工作当量 | - |
| IS_OVERLOAD | TINYINT | 是否超负荷 | 0=否, 1=是 |
| NEED_EXTRA_STAFF | INT | 需增派人数 | - |
| CALC_TIME | DATETIME | 计算时间 | 自动填充 |

**索引**：
- PRIMARY KEY (STAT_ID)
- UNIQUE INDEX idx_date_hour (STAT_DATE, STAT_HOUR)
- INDEX idx_stat_date (STAT_DATE)
- INDEX idx_is_overload (IS_OVERLOAD)

---

### 11. 日工作量汇总表 (daily_workload_summary)

**用途**：存储每日工作量汇总

**字段说明**：

| 字段名 | 类型 | 说明 | 备注 |
|--------|------|------|------|
| SUMMARY_ID | VARCHAR(36) | 汇总ID | 主键 |
| STAT_DATE | DATE | 统计日期 | - |
| TOTAL_PLAN_COUNT | INT | 计划任务总数 | - |
| TOTAL_NON_PLAN_COUNT | INT | 非计划任务总数 | - |
| TOTAL_COUNT | INT | 总任务数 | - |
| TOTAL_PLAN_EQUIVALENT | DECIMAL(10,2) | 计划工作当量总计 | - |
| TOTAL_NON_PLAN_EQUIVALENT | DECIMAL(10,2) | 非计划工作当量总计 | - |
| TOTAL_EQUIVALENT | DECIMAL(10,2) | 总工作当量 | - |
| OVERLOAD_HOUR_COUNT | INT | 超负荷时段数 | - |
| TOTAL_NEED_EXTRA_STAFF | INT | 需增派人员总计 | - |
| PEAK_HOUR | TINYINT | 峰值时段 | - |
| PEAK_EQUIVALENT | DECIMAL(10,2) | 峰值当量 | - |
| CALC_TIME | DATETIME | 计算时间 | 自动填充 |

**索引**：
- PRIMARY KEY (SUMMARY_ID)
- UNIQUE INDEX idx_stat_date (STAT_DATE)

---

## 🔍 三、数据表使用指南

### 排班系统核心表
1. **working_user**：存储所有值班人员信息
2. **working_groups**：存储班组信息，IS_ACTIVE字段决定是否参与排班
3. **work_schedule_recode**：存储排班记录，一个班组一天只能排一次班

### 工作量统计核心表
1. **计划任务表**：
   - maintenance_records（检修业务）
   - transfer_orders（转供电）
   - weekly_plans（周计划）
   - equipment_operations（设备投退）

2. **非计划任务表**：
   - fault_logs（故障日志）
   - defect_records（缺陷记录）
   - overload_records（重过载）
   - power_supply_protection（保供电）

3. **统计结果表**：
   - hourly_workload_stats（小时统计）
   - daily_workload_summary（日汇总）

### 关键时间字段
所有业务表中，用于工作量统计的关键时间字段：
- **START_TIME**：操作开始时间（用于判断时段）
- **END_TIME**：操作结束时间

### 枚举值说明

#### SHIFT_TYPE（班次类型）
- 1 = 晚班 (00:00 - 08:00)
- 2 = 早班 (08:00 - 16:00)
- 3 = 中班 (16:00 - 24:00)

#### STATUS（状态）
- 1 = 计划
- 2 = 执行中
- 3 = 已完成
- 4 = 取消

#### ID_LEADER（值班类型）
- 0 = 其他值班人员
- 1 = 副值
- 2 = 正值
- 3 = 值班长

---

## 📝 四、数据库初始化步骤

1. **创建数据库**
   ```sql
   CREATE DATABASE dispatch_system DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   USE dispatch_system;
   ```

2. **执行排班表SQL**
   ```bash
   mysql -u root -p dispatch_system < /workspace/projects/assets/sql/schedule_tables.sql
   ```

3. **执行工作量表SQL**
   ```bash
   mysql -u root -p dispatch_system < /workspace/projects/assets/sql/workload_tables.sql
   ```

4. **验证表创建**
   ```sql
   SHOW TABLES;
   -- 应显示12张表
   ```

---

## 🔧 五、配置数据库连接

在项目根目录创建 `.env` 文件：

```bash
# 数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_NAME=dispatch_system
DB_USER=root
DB_PASSWORD=your_password
```

---

## 📚 六、相关文档

- 架构设计文档：`/workspace/projects/docs/ARCHITECTURE.md`
- 排班表SQL：`/workspace/projects/assets/sql/schedule_tables.sql`
- 工作量表SQL：`/workspace/projects/assets/sql/workload_tables.sql`

---

## ⚠️ 七、重要提示

1. **IS_ACTIVE字段**：working_groups表中的IS_ACTIVE字段必须设置为'是'才能参与排班
2. **一个班组一天只排一次班**：这是核心约束，需要在应用层和数据库层都保证
3. **时间字段**：START_TIME和END_TIME是工作量统计的关键字段，必须准确填写
4. **枚举值**：严格遵守枚举值定义，不要使用字符串描述

---

如有疑问，请参考 SQL 文件中的注释和示例查询语句。
