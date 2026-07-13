"""
Oracle 数据库连接模块
=====================
连接 10.111.134.209:1521/omscsdb（OMSCS1 库，与 Java 系统共用），
替代当前内存模拟数据。连接失败时自动降级到 mock 数据。
"""

import os
import datetime
from typing import Optional

# ═══════════════════════════════════════
# Oracle 连接配置（从环境变量读取）
# ═══════════════════════════════════════
ORACLE_CONFIG = {
    "host": os.getenv("ORACLE_HOST", "10.111.134.209"),
    "port": int(os.getenv("ORACLE_PORT", "1521")),
    "service_name": os.getenv("ORACLE_SERVICE_NAME", "omscsdb"),
    "user": os.getenv("ORACLE_USER", "OMSCS1"),
    "password": os.getenv("ORACLE_PASSWORD", "omscs_oms123"),
}

# 简单 EZConnect 格式（与 Java 的 jdbc:oracle:thin:@host:port/service 一致）
_DB_HOST = ORACLE_CONFIG["host"]
_DB_PORT = ORACLE_CONFIG["port"]
_DB_SERVICE = ORACLE_CONFIG["service_name"]
EZCONNECT_STRING = f"{_DB_HOST}:{_DB_PORT}/{_DB_SERVICE}"

# 初始化 Oracle Client（thick 模式，支持 Oracle 11g+）
_oracle_initialized = False


def _init_oracle_client():
    """初始化 Oracle Client 厚模式（只需调用一次）"""
    global _oracle_initialized
    if _oracle_initialized:
        return
    try:
        import oracledb
        oracledb.init_oracle_client()
        _oracle_initialized = True
    except Exception as e:
        print(f"[OracleDB] Oracle Client 初始化失败: {e}")


def is_oracle_available() -> bool:
    """检查 Oracle 是否可达（每次调用都重新检测，不缓存失败结果）"""
    try:
        import oracledb
        _init_oracle_client()
        oracledb.defaults.connect_timeout = 10
        conn = oracledb.connect(
            user=ORACLE_CONFIG["user"],
            password=ORACLE_CONFIG["password"],
            dsn=EZCONNECT_STRING,
        )
        conn.close()
        return True
    except Exception as e:
        print(f"[OracleDB] 连接失败: {e}")
        return False


def get_oracle_connection():
    """获取 Oracle 数据库连接（oracledb 驱动 thick 模式，10秒超时）"""
    import oracledb
    _init_oracle_client()
    oracledb.defaults.connect_timeout = 10
    return oracledb.connect(
        user=ORACLE_CONFIG["user"],
        password=ORACLE_CONFIG["password"],
        dsn=EZCONNECT_STRING,
    )


# ═══════════════════════════════════════
# 查询班组 (OC_SCHEDULE_TEAM)
# ═══════════════════════════════════════
def query_teams() -> list[dict]:
    """
    查询 OC_SCHEDULE_TEAM 表，返回所有启用的班组。

    返回字段：
        team_id, team_name, team_leader_id, team_leader_name,
        person_ids(对应数据库 OTHER_PERSON_IDS), person_names(对应数据库 OTHER_PERSON_NAMES),
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
                NVL(OTHER_PERSON_IDS, '') AS OTHER_PERSON_IDS,
                NVL(OTHER_PERSON_NAMES, '') AS OTHER_PERSON_NAMES,
                NVL(CREATE_BUSI_DEPT_ID, '') AS CREATE_BUSI_DEPT_ID,
                NVL(CREATE_BUSI_DEPT_NAME, '') AS CREATE_BUSI_DEPT_NAME
            FROM OC_SCHEDULE_TEAM
            WHERE ENABLE_FLAG = 'Y'
        """

        sql += " ORDER BY TEAM_NAME"
        cursor.execute(sql)

        teams = []
        for row in cursor.fetchall():
            teams.append({
                "team_id": row[0],
                "team_name": row[1],
                "team_leader_id": row[2],
                "team_leader_name": row[3],
                "person_ids": row[4],
                "person_names": row[5],
                "create_busi_dept_id": row[6],
                "create_busi_dept_name": row[7],
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
                ON_DUTY_TIME,
                OFF_DUTY_TIME,
                NVL(SCHEDULE_STATUS, 'N') AS SCHEDULE_STATUS,
                NVL(TEAM_LEADER_ID, '') AS TEAM_LEADER_ID,
                NVL(TEAM_LEADER_NAME, '') AS TEAM_LEADER_NAME,
                NVL(OTHER_PERSON_IDS, '') AS OTHER_PERSON_IDS,
                NVL(OTHER_PERSON_NAMES, '') AS OTHER_PERSON_NAMES,
                NVL(TEMP_PERSON_IDS, '') AS TEMP_PERSON_IDS,
                NVL(TEMP_PERSON_NAMES, '') AS TEMP_PERSON_NAMES
            FROM OC_SCHEDULE_RECORD
            WHERE SCHEDULE_DATE >= :1
              AND SCHEDULE_DATE <= :2
        """
        params = [start_date, end_date]

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
                "on_duty_time": row[6],
                "off_duty_time": row[7],
                "schedule_status": row[8],
                "team_leader_id": row[9],
                "team_leader_name": row[10],
                "other_person_ids": row[11],
                "other_person_names": row[12],
                "temp_person_ids": row[13],
                "temp_person_names": row[14],
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