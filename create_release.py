import os
import shutil
import zipfile
from datetime import datetime

def create_release():
    # 定义源目录和目标目录
    build_dir = "build/exe.win-amd64-3.11"
    release_dir = "release"
    
    # 如果release目录已存在，先删除
    if os.path.exists(release_dir):
        shutil.rmtree(release_dir)
    
    # 创建release目录
    os.makedirs(release_dir, exist_ok=True)
    
    # 复制所有文件到release目录
    print("正在创建发布版本...")
    
    # 复制主程序
    shutil.copy(os.path.join(build_dir, "image_processor.exe"), release_dir)
    print("已复制主程序")
    
    # 复制python311.dll
    shutil.copy(os.path.join(build_dir, "python311.dll"), release_dir)
    print("已复制Python运行时")
    
    # 复制frozen_application_license.txt
    shutil.copy(os.path.join(build_dir, "frozen_application_license.txt"), release_dir)
    print("已复制许可证文件")
    
    # 复制lib目录
    shutil.copytree(os.path.join(build_dir, "lib"), os.path.join(release_dir, "lib"))
    print("已复制库文件")
    
    # 复制share目录（如果存在）
    if os.path.exists(os.path.join(build_dir, "share")):
        shutil.copytree(os.path.join(build_dir, "share"), os.path.join(release_dir, "share"))
        print("已复制共享文件")
    
    # 创建一个启动批处理文件
    bat_content = """@echo off
cd /d "%~dp0"
image_processor.exe
pause
"""
    with open(os.path.join(release_dir, "启动图像处理工具.bat"), "w", encoding="utf-8") as f:
        f.write(bat_content)
    
    print("已创建启动批处理文件")
    
    # 创建README文件
    readme_content = """图像处理工具 - 发布版本
========================

这是一个可以直接运行的图像处理工具，支持以下功能：
- 打开多种格式的图像文件（JPG, PNG, BMP, GIF, TIFF等）
- 批量导入图像（可一次性选择多张图片）
- 导入整个文件夹中的图像
- 拖拽导入图像（支持将图像文件拖拽到程序窗口中）
- 调整图像亮度和对比度
- 应用滤镜效果（模糊、边缘增强、锐化）
- 转换为灰度图像
- 保存处理后的图像

使用方法：
1. 双击"启动图像处理工具.bat"运行程序
2. 或者直接双击"image_processor.exe"运行程序

系统要求：
- Windows 7或更高版本

注意：
- 请不要删除任何文件，保持目录结构完整
- 如果需要移动程序到其他位置，请移动整个文件夹
"""
    with open(os.path.join(release_dir, "README.txt"), "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    print("已创建说明文件")
    
    # 创建ZIP压缩包
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"图像处理工具_v{timestamp}.zip"
    
    print("正在创建ZIP压缩包...")
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(release_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arc_path = os.path.relpath(file_path, release_dir)
                zipf.write(file_path, arcname=os.path.join("图像处理工具", arc_path))
    
    print(f"发布版本已创建: {zip_filename}")
    print("发布版本创建完成！")

if __name__ == "__main__":
    create_release()