"""
页面数据快照管理模块
===================
存储当前页面展示的数据快照，用户修改后也更新此快照。
AI 分析时从此表读取数据，确保分析的是用户当前看到的页面数据。

表结构：DISPATCH_PAGE_SNAPSHOT
  snapshot_date  DATE PRIMARY KEY     -- 日期
  page_data      CLOB                 -- 完整页面数据 JSON
  data_hash      VARCHAR2(64)         -- 数据哈希
  created_at     TIMESTAMP            -- 创建时间
  updated_at     TIMESTAMP            -- 更新时间
"""

import os
import json
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


def save_snapshot(snapshot_data: dict, target_date: str = None) -> bool:
    """
    保存页面数据快照。
    如果当天已有快照则覆盖更新。
    """
    if target_date is None:
        target_date = datetime.datetime.now().strftime("%Y-%m-%d")

    data_json = json.dumps(snapshot_data, ensure_ascii=False, default=str)
    data_hash = hashlib.md5(data_json.encode()).hexdigest()

    if _check_oracle():
        try:
            conn = _get_conn()
            cur = conn.cursor()
            cur.execute(
                """MERGE INTO DISPATCH_PAGE_SNAPSHOT t
                   USING (SELECT TO_DATE(:1,'YYYY-MM-DD') AS dt FROM DUAL) s
                   ON (t.snapshot_date = s.dt)
                   WHEN MATCHED THEN UPDATE SET
                       page_data = :2,
                       data_hash = :3,
                       updated_at = SYSTIMESTAMP
                   WHEN NOT MATCHED THEN INSERT
                       (snapshot_date, page_data, data_hash, created_at, updated_at)
                       VALUES (TO_DATE(:1,'YYYY-MM-DD'), :2, :3, SYSTIMESTAMP, SYSTIMESTAMP)""",
                [target_date, data_json, data_hash]
            )
            conn.commit()
            cur.close()
            conn.close()
            logger.info(f"[Snapshot] 已保存 {target_date} 快照 (hash={data_hash[:8]}...)")
            return True
        except Exception as e:
            logger.warning(f"[Snapshot] Oracle 保存快照失败: {e}，降级到内存")
            _memory_snapshot[target_date] = {"data": snapshot_data, "hash": data_hash}
            return True
    else:
        _memory_snapshot[target_date] = {"data": snapshot_data, "hash": data_hash}
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
                "SELECT page_data, data_hash FROM DISPATCH_PAGE_SNAPSHOT WHERE snapshot_date = TO_DATE(:1,'YYYY-MM-DD')",
                [target_date]
            )
            row = cur.fetchone()
            cur.close()
            conn.close()
            if row:
                data = json.loads(row[0])
                logger.info(f"[Snapshot] 已读取 {target_date} 快照 (hash={row[1][:8] if row[1] else 'N/A'}...)")
                return data
            return None
        except Exception as e:
            logger.warning(f"[Snapshot] Oracle 读取快照失败: {e}，尝试内存")
            return _memory_snapshot.get(target_date, {}).get("data")
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
                "SELECT data_hash FROM DISPATCH_PAGE_SNAPSHOT WHERE snapshot_date = TO_DATE(:1,'YYYY-MM-DD')",
                [target_date]
            )
            row = cur.fetchone()
            cur.close()
            conn.close()
            return row[0] if row else None
        except Exception:
            return None
    return None