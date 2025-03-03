"""
开发环境配置文件
支持VPN连接到医院局域网数据库
"""
#测试数据 00001719
# 二维码扫描器的COM口 - 开发环境不重要
SERIAL_PORT = "COM8"
# 波特率
BAUDRATE = "115200"

# Oracle数据库配置 - 开发环境不使用
DATABASE1_HOST = "127.0.0.1"
DATABASE2_HOST = "127.0.0.1"
DATABASE_PORT = 1521
DATABASE_SERVICE_NAME = "db"
DATABASE_USERNAME = "his4tl"
DATABASE_PASSWORD = "tlhis4"

# PostgreSQL数据库配置
# VPN模式 - 通过VPN连接到真实数据库
VPN_MODE = False  # 设置为True启用VPN连接模式

if VPN_MODE:
    # 当VPN已连接时使用真实数据库IP
    POSTGRES_HOST = "192.168.88.41"  # 医院局域网数据库IP
    POSTGRES_CONNECT_TIMEOUT = 10  # VPN连接可能较慢，增加超时时间
else:
    # 本地开发模式 - 快速失败
    POSTGRES_HOST = "127.0.0.1"  # localhost，会快速失败
    POSTGRES_CONNECT_TIMEOUT = 2  # 使用短超时

POSTGRES_PORT = 5432
POSTGRES_USERNAME = "lyra_ops"
POSTGRES_PASSWORD = "pVc7EPshyba5"
POSTGRES_DATABASE = "lyradb"

# 开发环境标志
DEV_MODE = True 