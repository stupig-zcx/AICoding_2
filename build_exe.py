import sys
from cx_Freeze import setup, Executable

# 依赖项
build_exe_options = {
    "packages": ["tkinter", "PIL"],
    "includes": ["tkinter", "PIL.Image", "PIL.ImageTk", "PIL.ImageEnhance", "PIL.ImageFilter"],
    "include_files": [],
    "excludes": []
}

# 基本配置
base = None
if sys.platform == "win32":
    base = "Win32GUI"  # 这将隐藏控制台窗口

setup(
    name="图像处理工具",
    version="1.0",
    description="简单的图像处理应用程序",
    options={"build_exe": build_exe_options},
    executables=[Executable("image_processor.py", base=base, icon=None)]
)