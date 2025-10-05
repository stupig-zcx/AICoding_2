import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import sys
from PIL import Image, ImageTk, ImageEnhance, ImageFilter

# 导入tkinterdnd2库实现拖拽功能
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False
    print("未安装tkinterdnd2库，拖拽功能将不可用。请运行 'pip install tkinterdnd2' 安装。")


class ImageProcessorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("图像处理工具")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        
        # 变量
        self.original_image = None
        self.processed_image = None
        self.display_image = None
        self.file_path = None
        self.image_list = []  # 存储导入的图像列表
        self.current_image_index = -1  # 当前显示的图像索引
        
        self.create_widgets()
        
    def create_widgets(self):
        # 创建菜单栏
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="打开图像", command=self.open_image)
        file_menu.add_command(label="批量导入", command=self.import_images)
        file_menu.add_command(label="导入文件夹", command=self.import_folder)
        file_menu.add_command(label="保存", command=self.save_image)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        
        # 编辑菜单
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="编辑", menu=edit_menu)
        edit_menu.add_command(label="重置", command=self.reset_image)
        
        # 主要内容框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左侧控制面板
        control_frame = ttk.Frame(main_frame, width=200)
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        control_frame.pack_propagate(False)
        
        # 图像列表框架
        image_list_frame = ttk.LabelFrame(control_frame, text="图像列表", padding=5)
        image_list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 图像列表
        list_frame = ttk.Frame(image_list_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # 滚动条
        list_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        self.image_listbox = tk.Listbox(list_frame, yscrollcommand=list_scrollbar.set)
        list_scrollbar.config(command=self.image_listbox.yview)
        self.image_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 绑定列表选择事件
        self.image_listbox.bind("<<ListboxSelect>>", self.on_listbox_select)
        
        # 控制面板按钮
        ttk.Button(control_frame, text="打开图像", command=self.open_image).pack(pady=5, fill=tk.X)
        ttk.Button(control_frame, text="批量导入", command=self.import_images).pack(pady=5, fill=tk.X)
        ttk.Button(control_frame, text="导入文件夹", command=self.import_folder).pack(pady=5, fill=tk.X)
        ttk.Button(control_frame, text="保存图像", command=self.save_image).pack(pady=5, fill=tk.X)
        ttk.Button(control_frame, text="重置图像", command=self.reset_image).pack(pady=5, fill=tk.X)
        
        # 右侧主显示区域
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 图像显示区域
        image_frame = ttk.Frame(right_frame)
        image_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # 滚动条
        self.canvas = tk.Canvas(image_frame, bg="gray")
        v_scrollbar = ttk.Scrollbar(image_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        h_scrollbar = ttk.Scrollbar(image_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 拖拽提示标签
        self.drop_label = tk.Label(self.canvas, text="拖拽图像文件到此处\n或使用左侧按钮导入图像", 
                                   bg="lightgray", relief="ridge", padx=20, pady=20)
        self.drop_label.pack(expand=True)
        
        # 如果支持拖拽功能，注册拖拽事件
        if HAS_DND:
            # 注册画布的拖拽事件
            self.canvas.drop_target_register(DND_FILES)
            self.canvas.dnd_bind('<<Drop>>', self.on_drop)
            # 注册拖拽提示标签的拖拽事件
            self.drop_label.drop_target_register(DND_FILES)
            self.drop_label.dnd_bind('<<Drop>>', self.on_drop)
        else:
            # 如果没有拖拽功能，添加提示
            info_label = tk.Label(control_frame, text="提示: 安装tkinterdnd2库可启用拖拽功能", 
                                 fg="red", font=("Arial", 8))
            info_label.pack(side=tk.BOTTOM, pady=5)
        
        # 图像处理选项
        processing_frame = ttk.LabelFrame(right_frame, text="图像处理", padding=5)
        processing_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        
        # 亮度和对比度调整
        adjust_frame = ttk.Frame(processing_frame)
        adjust_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(adjust_frame, text="亮度:").pack(side=tk.LEFT)
        self.brightness_scale = ttk.Scale(adjust_frame, from_=0.0, to=2.0, value=1.0, command=self.adjust_brightness)
        self.brightness_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        ttk.Label(adjust_frame, text="对比度:").pack(side=tk.LEFT)
        self.contrast_scale = ttk.Scale(adjust_frame, from_=0.0, to=2.0, value=1.0, command=self.adjust_contrast)
        self.contrast_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 滤镜选项
        filter_frame = ttk.Frame(processing_frame)
        filter_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(filter_frame, text="滤镜:").pack(side=tk.LEFT)
        ttk.Button(filter_frame, text="模糊", command=lambda: self.apply_filter(ImageFilter.BLUR)).pack(side=tk.LEFT, padx=2)
        ttk.Button(filter_frame, text="边缘增强", command=lambda: self.apply_filter(ImageFilter.EDGE_ENHANCE)).pack(side=tk.LEFT, padx=2)
        ttk.Button(filter_frame, text="锐化", command=lambda: self.apply_filter(ImageFilter.SHARPEN)).pack(side=tk.LEFT, padx=2)
        ttk.Button(filter_frame, text="灰度化", command=self.convert_to_grayscale).pack(side=tk.LEFT, padx=2)
        
        # 信息显示区域
        self.info_label = ttk.Label(control_frame, text="请导入图像文件开始处理")
        self.info_label.pack(side=tk.BOTTOM, pady=10)
        
    def open_image(self):
        file_paths = filedialog.askopenfilenames(
            title="选择图像文件",
            filetypes=[
                ("图像文件", "*.jpg *.jpeg *.png *.bmp *.gif *.tiff"),
                ("JPEG文件", "*.jpg *.jpeg"),
                ("PNG文件", "*.png"),
                ("BMP文件", "*.bmp"),
                ("所有文件", "*.*")
            ]
        )
        
        if file_paths:
            self.add_images_to_list(file_paths)
    
    def import_images(self):
        self.open_image()
    
    def import_folder(self):
        folder_path = filedialog.askdirectory(title="选择包含图像的文件夹")
        if folder_path:
            image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff')
            image_files = []
            
            for file in os.listdir(folder_path):
                if file.lower().endswith(image_extensions):
                    image_files.append(os.path.join(folder_path, file))
            
            if image_files:
                self.add_images_to_list(image_files)
            else:
                messagebox.showinfo("提示", "所选文件夹中未找到图像文件")
    
    def add_images_to_list(self, file_paths):
        # 添加新图像到列表
        for file_path in file_paths:
            if file_path not in [img['path'] for img in self.image_list]:
                try:
                    # 获取文件名（不含路径）
                    filename = os.path.basename(file_path)
                    self.image_list.append({
                        'path': file_path,
                        'name': filename
                    })
                    self.image_listbox.insert(tk.END, filename)
                except Exception as e:
                    messagebox.showerror("错误", f"无法加载图像 {file_path}:\n{str(e)}")
        
        # 如果这是第一批图像，自动选择第一个
        if len(self.image_list) > 0 and self.current_image_index == -1:
            self.image_listbox.selection_set(0)
            self.load_image(0)
    
    def load_image(self, index):
        if 0 <= index < len(self.image_list):
            self.current_image_index = index
            file_path = self.image_list[index]['path']
            
            try:
                self.original_image = Image.open(file_path)
                self.processed_image = self.original_image.copy()
                self.file_path = file_path
                self.display_image_on_canvas()
                self.update_info()
                
                # 更新列表框选择
                self.image_listbox.selection_clear(0, tk.END)
                self.image_listbox.selection_set(index)
                self.image_listbox.see(index)
            except Exception as e:
                messagebox.showerror("错误", f"无法打开图像文件:\n{str(e)}")
    
    def on_listbox_select(self, event):
        selection = self.image_listbox.curselection()
        if selection:
            index = selection[0]
            self.load_image(index)
    
    def display_image_on_canvas(self):
        # 隐藏拖拽提示
        self.drop_label.pack_forget()
        
        if self.processed_image:
            # 调整图像大小以适应显示区域
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            # 如果画布大小为1，说明还未正确初始化，使用默认大小
            if canvas_width <= 1:
                canvas_width = 600
            if canvas_height <= 1:
                canvas_height = 400
            
            img_width, img_height = self.processed_image.size
            
            # 计算缩放比例
            scale_w = canvas_width / img_width
            scale_h = canvas_height / img_height
            scale = min(scale_w, scale_h, 1.0)  # 不放大图像
            
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            
            # 缩放图像
            resized_image = self.processed_image.resize((new_width, new_height), Image.LANCZOS)
            self.display_image = ImageTk.PhotoImage(resized_image)
            
            # 清除画布并显示新图像
            self.canvas.delete("all")
            self.canvas.create_image(canvas_width/2, canvas_height/2, image=self.display_image)
            self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))
    
    def update_info(self):
        if self.processed_image:
            width, height = self.processed_image.size
            file_size = os.path.getsize(self.file_path) if self.file_path and os.path.exists(self.file_path) else 0
            file_size_str = self.format_file_size(file_size)
            image_info = f"尺寸: {width}x{height}px\n文件大小: {file_size_str}\n图像 {self.current_image_index + 1}/{len(self.image_list)}"
            self.info_label.config(text=image_info)
    
    def format_file_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def adjust_brightness(self, value):
        if self.original_image:
            brightness = float(value)
            enhancer = ImageEnhance.Brightness(self.original_image)
            self.processed_image = enhancer.enhance(brightness)
            self.display_image_on_canvas()
    
    def adjust_contrast(self, value):
        if self.original_image:
            contrast = float(value)
            enhancer = ImageEnhance.Contrast(self.original_image)
            self.processed_image = enhancer.enhance(contrast)
            self.display_image_on_canvas()
    
    def apply_filter(self, filter_type):
        if self.processed_image:
            self.processed_image = self.processed_image.filter(filter_type)
            self.display_image_on_canvas()
    
    def convert_to_grayscale(self):
        if self.processed_image:
            self.processed_image = self.processed_image.convert("L")
            self.display_image_on_canvas()
    
    def reset_image(self):
        if self.original_image:
            self.processed_image = self.original_image.copy()
            self.brightness_scale.set(1.0)
            self.contrast_scale.set(1.0)
            self.display_image_on_canvas()
    
    def save_image(self):
        if self.processed_image:
            file_path = filedialog.asksaveasfilename(
                title="保存图像",
                defaultextension=".png",
                filetypes=[
                    ("PNG格式", "*.png"),
                    ("JPEG格式", "*.jpg"),
                    ("BMP格式", "*.bmp"),
                    ("TIFF格式", "*.tiff")
                ]
            )
            
            if file_path:
                try:
                    self.processed_image.save(file_path)
                    messagebox.showinfo("成功", f"图像已保存到:\n{file_path}")
                except Exception as e:
                    messagebox.showerror("错误", f"保存图像时出错:\n{str(e)}")
        else:
            messagebox.showwarning("警告", "没有可保存的图像")
    
    # 处理拖拽文件的方法
    def on_drop(self, event):
        """处理拖拽到窗口的文件"""
        # 获取拖拽的文件列表
        if event.data:
            # 解析拖拽的数据
            # event.data 是一个包含文件路径的字符串，多个文件用空格分隔
            # 路径可能包含空格，需要用特殊方式处理
            import shlex
            file_paths = shlex.split(event.data)
            
            # 过滤出图像文件
            image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff')
            image_files = []
            
            for file_path in file_paths:
                # 移除可能的引号
                file_path = file_path.strip('"')
                if os.path.isfile(file_path) and file_path.lower().endswith(image_extensions):
                    image_files.append(file_path)
                elif os.path.isdir(file_path):
                    # 如果是目录，则导入目录中的所有图像
                    for subfile in os.listdir(file_path):
                        if subfile.lower().endswith(image_extensions):
                            image_files.append(os.path.join(file_path, subfile))
            
            if image_files:
                self.add_images_to_list(image_files)
            else:
                messagebox.showinfo("提示", "拖拽的文件中没有找到支持的图像文件")


def main():
    # 如果支持拖拽，使用TkinterDnD创建根窗口，否则使用普通tk.Tk()
    if HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    
    app = ImageProcessorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()