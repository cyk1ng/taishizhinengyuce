-- ========================================
-- 配网调度智能预测系统 - 排班表结构
-- 数据库类型: MySQL
-- 版本: 2.0
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
CREATE TABLE IF NOT EXISTS `work_schedule_recode` (
    `RECORD_ID` VARCHAR(36) NOT NULL COMMENT '记录ID',
    `USER_ID` VARCHAR(36) DEFAULT NULL COMMENT '用户ID',
    `USER_NAME` VARCHAR(255) DEFAULT NULL COMMENT '用户名',
    `GROUP_NAME` VARCHAR(255) DEFAULT NULL COMMENT '班组名称',
    `SCHEDULE_DATE` DATE DEFAULT NULL COMMENT '排班日期',
    `SHIFT_TYPE` VARCHAR(20) DEFAULT NULL COMMENT '班次类型(早班/中班/晚班)',
    `STATUS` VARCHAR(20) DEFAULT '计划' COMMENT '状态(计划/执行中/已完成/取消)',
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

-- 清空旧数据（可选）
-- TRUNCATE TABLE work_schedule_recode;
-- TRUNCATE TABLE working_user;
-- TRUNCATE TABLE working_groups;

-- 插入班组数据（注意IS_ACTIVE字段）
-- 班组数量可以随意设置，这里示例5个班组
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
-- 验证查询
-- ========================================

-- 查询生效的班组
-- SELECT * FROM working_groups WHERE IS_ACTIVE = '是';

-- 查询每个班组的人员配置
-- SELECT 
--     g.GROUP_NAME,
--     g.IS_ACTIVE,
--     SUM(CASE WHEN u.ID_LEADER = 3 THEN 1 ELSE 0 END) as 值班长人数,
--     SUM(CASE WHEN u.ID_LEADER = 2 THEN 1 ELSE 0 END) as 正值人数,
--     SUM(CASE WHEN u.ID_LEADER = 1 THEN 1 ELSE 0 END) as 副值人数,
--     SUM(CASE WHEN u.ID_LEADER = 0 THEN 1 ELSE 0 END) as 其他人数,
--     COUNT(*) as 总人数
-- FROM working_groups g
-- LEFT JOIN working_user u ON g.GROUP_NAME = u.`GROUP`
-- GROUP BY g.GROUP_NAME, g.IS_ACTIVE;

-- 检查班组是否满足最低人员要求（至少1名值班长+1名正值+1名副值）
-- SELECT 
--     g.GROUP_NAME,
--     g.IS_ACTIVE,
--     CASE 
--         WHEN SUM(CASE WHEN u.ID_LEADER = 3 THEN 1 ELSE 0 END) >= 1 
--              AND SUM(CASE WHEN u.ID_LEADER = 2 THEN 1 ELSE 0 END) >= 1 
--              AND SUM(CASE WHEN u.ID_LEADER = 1 THEN 1 ELSE 0 END) >= 1 
--         THEN '满足' 
--         ELSE '不满足' 
--     END as 人员配置状态
-- FROM working_groups g
-- LEFT JOIN working_user u ON g.GROUP_NAME = u.`GROUP`
-- GROUP BY g.GROUP_NAME, g.IS_ACTIVE;
