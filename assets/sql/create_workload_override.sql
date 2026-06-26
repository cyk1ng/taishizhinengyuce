-- ============================================
-- 工作量数据临时修改存储表
-- 用户在前端弹窗修改 开展中/已终结 的数字，
-- 存入此表，下次弹窗时读取覆盖源数据
-- ============================================

-- 删除已存在的表（可选，首次执行请注释掉）
-- DROP TABLE OC_WORKLOAD_OVERRIDE;

CREATE TABLE OC_WORKLOAD_OVERRIDE (
    OVERRIDE_ID     VARCHAR2(32)    PRIMARY KEY,
    WORKLOAD_TYPE   VARCHAR2(16)    NOT NULL,   -- 'plan' / 'nonplan'
    CATEGORY        VARCHAR2(32)    NOT NULL,   -- 分类标识
    FIELD_NAME      VARCHAR2(32)    NOT NULL,   -- 'in_progress' / 'completed' / 'count'
    FIELD_VALUE     NUMBER DEFAULT 0 NOT NULL,
    TARGET_DATE     VARCHAR2(10)    NOT NULL,   -- 'YYYY-MM-DD'
    CREATED_AT      TIMESTAMP DEFAULT SYSTIMESTAMP,
    UPDATED_AT      TIMESTAMP DEFAULT SYSTIMESTAMP,
    CONSTRAINT UK_WL_OVERRIDE UNIQUE (WORKLOAD_TYPE, CATEGORY, FIELD_NAME, TARGET_DATE)
);

COMMENT ON TABLE OC_WORKLOAD_OVERRIDE IS '工作量数据用户手动修正覆盖表';
COMMENT ON COLUMN OC_WORKLOAD_OVERRIDE.WORKLOAD_TYPE IS 'plan=计划工作量, nonplan=非计划工作量';
COMMENT ON COLUMN OC_WORKLOAD_OVERRIDE.CATEGORY IS '计划: maintenance/transfer/equipment/weekly_plan/protect；非计划: fault/defect/overload';
COMMENT ON COLUMN OC_WORKLOAD_OVERRIDE.FIELD_NAME IS 'in_progress=开展中, completed=已终结, count=数量';
COMMENT ON COLUMN OC_WORKLOAD_OVERRIDE.FIELD_VALUE IS '用户修改后的数字';
COMMENT ON COLUMN OC_WORKLOAD_OVERRIDE.TARGET_DATE IS '数据所属日期';
