"""coze_coding_utils 兼容替身 - error.classifier"""
from typing import Any, Dict

class ErrorClassifier:
    """错误分类器 - 替身"""
    @staticmethod
    def classify(error: Exception) -> Dict[str, Any]:
        return {"type": type(error).__name__, "message": str(error)}


def classify_error(error: Exception) -> Dict[str, Any]:
    """分类错误 - 替身"""
    return ErrorClassifier.classify(error)