"""
页面数据快照管理模块
===================
存储当前页面展示的数据快照，用户修改后也更新此快照。
AI 分析时从此表读取数据，确保分析的是用户当前看到的页面数据。

表结构：DISPATCH_PAGE_SNAPSHOT
  MK_ID            VARCHAR2(64) PRIMARY KEY  -- 主键
  DIS_ORG_ID       VARCHAR2(64)              -- 调度机构ID
  DIS_ORG_NAME     VARCHAR2(256)             -- 调度机构名称
  COUNTY_DEPT_ID   VARCHAR2(64)              -- 县配网部门ID
  COUNTY_DEPT_NAME VARCHAR2(256)             -- 县配网部门名称
  SNAPSHOT_DATE    DATE                      -- 快照日期
  PAGE_DATA        CLOB                      -- 完整页面数据 JSON
  DATA_HASH        VARCHAR2(64)              -- 数据哈希
  CREATED_AT       TIMESTAMP                 -- 创建时间
  UPDATED_AT       TIMESTAMP                 -- 更新时间
"""

import os
import json
import uuid
import hashlib
import datetime
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 内存降级存储（Oracle 不可用时使用）
_memory_snapshot: dict[str, dict] = {}


def _check_oracle() -> bool:
    """检查 Oracle 是否可达"""
    try:
        from oracle_db import is_oracle_available as _check
        return _check()
    except Exception:
        return False


def _get_conn():
    """获取 Oracle 连接"""
    from oracle_db import get_oracle_connection
    return get_oracle_connection()


def save_snapshot(
    snapshot_data: dict,
    target_date: str = None,
    dis_org_id: str = "",
    dis_org_name: str = "",
    county_dept_id: str = "",
    county_dept_name: str = "",
    mk_id: str = None
) -> bool:
    """
    保存页面数据快照。
    如果当天已有快照则覆盖更新。
    """
    if target_date is None:
        target_date = datetime.datetime.now().strftime("%Y-%m-%d")

    # 生成 MK_ID
    if mk_id is None:
        mk_id = f"SNP_{target_date}_{uuid.uuid4().hex[:8]}"

    data_json = json.dumps(snapshot_data, ensure_ascii=False, default=str)
    data_hash = hashlib.md5(data_json.encode()).hexdigest()

    if _check_oracle():
        try:
            conn = _get_conn()
            cur = conn.cursor()
            cur.execute(
                """MERGE INTO DISPATCH_PAGE_SNAPSHOT t
                   USING (SELECT :1 AS mk_id FROM DUAL) s
                   ON (t.MK_ID = s.mk_id)
                   WHEN MATCHED THEN UPDATE SET
                       DIS_ORG_ID = :2,
                       DIS_ORG_NAME = :3,
                       COUNTY_DEPT_ID = :4,
                       COUNTY_DEPT_NAME = :5,
                       SNAPSHOT_DATE = TO_DATE(:6,'YYYY-MM-DD'),
                       PAGE_DATA = :7,
                       DATA_HASH = :8,
                       UPDATED_AT = SYSTIMESTAMP
                   WHEN NOT MATCHED THEN INSERT
                       (MK_ID, DIS_ORG_ID, DIS_ORG_NAME, COUNTY_DEPT_ID, COUNTY_DEPT_NAME,
                        SNAPSHOT_DATE, PAGE_DATA, DATA_HASH, CREATED_AT, UPDATED_AT)
                       VALUES (:1, :2, :3, :4, :5, TO_DATE(:6,'YYYY-MM-DD'), :7, :8, SYSTIMESTAMP, SYSTIMESTAMP)""",
                [mk_id, dis_org_id, dis_org_name, county_dept_id, county_dept_name,
                 target_date, data_json, data_hash]
            )
            conn.commit()
            cur.close()
            conn.close()
            logger.info(f"[Snapshot] 已保存 {target_date} 快照 (mk_id={mk_id}, hash={data_hash[:8]}...)")
            return True
        except Exception as e:
            logger.warning(f"[Snapshot] Oracle 保存快照失败: {e}，降级到内存")
            _memory_snapshot[target_date] = {"data": snapshot_data, "hash": data_hash, "mk_id": mk_id}
            return True
    else:
        _memory_snapshot[target_date] = {"data": snapshot_data, "hash": data_hash, "mk_id": mk_id}
        logger.info(f"[Snapshot] 已保存 {target_date} 快照到内存")
        return True


def get_snapshot(target_date: str = None) -> Optional[dict]:
    """
    获取指定日期的页面数据快照。
    返回完整数据字典，没有快照时返回 None。
    """
    if target_date is None:
        target_date = datetime.datetime.now().strftime("%Y-%m-%d")

    if _check_oracle():
        try:
            conn = _get_conn()
            cur = conn.cursor()
            cur.execute(
                """SELECT PAGE_DATA, DATA_HASH, MK_ID, DIS_ORG_ID, DIS_ORG_NAME,
                          COUNTY_DEPT_ID, COUNTY_DEPT_NAME
                   FROM DISPATCH_PAGE_SNAPSHOT
                   WHERE SNAPSHOT_DATE = TO_DATE(:1,'YYYY-MM-DD')
                   ORDER BY UPDATED_AT DESC""",
                [target_date]
            )
            row = cur.fetchone()
            cur.close()
            conn.close()
            if row:
                data = json.loads(row[0])
                logger.info(f"[Snapshot] 已读取 {target_date} 快照 (mk_id={row[2]}, hash={row[1][:8] if row[1] else 'N/A'}...)")
                # 附加元数据
                data["_snapshot_meta"] = {
                    "mk_id": row[2],
                    "dis_org_id": row[3],
                    "dis_org_name": row[4],
                    "county_dept_id": row[5],
                    "county_dept_name": row[6]
                }
                return data
            return None
        except Exception as e:
            logger.warning(f"[Snapshot] Oracle 读取快照失败: {e}，尝试内存")
            mem = _memory_snapshot.get(target_date, {})
            return mem.get("data")
    else:
        return _memory_snapshot.get(target_date, {}).get("data")


def has_snapshot(target_date: str = None) -> bool:
    """检查是否有当天的快照"""
    return get_snapshot(target_date) is not None


def get_snapshot_hash(target_date: str = None) -> Optional[str]:
    """获取快照的哈希值"""
    if target_date is None:
        target_date = datetime.datetime.now().strftime("%Y-%m-%d")

    if target_date in _memory_snapshot:
        return _memory_snapshot[target_date].get("hash")

    if _check_oracle():
        try:
            conn = _get_conn()
            cur = conn.cursor()
            cur.execute(
                "SELECT DATA_HASH FROM DISPATCH_PAGE_SNAPSHOT WHERE SNAPSHOT_DATE = TO_DATE(:1,'YYYY-MM-DD') AND ROWNUM = 1",
                [target_date]
            )
            row = cur.fetchone()
            cur.close()
            conn.close()
            return row[0] if row else None
        except Exception:
            return None
    return None