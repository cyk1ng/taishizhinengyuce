"""coze_coding_utils 兼容替身 - error.classifier"""
from typing import Any, Dict, Optional


class ClassifiedError:
    """分类后的错误对象"""
    def __init__(self, code: str = "UNKNOWN", message: str = "", category: Any = None):
        self.code = code
        self.message = message
        self.category = category or type("Category", (), {"name": "UNKNOWN"})()


class ErrorClassifier:
    """错误分类器 - 替身"""
    def classify(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> ClassifiedError:
        return ClassifiedError(
            code="STUB_ERROR",
            message=str(error),
            category=type("Category", (), {"name": "STUB"})()
        )


def classify_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> ClassifiedError:
    """分类错误 - 替身"""
    return ErrorClassifier().classify(error, context)