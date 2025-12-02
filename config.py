# 二维码扫描器的COM口
# 妇科机器使用的是COM5
SERIAL_PORT = "COM8"
# 波特率
BAUDRATE = "115200"

# PostgreSQL数据库配置
POSTGRES_HOST = "192.168.88.41"
POSTGRES_PORT = 5432
POSTGRES_USERNAME = "lyra_ops"
POSTGRES_PASSWORD = "pVc7EPshyba5"  # 请替换为实际密码
POSTGRES_DATABASE = "lyradb"


# Xcope 接口配置（可根据实际环境修改）
XCOPE_BASE_URL = "http://127.0.0.1:9601"
XCOPE_CLIENT_ID = "Xcope_ExternalApi"
XCOPE_CLIENT_SECRET = "123456"
XCOPE_SCOPE = "Xcope"


# 状态变更回传接口(MES0167)操作人配置
# JSON 结构：数组类型，元素数量 1..N，可按需增删，代码中当前默认取第一个元素
# 每个元素包含：
# - UpdateUserCode：更新人工号
# - UpdateUserName：更新人姓名
STATUS_UPDATE_USERS = [
    {
        "UpdateUserCode": "AutoLoader",
        "UpdateUserName": "AutoLoader",
    },
]
