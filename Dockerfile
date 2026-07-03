FROM python:3.12-slim

LABEL description="配网调度业务量智能预测系统"
LABEL version="2.0"

WORKDIR /app

# 安装系统依赖（oracledb 需要 libaio）
RUN apt-get update && apt-get install -y --no-install-recommends \
        libaio1 \
        && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装 Python 包
COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
        fastapi uvicorn[standard] \
        langchain langchain-openai langgraph \
        sqlalchemy oracledb \
        pandas numpy \
        python-multipart python-dotenv \
        requests \
        jinja2 \
        python-pptx \
        pillow \
        opencv-python-headless \
        pymysql \
    && rm -rf /root/.cache/pip

# 复制项目代码
COPY src/ ./src/
COPY frontend/ ./frontend/
COPY config/ ./config/
COPY assets/ ./assets/
COPY .env ./.env

# 设置环境变量
ENV PYTHONPATH=/app/src
ENV COZE_WORKSPACE_PATH=/app

# 暴露端口
EXPOSE 5000

CMD ["python", "src/main.py"]