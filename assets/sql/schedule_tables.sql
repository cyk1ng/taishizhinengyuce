-- ========================================
-- 配网调度智能预测系统 - 排班表结构
-- 数据库类型: MySQL
-- ========================================

-- 1. 上班人员表 (working_user)
CREATE TABLE IF NOT EXISTS `working_user` (
    `MK_ID` VARCHAR(36) NOT NULL COMMENT '主键ID',
    `USER_ID` VARCHAR(36) DEFAULT NULL COMMENT '用户ID',
    `USER_NAME` VARCHAR(255) DEFAULT NULL COMMENT '用户名',
    `GROUP` VARCHAR(255) DEFAULT NULL COMMENT '所属班次',
    `ID_LEADER` INT DEFAULT 0 COMMENT '值班类型(0其他值班人员,1副值,2正值,3值班长)',
    `CITY_DEPT_ID` VARCHAR(36) DEFAULT NULL COMMENT '所属地市ID',
    `CITY_DEPT_NAME` VARCHAR(255) DEFAULT NULL COMMENT '所属地市名字',
    `CREATE_TIME` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `UPDATE_TIME` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`MK_ID`),
    INDEX `idx_user_id` (`USER_ID`),
    INDEX `idx_group` (`GROUP`),
    INDEX `idx_city_dept` (`CITY_DEPT_ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='上班人员表';

-- 2. 班组表 (working_groups) - 可选，也可从working_user表中按GROUP字段分组统计
CREATE TABLE IF NOT EXISTS `working_groups` (
    `GROUP_ID` VARCHAR(36) NOT NULL COMMENT '班组ID',
    `GROUP_NAME` VARCHAR(255) DEFAULT NULL COMMENT '班组名称',
    `GROUP_TYPE` VARCHAR(50) DEFAULT '轮班' COMMENT '班组类型',
    `SHIFT_PATTERN` VARCHAR(100) DEFAULT NULL COMMENT '轮班模式',
    `CITY_DEPT_ID` VARCHAR(36) DEFAULT NULL COMMENT '所属地市ID',
    `CITY_DEPT_NAME` VARCHAR(255) DEFAULT NULL COMMENT '所属地市名字',
    `CREATE_TIME` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `UPDATE_TIME` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`GROUP_ID`),
    INDEX `idx_city_dept` (`CITY_DEPT_ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='班组表';

-- 3. 排班记录表 (work_schedule_recode)
CREATE TABLE IF NOT EXISTS `work_schedule_recode` (
    `RECORD_ID` VARCHAR(36) NOT NULL COMMENT '记录ID',
    `USER_ID` VARCHAR(36) DEFAULT NULL COMMENT '用户ID',
    `USER_NAME` VARCHAR(255) DEFAULT NULL COMMENT '用户名',
    `GROUP_ID` VARCHAR(36) DEFAULT NULL COMMENT '班组ID',
    `GROUP_NAME` VARCHAR(255) DEFAULT NULL COMMENT '班组名称',
    `SCHEDULE_DATE` DATE DEFAULT NULL COMMENT '排班日期',
    `SHIFT_TYPE` VARCHAR(20) DEFAULT NULL COMMENT '班次类型(早班/中班/晚班)',
    `START_TIME` VARCHAR(10) DEFAULT NULL COMMENT '上班时间',
    `END_TIME` VARCHAR(10) DEFAULT NULL COMMENT '下班时间',
    `STATUS` VARCHAR(20) DEFAULT '计划' COMMENT '状态(计划/执行中/已完成/取消)',
    `ID_LEADER` INT DEFAULT 0 COMMENT '值班类型(0其他值班人员,1副值,2正值,3值班长)',
    `CITY_DEPT_ID` VARCHAR(36) DEFAULT NULL COMMENT '所属地市ID',
    `CITY_DEPT_NAME` VARCHAR(255) DEFAULT NULL COMMENT '所属地市名字',
    `CREATE_TIME` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `UPDATE_TIME` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`RECORD_ID`),
    INDEX `idx_user_id` (`USER_ID`),
    INDEX `idx_schedule_date` (`SCHEDULE_DATE`),
    INDEX `idx_group_id` (`GROUP_ID`),
    INDEX `idx_city_dept` (`CITY_DEPT_ID`),
    INDEX `idx_date_shift` (`SCHEDULE_DATE`, `SHIFT_TYPE`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='排班记录表';

-- ========================================
-- 示例数据（测试用）
-- ========================================

-- 插入示例人员数据
INSERT INTO `working_user` (`MK_ID`, `USER_ID`, `USER_NAME`, `GROUP`, `ID_LEADER`, `CITY_DEPT_ID`, `CITY_DEPT_NAME`) VALUES
('U001', '001', '张伟', '一班', 3, 'DEPT001', '广州供电局'),
('U002', '002', '李明', '一班', 2, 'DEPT001', '广州供电局'),
('U003', '003', '王芳', '一班', 1, 'DEPT001', '广州供电局'),
('U004', '004', '刘强', '一班', 0, 'DEPT001', '广州供电局'),
('U005', '005', '陈红', '二班', 3, 'DEPT001', '广州供电局'),
('U006', '006', '赵刚', '二班', 2, 'DEPT001', '广州供电局'),
('U007', '007', '孙丽', '二班', 1, 'DEPT001', '广州供电局'),
('U008', '008', '周杰', '二班', 0, 'DEPT001', '广州供电局'),
('U009', '009', '吴敏', '三班', 3, 'DEPT001', '广州供电局'),
('U010', '010', '郑华', '三班', 2, 'DEPT001', '广州供电局'),
('U011', '011', '黄燕', '三班', 1, 'DEPT001', '广州供电局'),
('U012', '012', '林峰', '三班', 0, 'DEPT001', '广州供电局');

-- 插入示例班组数据
INSERT INTO `working_groups` (`GROUP_ID`, `GROUP_NAME`, `GROUP_TYPE`, `SHIFT_PATTERN`, `CITY_DEPT_ID`, `CITY_DEPT_NAME`) VALUES
('G001', '一班', '轮班', '早-中-晚-休', 'DEPT001', '广州供电局'),
('G002', '二班', '轮班', '中-晚-早-休', 'DEPT001', '广州供电局'),
('G003', '三班', '轮班', '晚-早-中-休', 'DEPT001', '广州供电局');

-- 插入示例排班记录（最近7天）
INSERT INTO `work_schedule_recode` (`RECORD_ID`, `USER_ID`, `USER_NAME`, `GROUP_ID`, `GROUP_NAME`, `SCHEDULE_DATE`, `SHIFT_TYPE`, `START_TIME`, `END_TIME`, `STATUS`, `ID_LEADER`, `CITY_DEPT_ID`, `CITY_DEPT_NAME`) VALUES
-- 2024-03-18
('R001', '001', '张伟', 'G001', '一班', '2024-03-18', '早班', '08:00', '16:00', '已完成', 3, 'DEPT001', '广州供电局'),
('R002', '002', '李明', 'G001', '一班', '2024-03-18', '早班', '08:00', '16:00', '已完成', 2, 'DEPT001', '广州供电局'),
('R003', '005', '陈红', 'G002', '二班', '2024-03-18', '中班', '16:00', '00:00', '已完成', 3, 'DEPT001', '广州供电局'),
('R004', '009', '吴敏', 'G003', '三班', '2024-03-18', '晚班', '00:00', '08:00', '已完成', 3, 'DEPT001', '广州供电局'),
-- 2024-03-19
('R005', '001', '张伟', 'G001', '一班', '2024-03-19', '中班', '16:00', '00:00', '已完成', 3, 'DEPT001', '广州供电局'),
('R006', '005', '陈红', 'G002', '二班', '2024-03-19', '晚班', '00:00', '08:00', '已完成', 3, 'DEPT001', '广州供电局'),
('R007', '009', '吴敏', 'G003', '三班', '2024-03-19', '早班', '08:00', '16:00', '已完成', 3, 'DEPT001', '广州供电局');

-- ========================================
-- 查询示例
-- ========================================

-- 查询所有人员及角色分布
-- SELECT ID_LEADER, 
--        CASE ID_LEADER 
--            WHEN 0 THEN '其他值班人员'
--            WHEN 1 THEN '副值'
--            WHEN 2 THEN '正值'
--            WHEN 3 THEN '值班长'
--        END as role_name,
--        COUNT(*) as count
-- FROM working_user
-- GROUP BY ID_LEADER;

-- 查询班组人员
-- SELECT `GROUP`, COUNT(*) as member_count
-- FROM working_user
-- GROUP BY `GROUP`;

-- 查询排班记录
-- SELECT SCHEDULE_DATE, SHIFT_TYPE, COUNT(*) as staff_count
-- FROM work_schedule_recode
-- WHERE SCHEDULE_DATE BETWEEN '2024-03-18' AND '2024-03-25'
-- GROUP BY SCHEDULE_DATE, SHIFT_TYPE
-- ORDER BY SCHEDULE_DATE, SHIFT_TYPE;
