import time

import serial.tools.list_ports


class Scanner:
    def __init__(self, serial_port, baudrate, timeout=0):
        """
        初始化
        Args:
            serial_port:串口的名字
            baudrate:波特率
            timeout:读取超时时间
        """
        self.__serial_port = serial_port
        self.__baudrate = baudrate
        self.__timeout = timeout
        self.__qr_code_scanner = serial.Serial(serial_port, baudrate, timeout=timeout)

    def is_open(self) -> bool:
        """
        检查扫描器是否打开
        Returns:
            打开返回True，没打开返回False
        """
        if self.__qr_code_scanner.is_open:
            return True
        else:
            return False

    def open(self):
        """
        打开扫描器的串口连接，创建Scanner对象后不用主动去调用这个方法，该方法适用于close方法关闭后重新打开。
        """
        self.__qr_code_scanner.open()

    def close(self):
        """
        关闭扫描器的串口连接
        """
        self.__qr_code_scanner.close()

    def get_scanner_content(self) -> str:
        """
        获取扫描器的内容，会无限持续等待到扫描器有内容返回
        Returns:
            返回str
        """
        while True:
            if self.__qr_code_scanner.in_waiting:
                content: str = self.__qr_code_scanner.read(self.__qr_code_scanner.in_waiting).decode("gbk")
                return content
            time.sleep(0.5)
