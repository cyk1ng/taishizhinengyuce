"""
Oracle 数据库连接模块（参考代码）
===============================
连接你提供的 Oracle 库 10.111.134.211:1521/domsdb，
替代当前内存模拟的 ScheduleDataProvider 降级数据。

使用方法：
    1. 安装依赖：
       uv add oracledb

    2. 在 scheduling.py 的 ScheduleDataProvider 中，
       将 get_teams() / get_records() 的 mock 逻辑替换为
       调用本模块的 query_teams() / query_records()

    3. 如果连接失败，自动回退到当前的内存 mock 数据
"""

import os
import datetime
from typing import Optional
from dataclasses import dataclass

# ============================================
# Oracle 连接配置
# ============================================
ORACLE_CONFIG = {
    "host": os.getenv("ORACLE_HOST", "10.111.134.211"),
    "port": int(os.getenv("ORACLE_PORT", "1521")),
    "service_name": os.getenv("ORACLE_SERVICE_NAME", "domsdb"),
    "user": os.getenv("ORACLE_USER", "DOMS_JADP"),
    "password": os.getenv("ORACLE_PASSWORD", "doms_jadp"),
}

# TNS 连接串（从你图片中的 JDBC URL 转换而来）
# jdbc:oracle:thin:@(DESCRIPTION=...)
TNS_CONNECT_STRING = (
    "(DESCRIPTION="
    "(ADDRESS_LIST="
    "(ADDRESS=(PROTOCOL=TCP)(HOST=10.111.134.211)(PORT=1521))"
    "(ADDRESS=(PROTOCOL=TCP)(HOST=10.111.134.211)(PORT=1521))"
    "(LOAD_BALANCE=yes)"
    ")"
    "(CONNECT_DATA="
    "(SERVER=DEDICATED)"
    "(SERVICE_NAME=domsdb)"
    "(FAILOVER_MODE=(TYPE=SELECT)(METHOD=BASIC)(RETRIES=30)(DELAY=15))"
    ")"
    ")"
)


def get_oracle_connection():
    """获取 Oracle 数据库连接（使用 oracledb 驱动）"""
    import oracledb
    oracledb.init_oracle_client()  # 如果安装了 Oracle Instant Client

    conn = oracledb.connect(
        user=ORACLE_CONFIG["user"],
        password=ORACLE_CONFIG["password"],
        dsn=TNS_CONNECT_STRING,
        # 或者使用简写形式：
        # host=ORACLE_CONFIG["host"],
        # port=ORACLE_CONFIG["port"],
        # service_name=ORACLE_CONFIG["service_name"],
    )
    return conn


# ============================================
# 查询班组数据 (OC_SCHEDULE_TEAM)
# ============================================
def query_teams(city_dept_id: str = "") -> list[dict]:
    """
    查询 OC_SCHEDULE_TEAM 表，返回所有启用的班组。

    表结构（从数据推断）：
        OC_SCHEDULE_TEAM:
            - TEAM_ID        VARCHAR2(32)    -- 班组ID (主键)
            - TEAM_NAME      VARCHAR2(32)    -- 班组名称 (A班/B班/C班/D值/E班)
            - TEAM_LEADER_NAME VARCHAR2(32)  -- 值班长姓名
            - PERSON_IDS     VARCHAR2(500)   -- 人员ID列表（逗号分隔）
            - PERSON_NAMES   VARCHAR2(1000)  -- 人员姓名列表（逗号分隔）
            - SUGGESTED_COUNT NUMBER         -- 建议值班人数
            - CITY_DEPT_ID   VARCHAR2(32)    -- 城市/部门ID
            - ENABLE_FLAG    CHAR(1)         -- 启用标志 (Y/N)
            - SHIFT_TYPE     VARCHAR2(16)    -- 班次类型 (早班/晚班/夜班)
    """
    try:
        conn = get_oracle_connection()
        cursor = conn.cursor()

        sql = """
            SELECT
                TEAM_ID,
                TEAM_NAME,
                TEAM_LEADER_NAME,
                PERSON_IDS,
                PERSON_NAMES,
                SUGGESTED_COUNT,
                CITY_DEPT_ID,
                SHIFT_TYPE
            FROM OC_SCHEDULE_TEAM
            WHERE ENABLE_FLAG = 'Y'
        """
        params = []
        if city_dept_id:
            sql += " AND CITY_DEPT_ID = :1"
            params.append(city_dept_id)

        sql += " ORDER BY TEAM_NAME"
        cursor.execute(sql, params)

        teams = []
        for row in cursor.fetchall():
            teams.append({
                "team_id": row[0],
                "team_name": row[1],
                "team_leader_name": row[2],
                "person_ids": row[3].split(",") if row[3] else [],
                "person_names": row[4].split(",") if row[4] else [],
                "suggested_count": row[5] or 0,
                "city_dept_id": row[6],
                "shift_type": row[7] or "",
            })

        cursor.close()
        conn.close()
        return teams

    except Exception as e:
        print(f"[OracleDB] 查询班组失败: {e}")
        return []


