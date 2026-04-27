@echo off
chcp 65001 >nul
echo ========================================
echo   连接本地Ollama - 快速启动脚本
echo ========================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未检测到Python，请先安装Python
    pause
    exit /b 1
)

echo ✅ 检测到Python
echo.

REM 检查Ollama是否安装
ollama --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未检测到Ollama，请先安装Ollama
    echo    下载地址：https://ollama.com/download
    pause
    exit /b 1
)

echo ✅ 检测到Ollama
echo.

REM 检查Ollama服务是否运行
curl http://localhost:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Ollama服务未运行，正在启动...
    echo.
    echo 请在新窗口运行以下命令启动Ollama服务：
    echo    ollama serve
    echo.
    echo 等待Ollama启动后，按任意键继续测试...
    pause >nul
)

echo ✅ Ollama服务正在运行
echo.

REM 检查模型是否已下载
echo 检查qwen2.5:7b模型...
curl -s http://localhost:11434/api/tags | findstr "qwen2.5:7b" >nul 2>&1
if errorlevel 1 (
    echo ❌ 模型qwen2.5:7b未安装
    echo.
    echo 正在下载模型...
    echo    ollama pull qwen2.5:7b
    echo.
    ollama pull qwen2.5:7b
    if errorlevel 1 (
        echo ❌ 模型下载失败
        pause
        exit /b 1
    )
)

echo ✅ 模型qwen2.5:7b已安装
echo.

REM 运行测试脚本
echo 运行连接测试...
echo.
python scripts\test_ollama_connection.py
if errorlevel 1 (
    echo.
    echo ❌ 连接测试失败
    echo.
    echo 请检查：
    echo   1. Ollama服务是否正常运行
    echo   2. 模型是否已下载
    echo   3. 项目配置是否正确
    pause
    exit /b 1
)

echo.
echo ========================================
echo   ✅ 连接测试通过！
echo ========================================
echo.
echo 🚀 启动项目：
echo.
echo 1. 确保Ollama服务正在运行（已确认）
echo.
echo 2. 启动后端服务（新开一个终端）：
echo    cd %CD%
echo    python src\main.py
echo.
echo 3. 启动前端服务（新开一个终端）：
echo    cd %CD%
echo    python -m http.server 8000 --directory frontend
echo.
echo 4. 访问界面：
echo    http://localhost:8000
echo.
echo 📚 查看文档：
echo    连接本地Ollama指南.md
echo.
pause
