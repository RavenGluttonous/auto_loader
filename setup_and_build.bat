@echo off
setlocal enabledelayedexpansion
title AutoLoader一键式安装和构建工具
color 0A

echo ==========================================
echo    AutoLoader自动安装和构建工具
echo    设计用于非开发人员使用
echo ==========================================
echo.

REM 检查Python是否安装
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到Python，请先安装Python 3.8或更高版本
    echo 可以从 https://www.python.org/downloads/windows/ 下载
    pause
    exit /b 1
)

REM 创建日志目录
if not exist "logs\" mkdir logs
set LOG_FILE=logs\setup_%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%.log
REM 替换日志文件名中的空格
set LOG_FILE=!LOG_FILE: =0!

echo [%time%] 开始安装过程 > %LOG_FILE%

REM 步骤1：下载Oracle Instant Client
echo [步骤1/4] 检查Oracle客户端...
if not exist "instantclient-basic\" (
    echo Oracle客户端不存在，准备下载...
    echo.
    
    REM Oracle客户端下载地址（这里使用Oracle 23.4版本，根据需要可以更改）
    set ORACLE_CLIENT_URL=https://download.oracle.com/otn_software/nt/instantclient/2340000/instantclient-basic-windows.x64-23.4.0.0.0dbru.zip
    set ORACLE_ZIP=instantclient-basic-windows.x64-23.4.0.0.0dbru.zip
    
    echo [%time%] 下载Oracle客户端... >> %LOG_FILE%
    echo 正在下载Oracle客户端...这可能需要几分钟...
    
    REM 使用PowerShell下载文件
    powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%ORACLE_CLIENT_URL%' -OutFile '%ORACLE_ZIP%'}" >> %LOG_FILE% 2>&1
    
    if not exist "%ORACLE_ZIP%" (
        echo [错误] 下载Oracle客户端失败。
        echo 请手动下载Oracle Instant Client并解压到项目根目录下的instantclient-basic文件夹
        echo 下载地址: %ORACLE_CLIENT_URL%
        echo 详情请查看 %LOG_FILE%
        pause
        exit /b 1
    )
    
    echo [%time%] 解压Oracle客户端... >> %LOG_FILE%
    echo 正在解压Oracle客户端...
    
    REM 创建目录并解压
    if not exist "instantclient-basic\" mkdir instantclient-basic
    powershell -Command "& {Expand-Archive -Path '%ORACLE_ZIP%' -DestinationPath 'instantclient-basic\' -Force}" >> %LOG_FILE% 2>&1
    
    if %errorlevel% neq 0 (
        echo [错误] 解压Oracle客户端失败。
        echo 详情请查看 %LOG_FILE%
        pause
        exit /b 1
    )
    
    echo 删除下载的压缩包...
    del "%ORACLE_ZIP%" >> %LOG_FILE% 2>&1
    echo Oracle客户端安装完成！
) else (
    echo Oracle客户端已存在，跳过下载步骤。
)
echo.

REM 步骤2：安装Python依赖
echo [步骤2/4] 安装Python依赖...
echo [%time%] 安装Python依赖... >> %LOG_FILE%
pip install -r requirements.txt >> %LOG_FILE% 2>&1

if %errorlevel% neq 0 (
    echo [错误] 安装Python依赖失败。
    echo 详情请查看 %LOG_FILE%
    pause
    exit /b 1
)
echo Python依赖安装完成！
echo.

REM 步骤3：配置文件准备
echo [步骤3/4] 准备配置文件...
echo [%time%] 检查配置文件... >> %LOG_FILE%

if not exist "config.py" (
    if exist "config_example.py" (
        echo 未找到config.py，正在从config_example.py创建...
        copy config_example.py config.py >> %LOG_FILE% 2>&1
        echo 已创建config.py，请在构建后根据需要修改配置！
    ) else (
        echo [警告] 未找到config.py或config_example.py
        echo 构建可能会失败，请确保程序运行前有正确的配置文件
    )
)
echo.

REM 步骤4：构建可执行文件
echo [步骤4/4] 构建可执行文件...
echo [%time%] 开始构建... >> %LOG_FILE%
echo 正在构建可执行文件，这可能需要几分钟时间...

pyinstaller --name="auto_loader" --windowed --icon=icon.ico --add-data="icon.ico;." --add-data="beep.wav;." main.py >> %LOG_FILE% 2>&1

if %errorlevel% neq 0 (
    echo [错误] 构建可执行文件失败。
    echo 详情请查看 %LOG_FILE%
    pause
    exit /b 1
)

echo.
echo [%time%] 构建过程完成 >> %LOG_FILE%
echo ==========================================
echo    构建完成！
echo    可执行文件位于dist目录中
echo ==========================================
echo.
echo 详细日志保存在: %LOG_FILE%
echo.
pause
exit /b 0 