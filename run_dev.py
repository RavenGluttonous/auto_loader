"""
开发环境运行脚本 - 用于在macOS等开发环境中测试基本功能

这个脚本会临时替换以下组件的实现:
1. error_window - 避免对tkinter的依赖
2. scanner - 使用模拟扫描器，避免串口依赖

便于在开发环境中进行基本功能测试。

注意：此脚本仅用于开发和测试，不应在生产环境中使用。
"""
import os
import sys
import shutil
import importlib
import argparse
import time
import random
import string

# 模块路径定义
MODULE_PATHS = {
    'dialog_box': {
        'original': os.path.join(os.path.dirname(os.path.abspath(__file__)), 'window', 'prompt_dialog_box.py'),
        'dev': os.path.join(os.path.dirname(os.path.abspath(__file__)), 'window', 'prompt_dialog_box_dev.py'),
        'backup': os.path.join(os.path.dirname(os.path.abspath(__file__)), 'window', 'prompt_dialog_box.py.bak')
    },
    'scanner': {
        'original': os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scan', 'scanner.py'),
        'dev': os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scan', 'scanner_dev.py'),
        'backup': os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scan', 'scanner.py.bak')
    }
}

def setup_dev_environment():
    """设置开发环境，替换依赖组件"""
    success = True
    
    for module_name, paths in MODULE_PATHS.items():
        # 如果已有备份，则不进行备份
        if not os.path.exists(paths['backup']) and os.path.exists(paths['original']):
            print(f"创建原始{module_name}模块备份...")
            shutil.copy2(paths['original'], paths['backup'])
        
        # 复制开发版本到正式位置
        if os.path.exists(paths['dev']):
            print(f"使用开发版本的{module_name}...")
            shutil.copy2(paths['dev'], paths['original'])
        else:
            print(f"警告: 找不到开发版本的{module_name}模块")
            success = False
    
    return success

def restore_original_environment():
    """恢复原始环境"""
    for module_name, paths in MODULE_PATHS.items():
        if os.path.exists(paths['backup']):
            print(f"恢复原始{module_name}模块...")
            shutil.copy2(paths['backup'], paths['original'])

def mock_database():
    """创建模拟数据库连接，替换PostgreSQL连接"""
    # 在这里可以添加模拟数据库的代码
    # 本示例中我们让原始代码运行，但会在连接失败时提供更友好的错误处理
    pass

