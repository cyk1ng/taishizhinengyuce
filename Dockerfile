FROM python:3.12-slim

LABEL description="配网调度业务量智能预测系统"
LABEL version="2.0"

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
        libaio1 \
        git \
        && rm -rf /var/lib/apt/lists/*

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 复制依赖文件
COPY pyproject.toml uv.lock ./

# 安装 Python 依赖（使用 uv sync，精确匹配 pyproject.toml）
RUN uv sync --frozen --no-dev --no-cache

# 复制项目代码
COPY src/ ./src/
COPY frontend/ ./frontend/
COPY config/ ./config/
COPY assets/ ./assets/

# 设置环境变量
ENV PYTHONPATH=/app/src
ENV COZE_WORKSPACE_PATH=/app

# 暴露端口
EXPOSE 5000

# 使用 uv 运行
CMD ["uv", "run", "python", "src/main.py"]