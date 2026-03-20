import os
import time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
import logging
logger = logging.getLogger(__name__)

MAX_RETRY_TIME = 20  # 连接最大重试时间（秒）

# Load environment variables from .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

def get_db_url() -> str:
    """Build database URL from environment.
    
    支持的数据库类型：
    - MySQL: DB_TYPE=mysql
    - Oracle: DB_TYPE=oracle
    - PostgreSQL: DB_TYPE=postgres 或 PGDATABASE_URL
    
    环境变量配置：
    MySQL:
        DB_TYPE=mysql
        DB_HOST=localhost
        DB_PORT=3306
        DB_NAME=dispatch_db
        DB_USER=root
        DB_PASSWORD=your_password
    
    Oracle:
        DB_TYPE=oracle
        DB_HOST=localhost
        DB_PORT=1521
        DB_NAME=ORCL
        DB_USER=system
        DB_PASSWORD=your_password
    """
    # 优先使用完整 URL
    url = os.getenv("DATABASE_URL") or os.getenv("PGDATABASE_URL") or ""
    if url:
        return url
    
    # 从单独的环境变量构建 URL
    db_type = os.getenv("DB_TYPE", "").lower()
    
    if db_type == "mysql":
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "3306")
        name = os.getenv("DB_NAME", "dispatch_db")
        user = os.getenv("DB_USER", "root")
        password = os.getenv("DB_PASSWORD", "")
        # MySQL URL 格式: mysql+pymysql://user:password@host:port/dbname
        url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}?charset=utf8mb4"
        return url
    
    elif db_type == "oracle":
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "1521")
        name = os.getenv("DB_NAME", "ORCL")
        user = os.getenv("DB_USER", "system")
        password = os.getenv("DB_PASSWORD", "")
        # Oracle URL 格式: oracle+cx_oracle://user:password@host:port/?service_name=name
        url = f"oracle+cx_oracle://{user}:{password}@{host}:{port}/?service_name={name}"
        return url
    
    # 默认 PostgreSQL
    elif db_type == "postgres" or db_type == "postgresql":
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "5432")
        name = os.getenv("DB_NAME", "dispatch_db")
        user = os.getenv("DB_USER", "postgres")
        password = os.getenv("DB_PASSWORD", "")
        url = f"postgresql://{user}:{password}@{host}:{port}/{name}"
        return url
    
    # 尝试从 Coze 环境获取
    try:
        from coze_workload_identity import Client
        client = Client()
        env_vars = client.get_project_env_vars()
        client.close()
        for env_var in env_vars:
            if env_var.key == "PGDATABASE_URL" or env_var.key == "DATABASE_URL":
                url = env_var.value.replace("'", "'\\''")
                return url
    except Exception as e:
        logger.debug(f"Could not load from Coze environment: {e}")
    
    # 如果都没有配置，返回空（使用模拟数据）
    logger.warning("No database URL configured, will use mock data")
    return ""

_engine = None
_SessionLocal = None

def _create_engine_with_retry():
    url = get_db_url()
    if not url:
        logger.warning("Database URL is not set, using mock data mode")
        return None
    
    size = 100
    overflow = 100
    recycle = 1800
    timeout = 30
    
    engine = create_engine(
        url,
        pool_size=size,
        max_overflow=overflow,
        pool_pre_ping=True,
        pool_recycle=recycle,
        pool_timeout=timeout,
        echo=False,  # 生产环境关闭 SQL 日志
    )
    
    # 验证连接，带重试
    start_time = time.time()
    last_error = None
    while time.time() - start_time < MAX_RETRY_TIME:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database connection established successfully")
            return engine
        except OperationalError as e:
            last_error = e
            elapsed = time.time() - start_time
            logger.warning(f"Database connection failed, retrying... (elapsed: {elapsed:.1f}s)")
            time.sleep(min(1, MAX_RETRY_TIME - elapsed))
    
    logger.error(f"Database connection failed after {MAX_RETRY_TIME}s: {last_error}")
    raise last_error  # pyright: ignore [reportGeneralTypeIssues]

def get_engine():
    global _engine
    if _engine is None:
        _engine = _create_engine_with_retry()
    return _engine

def get_sessionmaker():
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine()
        if engine:
            _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        else:
            _SessionLocal = None
    return _SessionLocal

def get_session():
    sessionmaker_obj = get_sessionmaker()
    if sessionmaker_obj:
        return sessionmaker_obj()
    return None

def is_database_connected() -> bool:
    """检查数据库是否已连接"""
    return get_engine() is not None

__all__ = [
    "get_db_url",
    "get_engine",
    "get_sessionmaker",
    "get_session",
    "is_database_connected",
]
