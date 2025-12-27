#!/usr/bin/env python3
"""
Sora 2 视频生成工具启动脚本
提供GUI和命令行两种模式选择
"""

import sys
import os
from pathlib import Path


def check_dependencies():
    """检查依赖包"""
    print("检查依赖包...")

    required_packages = ['requests']
    optional_packages = ['PyQt5', 'PyQt-Fluent-Widgets']

    missing_required = []
    missing_optional = []

    # 检查必需包
    for package in required_packages:
        try:
            __import__(package)
            print(f"[OK] {package}")
        except ImportError:
            missing_required.append(package)
            print(f"[FAIL] {package}")

    # 检查可选包
    for package in optional_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"[OK] {package}")
        except ImportError:
            missing_optional.append(package)
            print(f"[FAIL] {package}")

    if missing_required:
        print(f"\n缺少必需依赖: {', '.join(missing_required)}")
        print("请运行: pip install -r requirements.txt")
        return False

    return True


def install_dependencies():
    """安装依赖包"""
    print("正在安装依赖包...")
    try:
        import subprocess
        result = subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'],
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("[OK] 依赖安装成功")
            return True
        else:
            print(f"[ERROR] 依赖安装失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"[ERROR] 安装依赖时出错: {e}")
        return False


def launch_gui():
    """启动GUI界面"""
    print("启动GUI界面...")
    try:
        # 在导入PyQt5之前设置插件路径
        import os
        import sys
        
        # 隐藏 PyQt-Fluent-Widgets 的 Pro 版本提示
        os.environ['QFluentWidgets_DISABLE_PRO_TIP'] = '1'
        
        # 设置Qt插件路径
        # 处理打包后的资源路径
        if getattr(sys, 'frozen', False):
            # 打包后的exe环境，使用临时解压目录
            base_path = Path(sys._MEIPASS)
            # 单文件模式下，插件放在根目录的 plugins/platforms 下
            # QT_PLUGIN_PATH 应该指向包含 platforms 目录的父目录
            plugins_base = base_path / 'plugins'
            platforms_dir = plugins_base / 'platforms'
            
            if platforms_dir.exists():
                os.environ['QT_PLUGIN_PATH'] = str(plugins_base)
                print(f"设置Qt插件路径: {plugins_base}")
                print(f"检查platforms目录: {platforms_dir.exists()}")
                if platforms_dir.exists():
                    files = list(platforms_dir.glob('*.dll'))
                    print(f"找到 {len(files)} 个插件文件: {[f.name for f in files]}")
            else:
                # 尝试其他可能的路径
                plugins_path = base_path / 'PyQt5' / 'Qt5' / 'plugins'
                if plugins_path.exists():
                    os.environ['QT_PLUGIN_PATH'] = str(plugins_path)
                    print(f"设置Qt插件路径: {plugins_path}")
                else:
                    print(f"警告: 未找到Qt插件目录！")
                    print(f"检查路径: {plugins_base}")
                    print(f"检查路径: {base_path / 'PyQt5' / 'Qt5' / 'plugins'}")
        else:
            # 开发环境，从site-packages中找到PyQt5路径
            for path in sys.path:
                pyqt5_path = os.path.join(path, 'PyQt5')
                if os.path.exists(pyqt5_path):
                    plugins_path = os.path.join(pyqt5_path, 'Qt5', 'plugins')
                    if os.path.exists(plugins_path):
                        # 转换为绝对路径并规范化
                        plugins_path = os.path.abspath(plugins_path)
                        os.environ['QT_PLUGIN_PATH'] = plugins_path
                        print(f"设置Qt插件路径: {plugins_path}")
                        break
        
        # 直接导入并启动GUI，不进行额外的依赖检查
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import QCoreApplication
        from main_window import MainWindow
        from constants import PROJECT_NAME
        
        app = QApplication(sys.argv)
        
        # 添加全局异常处理器，防止QFluentWidgets库的bug导致崩溃
        def exception_handler(exc_type, exc_value, exc_traceback):
            """全局异常处理器"""
            # 忽略QFluentWidgets库中已知的bug
            if exc_type == AttributeError:
                error_msg = str(exc_value)
                # 检查是否是已知的QFluentWidgets bug
                if "'QWheelEvent' object has no attribute 'propertyName'" in error_msg:
                    # 这是QFluentWidgets库的bug，忽略它
                    return
                elif "propertyName" in error_msg and "QWheelEvent" in error_msg:
                    # 类似的bug，也忽略
                    return
            
            # 其他异常正常处理
            import traceback
            traceback.print_exception(exc_type, exc_value, exc_traceback)
        
        # 设置全局异常处理器
        sys.excepthook = exception_handler
        
        # 在创建 QApplication 后，使用 addLibraryPath 设置插件路径
        if getattr(sys, 'frozen', False):
            base_path = Path(sys._MEIPASS)
            plugins_base = base_path / 'plugins'
            platforms_dir = plugins_base / 'platforms'
            
            if platforms_dir.exists():
                # 使用 Qt 的方法添加插件路径
                QCoreApplication.addLibraryPath(str(plugins_base))
                print(f"使用 addLibraryPath 添加插件路径: {plugins_base}")
                files = list(platforms_dir.glob('*.dll'))
                print(f"找到 {len(files)} 个平台插件文件: {[f.name for f in files]}")
                
                # 检查音频插件
                audio_dir = plugins_base / 'audio'
                if audio_dir.exists():
                    audio_files = list(audio_dir.glob('*.dll'))
                    print(f"找到 {len(audio_files)} 个音频插件文件: {[f.name for f in audio_files]}")
                
                # 检查媒体服务插件
                mediaservice_dir = plugins_base / 'mediaservice'
                if mediaservice_dir.exists():
                    mediaservice_files = list(mediaservice_dir.glob('*.dll'))
                    print(f"找到 {len(mediaservice_files)} 个媒体服务插件文件: {[f.name for f in mediaservice_files]}")
            else:
                # 尝试其他路径
                plugins_path = base_path / 'PyQt5' / 'Qt5' / 'plugins'
                if plugins_path.exists():
                    QCoreApplication.addLibraryPath(str(plugins_path))
                    print(f"使用 addLibraryPath 添加插件路径: {plugins_path}")

        # 设置应用程序信息
        app.setApplicationName(PROJECT_NAME)
        app.setOrganizationName(PROJECT_NAME)
        
        # 设置应用程序图标（用于任务栏）
        from PyQt5.QtGui import QIcon
        # 处理打包后的资源路径
        if getattr(sys, 'frozen', False):
            # 打包后的exe环境
            base_path = Path(sys._MEIPASS)
        else:
            # 开发环境
            base_path = Path(__file__).parent
        
        # 优先尝试 .ico 格式，如果没有则使用 .png
        logo_path = base_path / "logo.ico"
        if not logo_path.exists():
            logo_path = base_path / "logo.png"
        
        if logo_path.exists():
            app.setWindowIcon(QIcon(str(logo_path)))

        window = MainWindow()
        window.show()
        sys.exit(app.exec())

    except ImportError as e:
        print(f"[ERROR] GUI依赖缺失: {e}")
        print("请运行: pip install PyQt5 PyQt-Fluent-Widgets")
        return False
    except Exception as e:
        print(f"[ERROR] 启动GUI失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    # 设置工作目录
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    # 检查Python版本
    if sys.version_info < (3, 7):
        print("[ERROR] 需要Python 3.7或更高版本")
        print(f"当前版本: {sys.version}")
        return

    print(f"Python版本: {sys.version.split()[0]}")
    print(f"工作目录: {script_dir}")

    # 直接启动GUI界面
    print("正在启动GUI界面...")
    launch_gui()


if __name__ == "__main__":
    main()