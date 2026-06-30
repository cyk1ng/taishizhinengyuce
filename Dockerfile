FROM python:3.12-slim

LABEL description="配网调度业务量智能预测系统"
LABEL version="1.0"

WORKDIR /app

# 复制依赖文件并安装 Python 包
COPY pyproject.toml requirements.txt* ./
RUN pip install --no-cache-dir \
        fastapi uvicorn[standard] sqlalchemy oracledb \
        langchain langchain-openai langgraph \
        jinja2 python-multipart python-dotenv \
        pandas numpy 2>/dev/null \
    || pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY src/ ./src/
COPY frontend/ ./frontend/
COPY config/ ./config/
COPY assets/ ./assets/
COPY .env ./.env

# 暴露端口
EXPOSE 5000

CMD ["python", "src/main.py"]