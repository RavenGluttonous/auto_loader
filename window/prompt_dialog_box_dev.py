"""
开发环境使用的错误提示窗口实现，不依赖Tkinter
仅打印错误信息到控制台，用于开发调试
"""
import time

def error_window(message: str, window_width: int | str, window_height: int | str):
    """
    显示错误信息（开发版本）
    只是简单地打印到控制台，而不是弹出GUI窗口
    """
    print("\n" + "="*50)
    print("错误提示窗口 (开发模式)")
    print("="*50)
    print(f"消息: {message}")
    print(f"窗口尺寸: {window_width}x{window_height}")
    print("="*50)
    print("按Enter键继续...")
    
    # 在开发模式下模拟点击确认按钮
    input()  # 等待用户输入


def close_windows(window):
    """
    关闭窗口的模拟函数
    """
    pass  # 在开发环境中不需要做任何事情 