def test_logger():
    """
    测试logger模块的功能
    1. 测试基本日志记录
    2. 测试日志文件轮转功能
    """
    from utils import logger
    import os.path
    
    print("\n" + "="*50)
    print("开始测试日志系统")
    print("="*50)
    
    # 设置测试用的日志配置 - 使用较小的文件大小以便快速测试轮转
    test_log_dir = "logs_test"
    test_prefix = "logger_test"
    max_bytes = 1024 * 1024  # 1MB，便于快速测试
    
    # 确保测试目录存在
    os.makedirs(test_log_dir, exist_ok=True)
    
    # 初始化日志系统
    logger.setup_logging(
        log_level=logger.LOG_LEVEL_DEBUG,
        log_dir=test_log_dir,
        log_file_prefix=test_prefix,
        max_bytes=max_bytes,
        backup_count=5,
        console_output=True
    )
    
    print(f"日志系统已初始化，日志文件将保存在 {test_log_dir} 目录")
    print(f"设置的最大文件大小: {max_bytes/1024:.2f}KB")
    
    # 测试基本日志记录功能
    print("\n测试基本日志记录功能...")
    logger.debug("这是一条DEBUG级别的日志")
    logger.info("这是一条INFO级别的日志")
    logger.warning("这是一条WARNING级别的日志")
    logger.error("这是一条ERROR级别的日志")
    logger.critical("这是一条CRITICAL级别的日志")
    
    try:
        raise ValueError("这是一个异常")
    except Exception as e:
        logger.exception("捕获到异常")
    
    # 测试装饰器
    @logger.log_function_call()
    def test_function(param1, param2):
        logger.info(f"测试函数内部: {param1}, {param2}")
        return param1 + param2
    
    test_function("Hello", "World")
    
    # 测试日志文件轮转
    print("\n测试日志文件轮转功能...")
    print("开始写入大量日志数据，触发日志文件轮转...")
    
    # 获取当前日期，用于构造日志文件名
    from datetime import datetime
    current_date = datetime.now().strftime("%Y%m%d")
    base_log_file = os.path.join(test_log_dir, f"{test_prefix}_{current_date}.log")
    
    # 检查初始日志文件
    if os.path.exists(base_log_file):
        initial_size = os.path.getsize(base_log_file)
        print(f"初始日志文件大小: {initial_size/1024:.2f}KB")
    else:
        print(f"警告: 未找到日志文件 {base_log_file}")
        return
    
    # 生成大量日志以触发文件轮转
    print("生成大量日志记录...")
    rotation_count = 0
    max_rotations = 3  # 最多测试3次轮转
    
    # 先强制写入轮转文件，以确保测试时至少存在两个文件
    for i in range(10):
        # 生成随机字符串作为日志内容
        random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=1000))
        logger.debug(f"大量数据日志 #{i}: {random_str}")
    
    # 循环生成日志直到发现文件轮转
    for i in range(5000):  # 限制最大循环次数
        # 每100条日志检查一次是否发生轮转
        if i % 100 == 0:
            rotated_files = [f for f in os.listdir(test_log_dir) if f.startswith(test_prefix) and f.endswith('.log')]
            rotated_files.sort()
            
            if len(rotated_files) > rotation_count + 1:
                rotation_count = len(rotated_files) - 1
                print(f"检测到日志轮转! 当前日志文件数: {len(rotated_files)}")
                
                # 打印所有日志文件及其大小
                for log_file in rotated_files:
                    file_path = os.path.join(test_log_dir, log_file)
                    size_kb = os.path.getsize(file_path) / 1024
                    print(f"  - {log_file}: {size_kb:.2f}KB")
                
                if rotation_count >= max_rotations:
                    print(f"已达到预设的轮转测试次数 ({max_rotations})，测试完成")
                    break
            
        # 生成随机字符串作为日志内容
        random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=1000))
        logger.debug(f"大量数据日志 #{i}: {random_str}")
        
        # 降低写入速度，避免过快消耗资源
        if i % 10 == 0:
            time.sleep(0.01)
    
    # 最终检查
    rotated_files = [f for f in os.listdir(test_log_dir) if f.startswith(test_prefix) and f.endswith('.log')]
    rotated_files.sort()
    
    print("\n测试结果:")
    if len(rotated_files) > 1:
        print(f"成功! 日志轮转正常工作。共生成 {len(rotated_files)} 个日志文件:")
        for log_file in rotated_files:
            file_path = os.path.join(test_log_dir, log_file)
            size_kb = os.path.getsize(file_path) / 1024
            print(f"  - {log_file}: {size_kb:.2f}KB")
    else:
        print("未检测到日志轮转，可能需要生成更多数据或检查轮转配置")
    
    print("\n日志系统测试完成")
    print("="*50)

if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='AutoLoader开发模式运行工具')
    parser.add_argument('--test-logger', action='store_true', help='测试日志系统功能')
    parser.add_argument('--run', action='store_true', help='运行主程序')
    args = parser.parse_args()
    
    # 如果没有提供任何参数，默认运行主程序
    if not any(vars(parser.parse_args()).values()):
        args.run = True
    
    # 测试日志系统
    if args.test_logger:
        test_logger()
        sys.exit(0)
    
    # 运行主程序
    if args.run:
        print("以开发模式运行AutoLoader...")
        
        try:
            if setup_dev_environment():
                # 重新导入可能已经加载的模块
                for module in ['window.prompt_dialog_box', 'scan.scanner']:
                    if module in sys.modules:
                        del sys.modules[module]
                
                # 设置开发模式标记
                os.environ['AUTOLOADER_DEV_MODE'] = 'TRUE'
                
                # 导入并运行主程序
                print("\n开发模式准备就绪，正在启动主程序...\n")
                import auto_loader
                importlib.reload(auto_loader)  # 确保使用最新版本
                auto_loader.main()
        except Exception as e:
            print(f"开发模式运行错误: {e}")
        finally:
            # 恢复原始环境
            restore_original_environment() 