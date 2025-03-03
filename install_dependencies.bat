@echo off
echo 正在安装AutoLoader所需的依赖项...
echo.

REM 检查是否已安装Python
python --version 2>NUL
if %ERRORLEVEL% NEQ 0 (
    echo Python未安装，请先安装Python 3.8或更高版本
    echo 可以从 https://www.python.org/downloads/ 下载
    pause
    exit /b 1
)

REM 安装依赖项
echo 正在安装依赖项...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if %ERRORLEVEL% NEQ 0 (
    echo 安装依赖项时出错，请检查网络连接并重试
    pause
    exit /b 1
)

echo.
echo 依赖项安装完成！
echo 现在可以运行AutoLoader程序了
echo.
pause 