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

if __name__ == "__main__":
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