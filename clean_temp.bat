@echo off
chcp 65001 >nul
echo ========================================
echo 清理临时文件
echo ========================================
echo.

cd /d "%~dp0"

echo 正在清理临时文件...
del /f /q temp_notes*.sqlite 2>nul

if %errorlevel% == 0 (
    echo ✅ 临时文件已清理
) else (
    echo ℹ️  没有需要清理的文件
)

echo.
echo 现在可以重新启动任务看板了
echo.
pause
