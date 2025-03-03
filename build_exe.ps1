# 构建独立的Windows可执行文件
# 请在Windows系统上运行此脚本

# 清理之前的构建
if (Test-Path ".\build") {
    Remove-Item -Path ".\build" -Recurse -Force
}
if (Test-Path ".\dist") {
    Remove-Item -Path ".\dist" -Recurse -Force
}

# 确保最新的依赖已安装
python -m pip install -r requirements.txt

# 使用PyInstaller构建可执行文件
python -m PyInstaller --onefile --noconsole --add-data "logo.jpg;." --icon="logo.jpg" --name="auto_loader" --add-binary=".\instantclient-basic\instantclient_23_4\*;.\instantclient-basic\instantclient_23_4" auto_loader.py