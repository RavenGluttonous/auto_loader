@echo off
chcp 936 >nul
echo AutoLoader部署配置向导
echo ========================
echo.

if not exist config.py (
    if exist config_example.py (
        echo 未检测到config.py，将从config_example.py创建
        copy config_example.py config.py
        echo config.py已创建，请按照提示进行配置
    ) else (
        echo 错误：找不到config_example.py模板文件！
        echo 请确保部署包中包含config_example.py文件
        pause
        exit /b 1
    )
)

echo.
echo 配置文件检查完成
echo.
echo 请编辑config.py文件，设置以下内容：
echo  - 数据库连接参数（主机名、端口、用户名、密码）
echo  - 扫描器设备端口
echo.
echo 配置完成后，双击auto_loader.exe运行程序
echo.
echo 注意：确保目标系统已安装并配置PostgreSQL数据库
echo.
pause 