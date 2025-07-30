@echo off
chcp 65001 >nul
:: =====================================================
:: 停止指引总结 API 服务
:: 结束所有 python main.py 进程
:: =====================================================

echo.
echo === 正在停止指引总结 API 服务 ===
echo.

set PROJECT_DIR=D:\guide-summary
cd /d "%PROJECT_DIR%"

:: 查找并结束 python main.py 进程
tasklist | findstr /i "python.*main.py" >nul
if errorlevel 1 (
    echo 🟨 未检测到正在运行的 API 服务。
) else (
    echo 🛑 正在终止 python main.py 进程...
    taskkill /f /im python.exe /fi "cmdline eq main.py"
    if errorlevel 1 (
        echo ❌ 终止失败，请手动检查任务管理器。
    ) else (
        echo ✅ 服务已停止。
    )
)

pause