"""
开发环境使用的系统托盘模拟实现
不实际创建系统托盘图标，仅打印相关信息
"""

class TrayTask:
    def __init__(self):
        print("[DEV] 初始化系统托盘模拟器")
    
    def setup_systray(self):
        """
        模拟设置系统托盘图标
        """
        print("[DEV] 模拟系统托盘已启动")
        print("[DEV] 退出程序请按Ctrl+C或在模拟扫描器中输入'exit'")
    
    def quit_application(self):
        """
        退出应用
        """
        print("[DEV] 用户通过系统托盘请求退出")
        import os, signal
        pid = os.getpid()
        os.kill(pid, signal.SIGTERM) 