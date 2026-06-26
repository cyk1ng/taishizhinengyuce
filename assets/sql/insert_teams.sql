-- ============================================
-- 班组基础数据插入脚本
-- 表名: OC_SCHEDULE_TEAM
-- ============================================

-- A班 (早班 08:00-16:00)
INSERT INTO OC_SCHEDULE_TEAM (team_id, team_name, team_leader_id, team_leader_name,
    create_busi_dept_id, create_busi_dept_name, enable_flag,
    other_person_ids, other_person_names)
VALUES ('T001', 'A班', 'U001', '宗德文',
    'DEPT001', '调度中心', 'Y',
    'U101,U102,U103,U104,U105,U106,U107,U108,U109,U110',
    '王云,晏清阳,杨凡奇,李浩,王玥,何静,李光临,李杰,杨宏敬,龚瑞泉');

-- B班 (晚班 16:00-24:00)
INSERT INTO OC_SCHEDULE_TEAM (team_id, team_name, team_leader_id, team_leader_name,
    create_busi_dept_id, create_busi_dept_name, enable_flag,
    other_person_ids, other_person_names)
VALUES ('T002', 'B班', 'U002', '朱利明',
    'DEPT001', '调度中心', 'Y',
    'U201,U202,U203,U204,U205,U206',
    '张小丽,王海东,马兴源,杨智翔,丁紫笠,康林春');

-- C班 (夜班 00:00-08:00)
INSERT INTO OC_SCHEDULE_TEAM (team_id, team_name, team_leader_id, team_leader_name,
    create_busi_dept_id, create_busi_dept_name, enable_flag,
    other_person_ids, other_person_names)
VALUES ('T003', 'C班', 'U003', '余永胜',
    'DEPT001', '调度中心', 'Y',
    'U301,U302,U303,U304,U305,U306,U307',
    '王品,高恩福,杨志芳,沙成石,王一格,黄佳,耿绍胜');

-- D值 (无排班)
INSERT INTO OC_SCHEDULE_TEAM (team_id, team_name, team_leader_id, team_leader_name,
    create_busi_dept_id, create_busi_dept_name, enable_flag,
    other_person_ids, other_person_names)
VALUES ('T004', 'D值', 'U004', '韦于成',
    'DEPT001', '调度中心', 'Y',
    'U401,U402,U403,U404,U405,U406,U407,U408',
    '王梓伟,潘伟,李云川,保文鸿,杨丽丽,陶胜景,张小丽,黄佳');

-- E班 (无排班)
INSERT INTO OC_SCHEDULE_TEAM (team_id, team_name, team_leader_id, team_leader_name,
    create_busi_dept_id, create_busi_dept_name, enable_flag,
    other_person_ids, other_person_names)
VALUES ('T005', 'E班', 'U005', '王勇',
    'DEPT001', '调度中心', 'Y',
    'U501,U502,U503,U504,U505,U506',
    '欧钰慷,李燚,孙裕华,张梅,黑晓捷,宋静');

-- 乙班 (无排班)
INSERT INTO OC_SCHEDULE_TEAM (team_id, team_name, team_leader_id, team_leader_name,
    create_busi_dept_id, create_busi_dept_name, enable_flag,
    other_person_ids, other_person_names)
VALUES ('T006', '乙班', 'U006', '崔娇',
    'DEPT001', '调度中心', 'Y',
    'U601,U602',
    '桑江艳,王英子');

-- 甲班 (无排班)
INSERT INTO OC_SCHEDULE_TEAM (team_id, team_name, team_leader_id, team_leader_name,
    create_busi_dept_id, create_busi_dept_name, enable_flag,
    other_person_ids, other_person_names)
VALUES ('T007', '甲班', 'U007', '苏冀',
    'DEPT001', '调度中心', 'Y',
    'U701,U702',
    '张瑞颖,桑江艳');


-- ============================================
-- 排班记录插入脚本
-- 表名: OC_SCHEDULE_RECORD
-- 说明: 下面以当天日期为例插入今日排班
--       请将 'YYYY-MM-DD' 替换为实际日期
-- ============================================

-- 早班: A班 (08:00-16:00) - 设为在值
INSERT INTO OC_SCHEDULE_RECORD (record_id, dis_org_id, dis_org_name,
    team_id, team_name, schedule_status, change_time,
    on_duty_time, off_duty_time,
    team_leader_id, team_leader_name,
    other_person_ids, other_person_names)
VALUES ('SR_YYYYMMDD_001', 'DEPT001', '调度中心',
    'T001', 'A班', 'Y', NOW(),
    'YYYY-MM-DD 08:00:00', 'YYYY-MM-DD 16:00:00',
    'U001', '宗德文',
    'U101,U102,U103,U104,U105,U106,U107,U108,U109,U110',
    '王云,晏清阳,杨凡奇,李浩,王玥,何静,李光临,李杰,杨宏敬,龚瑞泉');

-- 晚班: B班 (16:00-24:00) - 已交班
INSERT INTO OC_SCHEDULE_RECORD (record_id, dis_org_id, dis_org_name,
    team_id, team_name, schedule_status, change_time,
    on_duty_time, off_duty_time,
    team_leader_id, team_leader_name,
    other_person_ids, other_person_names)
VALUES ('SR_YYYYMMDD_002', 'DEPT001', '调度中心',
    'T002', 'B班', 'N', NOW(),
    'YYYY-MM-DD 16:00:00', 'YYYY-MM-DD 24:00:00',
    'U002', '朱利明',
    'U201,U202,U203,U204,U205,U206',
    '张小丽,王海东,马兴源,杨智翔,丁紫笠,康林春');

-- 夜班: C班 (00:00-08:00) - 已交班
INSERT INTO OC_SCHEDULE_RECORD (record_id, dis_org_id, dis_org_name,
    team_id, team_name, schedule_status, change_time,
    on_duty_time, off_duty_time,
    team_leader_id, team_leader_name,
    other_person_ids, other_person_names)
VALUES ('SR_YYYYMMDD_003', 'DEPT001', '调度中心',
    'T003', 'C班', 'N', NOW(),
    'YYYY-MM-DD 00:00:00', 'YYYY-MM-DD 08:00:00',
    'U003', '余永胜',
    'U301,U302,U303,U304,U305,U306,U307',
    '王品,高恩福,杨志芳,沙成石,王一格,黄佳,耿绍胜');