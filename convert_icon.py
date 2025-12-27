"""
将 logo.png 转换为 logo.ico 用于 PyInstaller 打包
"""
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("正在安装 Pillow...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
    from PIL import Image

def convert_png_to_ico(png_path, ico_path):
    """将 PNG 转换为 ICO"""
    try:
        img = Image.open(png_path)
        # 创建多个尺寸的图标（Windows 需要）
        sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        img.save(ico_path, format='ICO', sizes=sizes)
        print(f"✓ 成功将 {png_path} 转换为 {ico_path}")
        return True
    except Exception as e:
        print(f"✗ 转换失败: {e}")
        return False

if __name__ == "__main__":
    script_dir = Path(__file__).parent
    png_path = script_dir / "logo.png"
    ico_path = script_dir / "logo.ico"
    
    if not png_path.exists():
        print(f"✗ 未找到 {png_path}")
        sys.exit(1)
    
    if ico_path.exists():
        print(f"✓ {ico_path} 已存在，跳过转换")
    else:
        if convert_png_to_ico(png_path, ico_path):
            print("图标转换完成")
        else:
            sys.exit(1)

