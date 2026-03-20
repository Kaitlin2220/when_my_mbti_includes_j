@echo off
chcp 65001 >nul
title 启动本地任务看板
color 0A

cd /d C:\Users\王莹\My_AI_Agents\Schedule_Manager

echo.
echo ================================================
echo   🚀 正在启动本地任务看板...
echo ================================================
echo.

python local_taskboard.py

if errorlevel 1 (
    echo.
    echo ❌ 启动失败！
    echo.
    echo 可能的原因：
    echo 1. Python 未安装或未配置环境变量
    echo 2. 缺少依赖库（tkinter 通常随 Python 自带）
    echo.
    echo 请检查 Python 安装情况
    pause
)
