"""
工作量数据覆盖存储模块
=====================
用户在前端弹窗手动修改 开展中/已终结 的数字后，
存入 OC_WORKLOAD_OVERRIDE 表（Oracle），
沙箱环境降级到内存字典。

Oracle 连接状态缓存：首次连接失败后，当前会话不再重复尝试 Oracle。
"""

import os
import json
import datetime
from typing import Optional

# 内存存储（沙箱降级用）
_in_memory_store: dict[str, dict] = {}

# Oracle 可用性缓存：第一次连不上就整会话跳过
_oracle_available: Optional[bool] = None
_oracle_initialized: bool = False


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
        print(f"[WorkloadOverride] Oracle Client 初始化失败: {e}")

# 唯一键： workload_type + category + field_name + target_date
def _make_key(wl_type: str, category: str, field: str, target_date: str) -> str:
    return f"{wl_type}:{category}:{field}:{target_date}"


def _check_oracle() -> bool:
    """检查 Oracle 是否可达，结果缓存到 _oracle_available"""
    global _oracle_available
    if _oracle_available is False:
        return False  # 之前已失败，不再尝试
    if _oracle_available is True:
        return True   # 之前已成功

    try:
        # 短超时快速检查
        import oracledb
        _init_oracle_client()
        host = os.getenv("ORACLE_HOST", "10.111.134.209")
        port = int(os.getenv("ORACLE_PORT", "1521"))
        service_name = os.getenv("ORACLE_SERVICE_NAME", "omscsdb")
        user = os.getenv("ORACLE_USER", "OMSCS1")
        password = os.getenv("ORACLE_PASSWORD", "omscs_oms123")

        conn = oracledb.connect(
            user=user,
            password=password,
            host=host,
            port=port,
            service_name=service_name,
            expire_time=5,
        )
        conn.close()
        _oracle_available = True
        return True
    except Exception as e:
        _oracle_available = False
        print(f"[WorkloadOverride] Oracle 不可达: {e}")
        return False


def _get_oracle_cursor():
    """获取 Oracle 连接的 cursor，失败返回 None"""
    from oracle_db import get_oracle_connection
    conn = get_oracle_connection()
    return conn.cursor(), conn


def save_override(
    workload_type: str,
    category: str,
    field_name: str,
    field_value: int,
    target_date: str,
) -> bool:
    """保存一条覆盖数据到 Oracle（降级到内存）"""
    # 只有 Oracle 可用时才尝试
    if _check_oracle():
        try:
            cursor, conn = _get_oracle_cursor()
            import uuid
            override_id = str(uuid.uuid4()).replace("-", "")[:32]

            cursor.execute("""
                MERGE INTO OC_WORKLOAD_OVERRIDE t
                USING (SELECT :1 AS wl_type, :2 AS cat, :3 AS fld, :4 AS dt FROM DUAL) s
                ON (t.WORKLOAD_TYPE = s.wl_type AND t.CATEGORY = s.cat
                    AND t.FIELD_NAME = s.fld AND t.TARGET_DATE = s.dt)
                WHEN MATCHED THEN
                    UPDATE SET FIELD_VALUE = :5, UPDATED_AT = SYSTIMESTAMP
                WHEN NOT MATCHED THEN
                    INSERT (OVERRIDE_ID, WORKLOAD_TYPE, CATEGORY, FIELD_NAME,
                            FIELD_VALUE, TARGET_DATE, CREATED_AT, UPDATED_AT)
                    VALUES (:6, :1, :2, :3, :5, :4, SYSTIMESTAMP, SYSTIMESTAMP)
            """, [
                workload_type, category, field_name, target_date,
                field_value, override_id
            ])
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            print(f"[WorkloadOverride] Oracle 写入失败，降级到内存: {e}")

    # 降级：内存
    key = _make_key(workload_type, category, field_name, target_date)
    _in_memory_store[key] = {
        "workload_type": workload_type,
        "category": category,
        "field_name": field_name,
        "field_value": field_value,
        "target_date": target_date,
    }
    return True


def save_batch_overrides(
    workload_type: str,
    data: dict,
    target_date: str,
) -> bool:
    """
    批量保存覆盖数据。
    data 结构：
        { category: { field_name: value, ... }, ... }
    示例：
        { "maintenance": {"in_progress": 10, "completed": 5}, ... }
    """
    success = True
    for category, fields in data.items():
        for field_name, field_value in fields.items():
            if not save_override(workload_type, category, field_name,
                                 int(field_value), target_date):
                success = False
    return success


def load_overrides(
    workload_type: str,
    target_date: str,
) -> dict[str, dict[str, int]]:
    """
    读取指定类型和日期的所有覆盖数据。
    返回：{ category: { field_name: value, ... }, ... }
    """
    result: dict[str, dict[str, int]] = {}

    # 只有 Oracle 可用时才尝试
    if _check_oracle():
        try:
            cursor, conn = _get_oracle_cursor()
            cursor.execute("""
                SELECT CATEGORY, FIELD_NAME, FIELD_VALUE
                FROM OC_WORKLOAD_OVERRIDE
                WHERE WORKLOAD_TYPE = :1 AND TARGET_DATE = :2
            """, [workload_type, target_date])

            for row in cursor.fetchall():
                cat = row[0]
                field = row[1]
                val = int(row[2]) if row[2] else 0
                if cat not in result:
                    result[cat] = {}
                result[cat][field] = val

            cursor.close()
            conn.close()
            if result:
                return result
        except Exception as e:
            print(f"[WorkloadOverride] Oracle 读取失败，降级到内存: {e}")

    # 降级：内存
    prefix = f"{workload_type}:"
    suffix = f":{target_date}"
    for key, val in _in_memory_store.items():
        if key.startswith(prefix) and key.endswith(suffix):
            parts = key.split(":")
            cat = parts[1]
            field = parts[2]
            if cat not in result:
                result[cat] = {}
            result[cat][field] = val["field_value"]

    return result


def apply_overrides_to_details(
    details: dict,
    overrides: dict[str, dict[str, int]],
) -> dict:
    """
    将覆盖数据合并到详情数据中。
    overrides = { category: { field: value } }
    """
    result = {}
    for cat, cat_data in details.items():
        merged = dict(cat_data)
        if cat in overrides:
            for field, val in overrides[cat].items():
                merged[field] = val
            # 重新计算 total
            if "in_progress" in merged and "completed" in merged:
                merged["total"] = merged["in_progress"] + merged["completed"]
                merged["count"] = merged["total"]
        result[cat] = merged
    return result


def clear_overrides(workload_type: str, target_date: str) -> bool:
    """清除某类型某日的所有覆盖记录"""
    if _check_oracle():
        try:
            cursor, conn = _get_oracle_cursor()
            cursor.execute("""
                DELETE FROM OC_WORKLOAD_OVERRIDE
                WHERE WORKLOAD_TYPE = :1 AND TARGET_DATE = :2
            """, [workload_type, target_date])
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception:
            pass

    # 内存降级
    prefix = f"{workload_type}:"
    suffix = f":{target_date}"
    keys_to_del = [k for k in _in_memory_store if k.startswith(prefix) and k.endswith(suffix)]
    for k in keys_to_del:
        del _in_memory_store[k]
    return True