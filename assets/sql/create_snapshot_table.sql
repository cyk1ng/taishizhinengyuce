-- 页面数据快照表
-- 用于存储当前页面展示的数据，用户在界面上修改后也更新此表
-- AI 分析时从此表读取数据，而非从原始数据库表重新查询
CREATE TABLE DISPATCH_PAGE_SNAPSHOT (
    snapshot_date DATE PRIMARY KEY,
    page_data CLOB,          -- 完整页面数据 JSON
    data_hash VARCHAR2(64),  -- 数据哈希，用于快速比较
    created_at TIMESTAMP DEFAULT SYSTIMESTAMP,
    updated_at TIMESTAMP DEFAULT SYSTIMESTAMP
);