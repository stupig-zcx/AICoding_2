import os
import shutil
import zipfile
from datetime import datetime

def package_application():
    """
    将构建的可执行文件打包成一个zip文件以便分发
    """
    build_dir = "build/exe.win-amd64-3.11"
    if not os.path.exists(build_dir):
        print("错误: 未找到构建目录。请先运行 'python build_exe.py build' 命令。")
        return
    
    # 创建版本号
    version = datetime.now().strftime("%Y%m%d_%H%M%S")
    package_name = f"image_processor_win64_{version}"
    
    # 创建临时目录
    temp_dir = f"temp_{package_name}"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)
    
    # 复制所有文件到临时目录
    print("正在复制文件...")
    for item in os.listdir(build_dir):
        source = os.path.join(build_dir, item)
        destination = os.path.join(temp_dir, item)
        if os.path.isdir(source):
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)
    
    # 添加README文件
    readme_content = """图像处理工具
================

这是一个简单的图像处理应用程序，可以对图像进行基本的编辑操作。

系统要求:
- Windows 7 或更高版本
- 无需安装Python或其他依赖项

使用方法:
1. 解压此压缩包到任意目录
2. 双击运行 image_processor.exe

功能:
- 打开多种格式的图像文件（JPG, PNG, BMP, GIF, TIFF等）
- 调整图像亮度和对比度
- 应用滤镜效果（模糊、边缘增强、锐化）
- 转换为灰度图像
- 保存处理后的图像

注意: 
这是绿色软件，所有设置和数据都保存在程序所在目录。
"""
    
    with open(os.path.join(temp_dir, "README.txt"), "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    # 创建zip文件
    print("正在创建zip包...")
    zip_filename = f"{package_name}.zip"
    shutil.make_archive(package_name, 'zip', temp_dir)
    
    # 清理临时目录
    shutil.rmtree(temp_dir)
    
    print(f"打包完成！创建了 {zip_filename}")
    print("您可以分发此zip文件给其他Windows用户。")

if __name__ == "__main__":
    package_application()