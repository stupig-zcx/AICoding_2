@echo off
echo 安装依赖...
pip install -r requirements.txt
echo 构建Windows可执行文件...
python build_exe.py build
echo 构建完成！可执行文件位于build文件夹中。
pause