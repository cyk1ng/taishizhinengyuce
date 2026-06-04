@echo off
REM ============================================================
REM 本地模型一键启动脚本（Windows）
REM ============================================================

echo.
echo ============================================================
echo       配网调度系统 - 本地模型启动脚本
echo ============================================================
echo.

REM 检查 Ollama 是否安装
echo [1/4] 检查 Ollama 是否安装...
ollama --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Ollama 未安装！
    echo 请访问 https://ollama.com/download 下载安装
    pause
    exit /b 1
)
echo ✅ Ollama 已安装

REM 检查模型是否已下载
echo.
echo [2/4] 检查本地模型...
ollama list | findstr "qwen2.5:7b" >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  qwen2.5:7b 模型未安装，正在下载...
    ollama pull qwen2.5:7b
    if %errorlevel% neq 0 (
        echo ❌ 模型下载失败！
        pause
        exit /b 1
    )
)
echo ✅ qwen2.5:7b 模型已就绪

REM 启动 Ollama 服务（后台运行）
echo.
echo [3/4] 启动 Ollama 服务...
start /B ollama serve
timeout /t 3 >nul

REM 验证服务是否启动成功
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Ollama 服务启动失败！
    echo 请检查端口 11434 是否被占用
    pause
    exit /b 1
)
echo ✅ Ollama 服务已启动

REM 测试本地模型
echo.
echo [4/4] 测试本地模型连接...
python scripts\test_local_model.py
if %errorlevel% neq 0 (
    echo ⚠️  模型测试失败，请检查配置
) else (
    echo ✅ 本地模型测试通过
)

echo.
echo ============================================================
echo 🎉 本地模型启动成功！
echo ============================================================
echo.
echo 服务信息：
echo   - Ollama API: http://localhost:11434
echo   - 模型名称: qwen2.5:7b
echo   - 查看模型: ollama list
echo.
echo 下一步：
echo   1. 启动系统：python src\main.py
echo   2. 访问界面：http://localhost:8000
echo.
echo 常用命令：
echo   - 查看模型: ollama list
echo   - 测试模型: ollama run qwen2.5:7b "你好"
echo   - 停止服务: Ctrl+C
echo.
pause
