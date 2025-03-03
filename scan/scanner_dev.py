"""
开发环境使用的模拟扫描器实现
不需要实际的串口连接，通过命令行输入模拟扫描
"""

class Scanner:
    def __init__(self, serial_port, baudrate, timeout=0):
        """
        初始化模拟扫描器
        Args:
            serial_port: 忽略
            baudrate: 忽略
            timeout: 忽略
        """
        print(f"[DEV] 初始化模拟扫描器 (实际串口:{serial_port}, 波特率:{baudrate})")
        self.__serial_port = serial_port
        self.__baudrate = baudrate
        self.__timeout = timeout
        self.__is_open = True

    def is_open(self) -> bool:
        """
        检查扫描器是否打开
        Returns:
            打开返回True，没打开返回False
        """
        return self.__is_open

    def open(self):
        """
        打开扫描器的串口连接
        """
        self.__is_open = True
        print("[DEV] 模拟扫描器已打开")

    def close(self):
        """
        关闭扫描器的串口连接
        """
        self.__is_open = False
        print("[DEV] 模拟扫描器已关闭")

    def get_scanner_content(self) -> str:
        """
        通过命令行输入模拟扫描器输入
        Returns:
            返回用户输入的字符串
        """
        print("\n" + "="*50)
        print("[DEV] 模拟扫描器等待输入")
        print("="*50)
        print("请输入模拟扫描内容 (输入 'TJ12345' 模拟体检条码, 或输入其他值模拟诊疗卡号)")
        print("特殊命令: 'AutoLoaderRollback' 回退编号, 'exit' 退出程序")
        print("="*50)
        
        content = input(">> ")
        
        if content.lower() == 'exit':
            print("[DEV] 用户请求退出程序")
            import os, signal
            pid = os.getpid()
            os.kill(pid, signal.SIGTERM)
            
        return content 