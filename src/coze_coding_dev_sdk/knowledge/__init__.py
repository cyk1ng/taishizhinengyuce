"""Knowledge module stubs for Docker deployment"""

from enum import Enum
from typing import Any, Dict, List, Optional


class DataSourceType(Enum):
    """数据源类型"""
    TEXT = "text"
    URL = "url"
    FILE = "file"


class KnowledgeDocument:
    """知识库文档"""
    def __init__(self, name: str, content: str, source_type: str = "text",
                 metadata: Optional[Dict[str, Any]] = None, 
                 chunk_size: int = 500, chunk_overlap: int = 50, **kwargs):
        self.name = name
        self.content = content
        self.source_type = source_type
        self.metadata = metadata or {}
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap


class ChunkConfig:
    """文档分块配置"""
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50, **kwargs):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap