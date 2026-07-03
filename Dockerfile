FROM python:3.12-slim

LABEL description="配网调度业务量智能预测系统"
LABEL version="2.0"

WORKDIR /app

# 安装 Python 依赖（只装实际使用的包，避免 torch/prophet 等重型未使用包）
COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
        fastapi uvicorn[standard] \
        langchain langchain-openai langgraph \
        sqlalchemy pymysql oracledb \
        pandas numpy \
        python-multipart python-dotenv \
        requests \
        jinja2 python-pptx pillow opencv-python-headless \
        cozeloop \
    && rm -rf /root/.cache/pip

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

CMD ["python", "src/main.py"]