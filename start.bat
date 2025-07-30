@echo off
chcp 65001 >nul
:: =====================================================
:: 指引总结 API 启动脚本
:: 支持：首次自动创建环境 + 二次启动跳过安装 + 强制重装 (-r)
:: =====================================================

echo.
echo === 指引总结 API 服务启动中 ===
echo.

set PROJECT_DIR=D:\guide-summary
cd /d "%PROJECT_DIR%"

:: 检查是否已激活虚拟环境
if defined VIRTUAL_ENV (
    echo ❌ 当前已激活其他虚拟环境，请退出后重试。
    pause
    exit /b 1
)

:: 处理 -r 参数：强制重装
if "%1"=="-r" (
    echo 🧹 正在清理旧环境...
    if exist "venv\" (
        rmdir /q /s venv
        if errorlevel 1 (
            echo ❌ 删除 venv 失败，请关闭正在使用的程序（如编辑器、终端）。
            pause
            exit /b 1
        )
        echo ✅ 已清理旧环境。
    ) else (
        echo 🟨 venv 目录不存在，无需清理。
    )
)

:: 创建虚拟环境（如果不存在）
if not exist "venv\" (
    echo 🌱 虚拟环境不存在，正在创建...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ 创建虚拟环境失败，请检查 Python 是否安装且在 PATH 中。
        pause
        exit /b 1
    )
    echo ✅ 虚拟环境创建成功。
)

:: 激活虚拟环境
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ❌ 激活虚拟环境失败。
    pause
    exit /b 1
)

:: 检查依赖是否已安装
python -c "import fastapi, uvicorn" >nul 2>&1
if errorlevel 1 (
    echo 📦 依赖未安装或不完整，正在安装 requirements.txt...
    pip install -r requirements.txt --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple
    if errorlevel 1 (
        echo ❌ 依赖安装失败，请检查网络或 requirements.txt 文件。
        pause
        exit /b 1
    )
    echo ✅ 依赖安装完成。
) else (
    echo 🟩 虚拟环境和依赖已就绪，跳过安装。
)

:: 启动服务
echo.
echo 🚀 正在启动 FastAPI 服务...
echo    访问 http://localhost:8000/api/v1/docs 查看 API 文档
echo    按 Ctrl+C 停止服务
echo.

:: 启动主程序
python main.py

:: 服务停止后提示
echo.
echo 🔚 服务已停止。
pause