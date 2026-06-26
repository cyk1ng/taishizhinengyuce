"""
Oracle 数据库连接模块
=====================
连接 10.111.134.211:1521/domsdb（DOMS_JADP 库），
替代当前内存模拟数据。连接失败时自动降级到 mock 数据。
"""

import os
import datetime
from typing import Optional

# ═══════════════════════════════════════
# Oracle 连接配置（从环境变量读取）
# ═══════════════════════════════════════
ORACLE_CONFIG = {
    "host": os.getenv("ORACLE_HOST", "10.111.134.211"),
    "port": int(os.getenv("ORACLE_PORT", "1521")),
    "service_name": os.getenv("ORACLE_SERVICE_NAME", "domsdb"),
    "user": os.getenv("ORACLE_USER", "DOMS_JADP"),
    "password": os.getenv("ORACLE_PASSWORD", "doms_jadp"),
}

# TNS 连接串（含负载均衡 + 故障转移）
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
    """获取 Oracle 数据库连接（oracledb 驱动）"""
    import oracledb
    try:
        oracledb.init_oracle_client()
    except Exception:
        pass  # 没装 Instant Client 也能用 thin 模式

    return oracledb.connect(
        user=ORACLE_CONFIG["user"],
        password=ORACLE_CONFIG["password"],
        dsn=TNS_CONNECT_STRING,
    )


# ═══════════════════════════════════════
# 查询班组 (OC_SCHEDULE_TEAM)
# ═══════════════════════════════════════
def query_teams(city_dept_id: str = "") -> list[dict]:
    """
    查询 OC_SCHEDULE_TEAM 表，返回所有启用的班组。

    返回字段：
        team_id, team_name, team_leader_id, team_leader_name,
        person_ids, person_names, suggested_count, city_dept_id, shift_type,
        create_busi_dept_id, create_busi_dept_name
    """
    try:
        conn = get_oracle_connection()
        cursor = conn.cursor()

        sql = """
            SELECT
                TEAM_ID,
                TEAM_NAME,
                NVL(TEAM_LEADER_ID, '') AS TEAM_LEADER_ID,
                NVL(TEAM_LEADER_NAME, '') AS TEAM_LEADER_NAME,
                NVL(PERSON_IDS, '') AS PERSON_IDS,
                NVL(PERSON_NAMES, '') AS PERSON_NAMES,
                NVL(SUGGESTED_COUNT, 0) AS SUGGESTED_COUNT,
                NVL(CITY_DEPT_ID, '') AS CITY_DEPT_ID,
                NVL(SHIFT_TYPE, '') AS SHIFT_TYPE,
                NVL(CREATE_BUSI_DEPT_ID, '') AS CREATE_BUSI_DEPT_ID,
                NVL(CREATE_BUSI_DEPT_NAME, '') AS CREATE_BUSI_DEPT_NAME
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
                "team_leader_id": row[2],
                "team_leader_name": row[3],
                "person_ids": row[4],
                "person_names": row[5],
                "suggested_count": int(row[6]) if row[6] else 0,
                "city_dept_id": row[7],
                "shift_type": row[8],
                "create_busi_dept_id": row[9],
                "create_busi_dept_name": row[10],
            })

        cursor.close()
        conn.close()
        return teams

    except Exception as e:
        print(f"[OracleDB] 查询班组失败: {e}")
        return []


# ═══════════════════════════════════════
# 查询排班记录 (OC_SCHEDULE_RECORD)
# ═══════════════════════════════════════
def query_records(
    start_date: datetime.date,
    end_date: datetime.date,
    city_dept_id: str = ""
) -> list[dict]:
    """
    查询 OC_SCHEDULE_RECORD 表，获取指定日期范围的排班记录。
    """
    try:
        conn = get_oracle_connection()
        cursor = conn.cursor()

        sql = """
            SELECT
                RECORD_ID,
                NVL(DIS_ORG_ID, '') AS DIS_ORG_ID,
                NVL(DIS_ORG_NAME, '') AS DIS_ORG_NAME,
                NVL(TEAM_ID, '') AS TEAM_ID,
                NVL(TEAM_NAME, '') AS TEAM_NAME,
                SCHEDULE_DATE,
                NVL(SHIFT_TYPE, '') AS SHIFT_TYPE,
                ON_DUTY_TIME,
                OFF_DUTY_TIME,
                NVL(SCHEDULE_STATUS, 'N') AS SCHEDULE_STATUS,
                NVL(TEAM_LEADER_ID, '') AS TEAM_LEADER_ID,
                NVL(TEAM_LEADER_NAME, '') AS TEAM_LEADER_NAME,
                NVL(OTHER_PERSON_IDS, '') AS OTHER_PERSON_IDS,
                NVL(OTHER_PERSON_NAMES, '') AS OTHER_PERSON_NAMES,
                NVL(CITY_DEPT_ID, '') AS CITY_DEPT_ID,
                NVL(TEMP_PERSON_IDS, '') AS TEMP_PERSON_IDS,
                NVL(TEMP_PERSON_NAMES, '') AS TEMP_PERSON_NAMES
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
                "dis_org_id": row[1],
                "dis_org_name": row[2],
                "team_id": row[3],
                "team_name": row[4],
                "schedule_date": row[5],
                "shift_type": row[6],
                "on_duty_time": row[7],
                "off_duty_time": row[8],
                "schedule_status": row[9],
                "team_leader_id": row[10],
                "team_leader_name": row[11],
                "other_person_ids": row[12],
                "other_person_names": row[13],
                "city_dept_id": row[14],
                "temp_person_ids": row[15],
                "temp_person_names": row[16],
            })

        cursor.close()
        conn.close()
        return records

    except Exception as e:
        print(f"[OracleDB] 查询排班记录失败: {e}")
        return []


if __name__ == "__main__":
    print(f"Oracle: {ORACLE_CONFIG['user']}@{ORACLE_CONFIG['host']}:{ORACLE_CONFIG['port']}/{ORACLE_CONFIG['service_name']}")
    teams = query_teams()
    print(f"班组 {len(teams)} 个:")
    for t in teams:
        names = t["person_names"].split(",") if t["person_names"] else []
        print(f"  {t['team_name']}: {t['team_leader_name']} ({len(names)}人)")
    today = datetime.date.today()
    records = query_records(today, today)
    print(f"\n今日记录 {len(records)} 条")