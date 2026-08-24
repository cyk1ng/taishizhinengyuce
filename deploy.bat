@echo off
chcp 65001 >nul
REM =============================================
REM 配网调度业务量智能预测系统 - Windows 部署脚本
REM =============================================
REM 使用方法：
REM   双击运行 或 在 PowerShell 中执行：.\deploy.bat [选项]
REM
REM 选项：
REM   build     - 仅构建镜像
REM   start     - 启动服务
REM   stop      - 停止服务
REM   restart   - 重启服务
REM   logs      - 查看日志
REM   test      - 测试模式启动
REM   full      - 完整部署（构建 + 启动）
REM =============================================

setlocal enabledelayedexpansion

REM 检查参数
set ACTION=%1
if "%ACTION%"=="" set ACTION=full

echo.
echo ============================================
echo   配网调度业务量智能预测系统 - 部署工具
echo ============================================
echo.

REM 检查 Docker
where docker >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Docker 未安装，请先安装 Docker Desktop
    echo 下载地址：https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)
echo [OK] Docker 已安装

REM 检查 Oracle Instant Client
if exist "instantclient-basic-linux.x64-23.26.3.0.0.zip" (
    echo [OK] Oracle Instant Client 23.26 已就绪
) else if exist "instantclient-basiclite-linux.x64-19.21.0.0.0dbru.zip" (
    echo [OK] Oracle Instant Client 19.21 已就绪
) else (
    echo [WARNING] Oracle Instant Client 文件未找到
    echo 请下载并放到项目根目录：
    echo https://www.oracle.com/database/technologies/instant-client/linux-x86-64-downloads.html
)

REM 检查 .env 文件
if not exist ".env" (
    echo [WARNING] .env 文件不存在，从 .env.example 复制...
    copy .env.example .env
    echo [WARNING] 请编辑 .env 文件配置你的环境
) else (
    echo [OK] .env 文件已存在
)

REM 检查模型配置
if exist "config\agent_llm_config.json" (
    for /f "tokens=2 delims=:" %%a in ('findstr /c:"\"model\"" config\agent_llm_config.json') do (
        set MODEL=%%a
    )
    echo [INFO] 当前模型配置：%MODEL%
)

echo.
echo ============================================
echo   执行操作：%ACTION%
echo ============================================
echo.

if "%ACTION%"=="build" (
    goto :build
) else if "%ACTION%"=="start" (
    goto :start
) else if "%ACTION%"=="stop" (
    goto :stop
) else if "%ACTION%"=="restart" (
    goto :restart
) else if "%ACTION%"=="logs" (
    goto :logs
) else if "%ACTION%"=="test" (
    goto :test
) else if "%ACTION%"=="full" (
    goto :full
) else if "%ACTION%"=="help" (
    goto :help
) else (
    echo [ERROR] 未知选项：%ACTION%
    goto :help
)

:build
echo [INFO] 构建 Docker 镜像...
docker compose build dispatch-app
if errorlevel 1 (
    echo [ERROR] 镜像构建失败
    pause
    exit /b 1
)
echo [SUCCESS] 镜像构建完成
goto :end

:start
echo [INFO] 启动服务...
docker compose up -d dispatch-app
if errorlevel 1 (
    echo [ERROR] 服务启动失败
    pause
    exit /b 1
)
echo [SUCCESS] 服务已启动
echo [INFO] 访问地址：http://localhost:5000
goto :healthcheck

:test
echo [INFO] 启动测试模式（假数据）...
docker compose up -d dispatch-app-test
if errorlevel 1 (
    echo [ERROR] 服务启动失败
    pause
    exit /b 1
)
echo [SUCCESS] 测试服务已启动
echo [INFO] 访问地址：http://localhost:5001
goto :healthcheck

:stop
echo [INFO] 停止服务...
docker compose down
echo [SUCCESS] 服务已停止
goto :end

:restart
echo [INFO] 重启服务...
docker compose restart dispatch-app
echo [SUCCESS] 服务已重启
goto :healthcheck

:logs
echo [INFO] 查看日志（Ctrl+C 退出）...
docker compose logs -f dispatch-app
goto :end

:full
echo [INFO] 完整部署流程...
echo.

echo [步骤 1/3] 构建镜像...
docker compose build dispatch-app
if errorlevel 1 (
    echo [ERROR] 镜像构建失败
    pause
    exit /b 1
)
echo [SUCCESS] 镜像构建完成
echo.

echo [步骤 2/3] 启动服务...
docker compose up -d dispatch-app
if errorlevel 1 (
    echo [ERROR] 服务启动失败
    pause
    exit /b 1
)
echo [SUCCESS] 服务已启动
echo.

goto :healthcheck

:healthcheck
echo [步骤 3/3] 健康检查...
timeout /t 5 /nobreak >nul

docker ps | findstr "dispatch-app" >nul
if errorlevel 1 (
    echo [ERROR] 容器未运行
    pause
    exit /b 1
)
echo [SUCCESS] 容器运行正常

echo.
echo ============================================
echo   部署完成！
echo ============================================
echo   访问地址：http://localhost:5000
echo   查看日志：docker compose logs -f dispatch-app
echo   停止服务：docker compose down
echo ============================================
echo.
goto :end

:help
echo 使用方法：deploy.bat [选项]
echo.
echo 选项：
echo   build     - 仅构建镜像
echo   start     - 启动服务（生产模式）
echo   stop      - 停止服务
echo   restart   - 重启服务
echo   logs      - 查看日志
echo   test      - 测试模式启动（假数据）
echo   full      - 完整部署（构建 + 启动 + 健康检查）
echo   help      - 显示此帮助
echo.
echo 示例：
echo   deploy.bat full      # 完整部署
echo   deploy.bat test      # 测试模式
echo   deploy.bat logs      # 查看日志
goto :end

:end
echo.
pause
