-- ========================================
-- 配网调度智能预测系统 - 排班表结构
-- 数据库类型: MySQL
-- 版本: 2.1
-- ========================================

-- 1. 上班人员表 (working_user)
-- 角色说明：ID_LEADER - 0:其他值班人员, 1:副值, 2:正值, 3:值班长
CREATE TABLE IF NOT EXISTS `working_user` (
    `MK_ID` VARCHAR(36) NOT NULL COMMENT '主键ID',
    `USER_ID` VARCHAR(36) DEFAULT NULL COMMENT '用户ID',
    `USER_NAME` VARCHAR(255) DEFAULT NULL COMMENT '用户名',
    `GROUP` VARCHAR(255) DEFAULT NULL COMMENT '所属班组',
    `ID_LEADER` INT DEFAULT 0 COMMENT '值班类型(0其他值班人员,1副值,2正值,3值班长)',
    `CITY_DEPT_ID` VARCHAR(36) DEFAULT NULL COMMENT '所属地市ID',
    `CITY_DEPT_NAME` VARCHAR(255) DEFAULT NULL COMMENT '所属地市名字',
    `CREATE_TIME` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `UPDATE_TIME` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`MK_ID`),
    INDEX `idx_user_id` (`USER_ID`),
    INDEX `idx_group` (`GROUP`),
    INDEX `idx_leader` (`ID_LEADER`),
    INDEX `idx_city_dept` (`CITY_DEPT_ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='上班人员表';

-- 2. 班组表 (working_groups)
-- 关键字段：IS_ACTIVE - 生效状态（是/否），只有生效的班组才会被排班
CREATE TABLE IF NOT EXISTS `working_groups` (
    `GROUP_ID` VARCHAR(36) NOT NULL COMMENT '班组ID',
    `GROUP_NAME` VARCHAR(255) NOT NULL COMMENT '班组名称',
    `IS_ACTIVE` VARCHAR(10) DEFAULT '是' COMMENT '是否生效(是/否)，只有生效的班组才会被安排排班',
    `CITY_DEPT_ID` VARCHAR(36) DEFAULT NULL COMMENT '所属地市ID',
    `CITY_DEPT_NAME` VARCHAR(255) DEFAULT NULL COMMENT '所属地市名字',
    `CREATE_TIME` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `UPDATE_TIME` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`GROUP_ID`),
    INDEX `idx_group_name` (`GROUP_NAME`),
    INDEX `idx_is_active` (`IS_ACTIVE`),
    INDEX `idx_city_dept` (`CITY_DEPT_ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='班组表';

-- 3. 排班记录表 (work_schedule_recode)
-- 关键规则：一个班组一天只能排一次班（早班/中班/晚班三选一）
-- SHIFT_TYPE: 1=晚班, 2=早班, 3=中班
-- STATUS: 1=计划, 2=执行中, 3=已完成, 4=取消
CREATE TABLE IF NOT EXISTS `work_schedule_recode` (
    `RECORD_ID` VARCHAR(36) NOT NULL COMMENT '记录ID',
    `USER_ID` VARCHAR(36) DEFAULT NULL COMMENT '用户ID',
    `USER_NAME` VARCHAR(255) DEFAULT NULL COMMENT '用户名',
    `GROUP_NAME` VARCHAR(255) DEFAULT NULL COMMENT '班组名称',
    `SCHEDULE_DATE` DATE DEFAULT NULL COMMENT '排班日期',
    `SHIFT_TYPE` INT DEFAULT 2 COMMENT '班次类型(1晚班/2早班/3中班)',
    `STATUS` INT DEFAULT 1 COMMENT '状态(1计划/2执行中/3已完成/4取消)',
    `ID_LEADER` INT DEFAULT 0 COMMENT '值班类型(0其他值班人员,1副值,2正值,3值班长)',
    `CITY_DEPT_ID` VARCHAR(36) DEFAULT NULL COMMENT '所属地市ID',
    `CITY_DEPT_NAME` VARCHAR(255) DEFAULT NULL COMMENT '所属地市名字',
    `CREATE_TIME` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `UPDATE_TIME` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`RECORD_ID`),
    INDEX `idx_user_id` (`USER_ID`),
    INDEX `idx_schedule_date` (`SCHEDULE_DATE`),
    INDEX `idx_group_name` (`GROUP_NAME`),
    INDEX `idx_city_dept` (`CITY_DEPT_ID`),
    INDEX `idx_date_shift` (`SCHEDULE_DATE`, `SHIFT_TYPE`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='排班记录表';

-- ========================================
-- 示例数据（测试用）
-- ========================================

-- 插入班组数据（注意IS_ACTIVE字段）
INSERT INTO `working_groups` (`GROUP_ID`, `GROUP_NAME`, `IS_ACTIVE`, `CITY_DEPT_ID`, `CITY_DEPT_NAME`) VALUES
('G001', '一班', '是', 'DEPT001', '广州供电局'),
('G002', '二班', '是', 'DEPT001', '广州供电局'),
('G003', '三班', '是', 'DEPT001', '广州供电局'),
('G004', '四班', '是', 'DEPT001', '广州供电局'),
('G005', '五班', '否', 'DEPT001', '广州供电局');  -- 这个班组不会参与排班

-- 插入人员数据
-- 每个班组需要至少：1名值班长(ID_LEADER=3) + 1名正值(ID_LEADER=2) + 1名副值(ID_LEADER=1)

-- 一班（4人）
INSERT INTO `working_user` (`MK_ID`, `USER_ID`, `USER_NAME`, `GROUP`, `ID_LEADER`, `CITY_DEPT_ID`, `CITY_DEPT_NAME`) VALUES
('U001', '001', '张伟', '一班', 3, 'DEPT001', '广州供电局'),  -- 值班长
('U002', '002', '李明', '一班', 2, 'DEPT001', '广州供电局'),  -- 正值
('U003', '003', '王芳', '一班', 1, 'DEPT001', '广州供电局'),  -- 副值
('U004', '004', '刘强', '一班', 0, 'DEPT001', '广州供电局');  -- 其他值班人员

-- 二班（4人）
INSERT INTO `working_user` (`MK_ID`, `USER_ID`, `USER_NAME`, `GROUP`, `ID_LEADER`, `CITY_DEPT_ID`, `CITY_DEPT_NAME`) VALUES
('U005', '005', '陈红', '二班', 3, 'DEPT001', '广州供电局'),  -- 值班长
('U006', '006', '赵刚', '二班', 2, 'DEPT001', '广州供电局'),  -- 正值
('U007', '007', '孙丽', '二班', 1, 'DEPT001', '广州供电局'),  -- 副值
('U008', '008', '周杰', '二班', 0, 'DEPT001', '广州供电局');  -- 其他值班人员

-- 三班（4人）
INSERT INTO `working_user` (`MK_ID`, `USER_ID`, `USER_NAME`, `GROUP`, `ID_LEADER`, `CITY_DEPT_ID`, `CITY_DEPT_NAME`) VALUES
('U009', '009', '吴敏', '三班', 3, 'DEPT001', '广州供电局'),  -- 值班长
('U010', '010', '郑华', '三班', 2, 'DEPT001', '广州供电局'),  -- 正值
('U011', '011', '黄燕', '三班', 1, 'DEPT001', '广州供电局'),  -- 副值
('U012', '012', '林峰', '三班', 0, 'DEPT001', '广州供电局');  -- 其他值班人员

-- 四班（4人）
INSERT INTO `working_user` (`MK_ID`, `USER_ID`, `USER_NAME`, `GROUP`, `ID_LEADER`, `CITY_DEPT_ID`, `CITY_DEPT_NAME`) VALUES
('U013', '013', '杨波', '四班', 3, 'DEPT001', '广州供电局'),  -- 值班长
('U014', '014', '何静', '四班', 2, 'DEPT001', '广州供电局'),  -- 正值
('U015', '015', '徐强', '四班', 1, 'DEPT001', '广州供电局'),  -- 副值
('U016', '016', '马丽', '四班', 0, 'DEPT001', '广州供电局');  -- 其他值班人员

-- 五班（已停用，不会参与排班）
INSERT INTO `working_user` (`MK_ID`, `USER_ID`, `USER_NAME`, `GROUP`, `ID_LEADER`, `CITY_DEPT_ID`, `CITY_DEPT_NAME`) VALUES
('U017', '017', '钱伟', '五班', 3, 'DEPT001', '广州供电局'),
('U018', '018', '孙明', '五班', 2, 'DEPT001', '广州供电局'),
('U019', '019', '李芳', '五班', 1, 'DEPT001', '广州供电局');

-- ========================================
-- 插入示例排班记录（使用数字枚举）
-- SHIFT_TYPE: 1=晚班, 2=早班, 3=中班
-- STATUS: 1=计划, 2=执行中, 3=已完成, 4=取消
-- ========================================

-- 2024-03-18 排班（已完成）
INSERT INTO `work_schedule_recode` (`RECORD_ID`, `USER_ID`, `USER_NAME`, `GROUP_NAME`, `SCHEDULE_DATE`, `SHIFT_TYPE`, `STATUS`, `ID_LEADER`, `CITY_DEPT_ID`, `CITY_DEPT_NAME`) VALUES
-- 一班 早班 (SHIFT_TYPE=2)
('R001', '001', '张伟', '一班', '2024-03-18', 2, 3, 3, 'DEPT001', '广州供电局'),
('R002', '002', '李明', '一班', '2024-03-18', 2, 3, 2, 'DEPT001', '广州供电局'),
('R003', '003', '王芳', '一班', '2024-03-18', 2, 3, 1, 'DEPT001', '广州供电局'),
-- 二班 中班 (SHIFT_TYPE=3)
('R004', '005', '陈红', '二班', '2024-03-18', 3, 3, 3, 'DEPT001', '广州供电局'),
('R005', '006', '赵刚', '二班', '2024-03-18', 3, 3, 2, 'DEPT001', '广州供电局'),
-- 三班 晚班 (SHIFT_TYPE=1)
('R006', '009', '吴敏', '三班', '2024-03-18', 1, 3, 3, 'DEPT001', '广州供电局'),
('R007', '010', '郑华', '三班', '2024-03-18', 1, 3, 2, 'DEPT001', '广州供电局');

-- 2024-03-19 排班（已完成）
INSERT INTO `work_schedule_recode` (`RECORD_ID`, `USER_ID`, `USER_NAME`, `GROUP_NAME`, `SCHEDULE_DATE`, `SHIFT_TYPE`, `STATUS`, `ID_LEADER`, `CITY_DEPT_ID`, `CITY_DEPT_NAME`) VALUES
-- 四班 早班
('R008', '013', '杨波', '四班', '2024-03-19', 2, 3, 3, 'DEPT001', '广州供电局'),
('R009', '014', '何静', '四班', '2024-03-19', 2, 3, 2, 'DEPT001', '广州供电局'),
-- 一班 中班
('R010', '001', '张伟', '一班', '2024-03-19', 3, 3, 3, 'DEPT001', '广州供电局'),
('R011', '002', '李明', '一班', '2024-03-19', 3, 3, 2, 'DEPT001', '广州供电局'),
-- 二班 晚班
('R012', '005', '陈红', '二班', '2024-03-19', 1, 3, 3, 'DEPT001', '广州供电局'),
('R013', '006', '赵刚', '二班', '2024-03-19', 1, 3, 2, 'DEPT001', '广州供电局');

-- 2024-03-20 排班（执行中）
INSERT INTO `work_schedule_recode` (`RECORD_ID`, `USER_ID`, `USER_NAME`, `GROUP_NAME`, `SCHEDULE_DATE`, `SHIFT_TYPE`, `STATUS`, `ID_LEADER`, `CITY_DEPT_ID`, `CITY_DEPT_NAME`) VALUES
-- 三班 早班
('R014', '009', '吴敏', '三班', '2024-03-20', 2, 2, 3, 'DEPT001', '广州供电局'),
('R015', '010', '郑华', '三班', '2024-03-20', 2, 2, 2, 'DEPT001', '广州供电局'),
-- 四班 中班
('R016', '013', '杨波', '四班', '2024-03-20', 3, 2, 3, 'DEPT001', '广州供电局'),
('R017', '014', '何静', '四班', '2024-03-20', 3, 2, 2, 'DEPT001', '广州供电局'),
-- 一班 晚班
('R018', '001', '张伟', '一班', '2024-03-20', 1, 2, 3, 'DEPT001', '广州供电局'),
('R019', '002', '李明', '一班', '2024-03-20', 1, 2, 2, 'DEPT001', '广州供电局');

-- 2024-03-21 排班（计划中）
INSERT INTO `work_schedule_recode` (`RECORD_ID`, `USER_ID`, `USER_NAME`, `GROUP_NAME`, `SCHEDULE_DATE`, `SHIFT_TYPE`, `STATUS`, `ID_LEADER`, `CITY_DEPT_ID`, `CITY_DEPT_NAME`) VALUES
-- 二班 早班
('R020', '005', '陈红', '二班', '2024-03-21', 2, 1, 3, 'DEPT001', '广州供电局'),
('R021', '006', '赵刚', '二班', '2024-03-21', 2, 1, 2, 'DEPT001', '广州供电局'),
-- 三班 中班
('R022', '009', '吴敏', '三班', '2024-03-21', 3, 1, 3, 'DEPT001', '广州供电局'),
('R023', '010', '郑华', '三班', '2024-03-21', 3, 1, 2, 'DEPT001', '广州供电局'),
-- 四班 晚班
('R024', '013', '杨波', '四班', '2024-03-21', 1, 1, 3, 'DEPT001', '广州供电局'),
('R025', '014', '何静', '四班', '2024-03-21', 1, 1, 2, 'DEPT001', '广州供电局');

-- ========================================
-- 枚举值说明
-- ========================================
/*
SHIFT_TYPE 班次类型：
  1 = 晚班 (00:00 - 08:00)
  2 = 早班 (08:00 - 16:00)
  3 = 中班 (16:00 - 24:00)

STATUS 状态：
  1 = 计划
  2 = 执行中
  3 = 已完成
  4 = 取消
*/

-- ========================================
-- 查询示例
-- ========================================

-- 查询排班记录（显示班次和状态名称）
-- SELECT 
--     SCHEDULE_DATE,
--     CASE SHIFT_TYPE 
--         WHEN 1 THEN '晚班'
--         WHEN 2 THEN '早班'
--         WHEN 3 THEN '中班'
--     END as 班次,
--     GROUP_NAME as 班组,
--     USER_NAME as 人员,
--     CASE STATUS
--         WHEN 1 THEN '计划'
--         WHEN 2 THEN '执行中'
--         WHEN 3 THEN '已完成'
--         WHEN 4 THEN '取消'
--     END as 状态
-- FROM work_schedule_recode
-- ORDER BY SCHEDULE_DATE, SHIFT_TYPE;

-- 统计班组排班情况
-- SELECT 
--     GROUP_NAME,
--     COUNT(*) as 总班次,
--     SUM(CASE WHEN SHIFT_TYPE = 1 THEN 1 ELSE 0 END) as 晚班次数,
--     SUM(CASE WHEN SHIFT_TYPE = 2 THEN 1 ELSE 0 END) as 早班次数,
--     SUM(CASE WHEN SHIFT_TYPE = 3 THEN 1 ELSE 0 END) as 中班次数
-- FROM work_schedule_recode
-- GROUP BY GROUP_NAME;

-- 检查约束：一个班组一天是否只排了一次班
-- SELECT SCHEDULE_DATE, GROUP_NAME, COUNT(DISTINCT SHIFT_TYPE) as 班次数
-- FROM work_schedule_recode
-- GROUP BY SCHEDULE_DATE, GROUP_NAME
-- HAVING COUNT(DISTINCT SHIFT_TYPE) > 1;
