FROM python:3.12-slim-bookworm

LABEL description="配网调度业务量智能预测系统"
LABEL version="2.0"

WORKDIR /app

# 安装系统依赖（libaio1 是 Oracle Instant Client 需要的）
RUN apt-get update && apt-get install -y --no-install-recommends \
        libaio1 \
        unzip \
    && rm -rf /var/lib/apt/lists/*

# 复制本地下载的 Oracle Instant Client 19.21（支持 Oracle 11g+）
COPY instantclient-basiclite-linux.x64-19.21.0.0.0dbru.zip /tmp/instantclient.zip
RUN unzip -q /tmp/instantclient.zip -d /opt/oracle \
    && rm /tmp/instantclient.zip \
    && echo /opt/oracle/instantclient_19_21 > /etc/ld.so.conf.d/oracle-instantclient.conf \
    && ldconfig

ENV LD_LIBRARY_PATH=/opt/oracle/instantclient_19_21

# 安装 Python 依赖（只装实际使用的包，移除未使用的重型包）
COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
        fastapi uvicorn[standard] \
        langchain langchain-openai langgraph \
        sqlalchemy pymysql oracledb \
        pandas numpy \
        python-multipart python-dotenv \
        requests \
        jinja2 python-pptx pillow \
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