# ============================================
# 查询排班记录 (OC_SCHEDULE_RECORD)
# ============================================
def query_records(
    start_date: datetime.date,
    end_date: datetime.date,
    city_dept_id: str = ""
) -> list[dict]:
    """
    查询 OC_SCHEDULE_RECORD 表，获取指定日期范围的排班记录。

    表结构（从数据推断）：
        OC_SCHEDULE_RECORD:
            - RECORD_ID       VARCHAR2(32)    -- 记录ID (主键)
            - TEAM_ID         VARCHAR2(32)    -- 班组ID
            - TEAM_NAME       VARCHAR2(32)    -- 班组名称
            - SCHEDULE_DATE   DATE            -- 排班日期
            - SHIFT_TYPE      VARCHAR2(16)    -- 班次类型
            - ON_DUTY_TIME    DATE            -- 上班时间
            - OFF_DUTY_TIME   DATE            -- 下班时间
            - SCHEDULE_STATUS CHAR(1)         -- 排班状态 (Y=当值/N=休息)
            - CITY_DEPT_ID    VARCHAR2(32)    -- 城市/部门ID
            - TEMP_PERSON_IDS VARCHAR2(500)   -- 临时人员ID列表
            - TEMP_PERSON_NAMES VARCHAR2(1000) -- 临时人员姓名列表
    """
    try:
        conn = get_oracle_connection()
        cursor = conn.cursor()

        sql = """
            SELECT
                RECORD_ID,
                TEAM_ID,
                TEAM_NAME,
                SCHEDULE_DATE,
                SHIFT_TYPE,
                ON_DUTY_TIME,
                OFF_DUTY_TIME,
                SCHEDULE_STATUS,
                CITY_DEPT_ID,
                TEMP_PERSON_IDS,
                TEMP_PERSON_NAMES
            FROM OC_SCHEDULE_RECORD
            WHERE SCHEDULE_DATE >= :1
              AND SCHEDULE_DATE <= :2
        """
        params = [start_date, end_date]

        if city_dept_id:
            sql += " AND CITY_DEPT_ID = :3"
            params.append(city_dept_id)

        sql += " ORDER BY SCHEDULE_DATE, TEAM_NAME"
        cursor.execute(sql, params)

        records = []
        for row in cursor.fetchall():
            records.append({
                "record_id": row[0],
                "team_id": row[1],
                "team_name": row[2],
                "schedule_date": row[3],
                "shift_type": row[4],
                "on_duty_time": row[5],
                "off_duty_time": row[6],
                "schedule_status": row[7],
                "city_dept_id": row[8],
                "temp_person_ids": row[9].split(",") if row[9] else [],
                "temp_person_names": row[10].split(",") if row[10] else [],
            })

        cursor.close()
        conn.close()
        return records

    except Exception as e:
        print(f"[OracleDB] 查询排班记录失败: {e}")
        return []


# ============================================
# 如何集成到现有代码中（替换 mock 数据）
# ============================================
"""
在 src/tools/scheduling.py 的 ScheduleDataProvider 中，
将以下方法替换：

=== get_teams() 替换 ===
原代码：
    def get_teams(city_dept_id):
        return ScheduleDataProvider._get_mock_teams_data()

替换为：
    def get_teams(city_dept_id):
        teams_data = query_teams(city_dept_id)
        if teams_data:
            # 转换为 OcScheduleTeam 对象
            from src.tools.scheduling import OcScheduleTeam
            result = []
            for t in teams_data:
                result.append(OcScheduleTeam(
                    team_id=t["team_id"],
                    team_name=t["team_name"],
                    team_leader_name=t["team_leader_name"],
                    person_id_list=t["person_ids"],
                    person_name_list=t["person_names"],
                    suggested_count=t["suggested_count"],
                    city_dept_id=t["city_dept_id"],
                    shift_type=t["shift_type"],
                ))
            return result
        # 回退到 mock 数据
        return ScheduleDataProvider._get_mock_teams_data()


=== get_records() 替换 ===
原代码：
    def get_records(start_date, end_date, city_dept_id):
        ScheduleDataProvider._ensure_record_store()
        ... # 从内存查询

替换为：
    def get_records(start_date, end_date, city_dept_id):
        records_data = query_records(start_date, end_date, city_dept_id)
        if records_data:
            from src.tools.scheduling import OcScheduleRecord
            result = []
            for r in records_data:
                result.append(OcScheduleRecord(
                    record_id=r["record_id"],
                    team_id=r["team_id"],
                    team_name=r["team_name"],
                    schedule_date=r["schedule_date"].isoformat(),
                    shift_type=r["shift_type"],
                    on_duty_time=r["on_duty_time"],
                    off_duty_time=r["off_duty_time"],
                    schedule_status=r["schedule_status"],
                    city_dept_id=r["city_dept_id"],
                    temp_person_ids=r["temp_person_ids"],
                    temp_person_names=r["temp_person_names"],
                ))
            return result
        # 回退到 mock 数据
        ScheduleDataProvider._ensure_record_store()
        return [...]  # 原逻辑
"""


if __name__ == "__main__":
    """测试连接"""
    print(f"Oracle 连接信息:")
    print(f"  Host: {ORACLE_CONFIG['host']}:{ORACLE_CONFIG['port']}")
    print(f"  Service: {ORACLE_CONFIG['service_name']}")
    print(f"  User: {ORACLE_CONFIG['user']}")
    print(f"  TNS: {TNS_CONNECT_STRING[:60]}...")
    print()

    # 测试查询
    teams = query_teams()
    print(f"查询到 {len(teams)} 个班组:")
    for t in teams:
        print(f"  {t['team_name']}: {t['team_leader_name']} ({len(t['person_names'])}人)")

    today = datetime.date.today()
    records = query_records(today, today)
    print(f"\n今日排班记录: {len(records)} 条")
    for r in records:
        print(f"  {r['team_name']}: {r['shift_type']} status={r['schedule_status']}")