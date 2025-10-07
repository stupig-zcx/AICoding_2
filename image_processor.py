import tkinter as tk
from tkinter import filedialog, messagebox, ttk, colorchooser
import os
import sys
from PIL import Image, ImageTk, ImageEnhance, ImageFilter, ImageDraw, ImageFont
import json

# 获取系统字体
try:
    from tkinter import font
    SYSTEM_FONTS = list(font.families())
    SYSTEM_FONTS.sort()
except:
    SYSTEM_FONTS = ["Arial", "Times New Roman", "Courier New", "SimHei", "SimSun", "Microsoft YaHei"]

# 导入tkinterdnd2库实现拖拽功能
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False
    print("未安装tkinterdnd2库，拖拽功能将不可用。请运行 'pip install tkinterdnd2' 安装。")


class ScrollableImageList(tk.Frame):
    """可滚动的图像列表框架"""
    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app
        self.thumbnails = []  # 存储缩略图标签引用
        
        # 创建画布和滚动条
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        # 配置画布滚动
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        # 绑定事件
        self.scrollable_frame.bind("<Configure>", self.on_frame_configure)
        self.canvas.bind("<Configure>", self.on_canvas_configure)
        
        # 鼠标滚轮支持
        self.bind_mousewheel()
        
        # 布局
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # 网格布局参数
        self.columns = 2  # 默认每行显示两个缩略图
        self.thumbnail_size = (80, 80)
        
    def bind_mousewheel(self):
        """绑定鼠标滚轮事件"""
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            
        def _bind_to_mousewheel(event):
            self.canvas.bind_all("<MouseWheel>", _on_mousewheel)
            
        def _unbind_from_mousewheel(event):
            self.canvas.unbind_all("<MouseWheel>")
            
        self.canvas.bind('<Enter>', _bind_to_mousewheel)
        self.canvas.bind('<Leave>', _unbind_from_mousewheel)
        
    def on_frame_configure(self, event=None):
        """当滚动框架大小改变时更新滚动区域"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
    def on_canvas_configure(self, event):
        """当画布大小改变时调整窗口大小"""
        canvas_width = event.width
        self.canvas.itemconfig(self.canvas_window, width=canvas_width)
        self.update_layout()
        
    def update_layout(self):
        """更新缩略图布局"""
        # 固定每行显示两个缩略图
        self.columns = 2
            
        # 重新排列所有缩略图
        for i, thumbnail_frame in enumerate(self.thumbnails):
            row = i // self.columns
            col = i % self.columns
            thumbnail_frame.grid(row=row, column=col, padx=5, pady=5)
            
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
    def add_thumbnail(self, image_path, thumbnail_image, filename):
        """添加缩略图到列表"""
        index = len(self.thumbnails)
        
        # 创建缩略图框架
        thumbnail_frame = ttk.Frame(self.scrollable_frame, relief="ridge", padding=2)
        thumbnail_frame.index = index  # 保存索引
        
        # 创建缩略图标签
        thumbnail_label = tk.Label(thumbnail_frame, image=thumbnail_image, bd=0)
        thumbnail_label.pack()
        
        # 创建文件名标签
        name_label = ttk.Label(thumbnail_frame, text=filename, font=("Arial", 8))
        name_label.pack()
        
        # 绑定点击事件
        for widget in [thumbnail_frame, thumbnail_label, name_label]:
            widget.bind("<Button-1>", lambda e, idx=index: self.app.load_image(idx))
            
        self.thumbnails.append(thumbnail_frame)
        self.update_layout()
        
    def clear(self):
        """清空所有缩略图"""
        for thumbnail in self.thumbnails:
            thumbnail.destroy()
        self.thumbnails = []


class WatermarkTemplateManager:
    """水印模板管理器"""
    def __init__(self, app):
        self.app = app
        self.templates_file = "watermark_templates.json"
        self.templates = {}
        self.load_templates()
        
    def load_templates(self):
        """加载水印模板"""
        try:
            if os.path.exists(self.templates_file):
                with open(self.templates_file, 'r', encoding='utf-8') as f:
                    self.templates = json.load(f)
        except Exception as e:
            print(f"加载水印模板失败: {e}")
            self.templates = {}
            
    def save_templates(self):
        """保存水印模板"""
        try:
            with open(self.templates_file, 'w', encoding='utf-8') as f:
                json.dump(self.templates, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存水印模板失败: {e}")
            
    def add_template(self, name, settings):
        """添加模板"""
        self.templates[name] = settings
        self.save_templates()
        
    def remove_template(self, name):
        """删除模板"""
        if name in self.templates:
            del self.templates[name]
            self.save_templates()
            
    def get_template(self, name):
        """获取模板"""
        return self.templates.get(name, None)
        
    def get_template_names(self):
        """获取所有模板名称"""
        return list(self.templates.keys())


class ImageProcessorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("图像处理工具")
        self.root.geometry("1200x700")
        self.root.minsize(1000, 600)
        
        # 变量
        self.original_image = None
        self.processed_image = None
        self.display_image = None
        self.file_path = None
        self.image_list = []  # 存储导入的图像列表
        self.current_image_index = -1  # 当前显示的图像索引
        self.thumbnail_size = (80, 80)  # 缩略图大小
        
        # 默认水印变量
        self.default_watermark_vars = {
            'text': tk.StringVar(value="水印文本"),
            'font_family': tk.StringVar(value="Microsoft YaHei"),  # 更改为微软雅黑作为默认字体
            'font_size': tk.IntVar(value=20),
            'bold': tk.BooleanVar(value=False),
            'italic': tk.BooleanVar(value=False),
            'color': tk.StringVar(value="#000000"),  # 黑色
            'opacity': tk.IntVar(value=50),  # 50% 透明度 (0-100)
            'shadow': tk.BooleanVar(value=False),
            'outline': tk.BooleanVar(value=False),
            'outline_color': tk.StringVar(value="#FFFFFF"),  # 白色描边
            'position': tk.StringVar(value="bottom-right")  # 位置
        }
        
        # 水印模板管理器
        self.template_manager = WatermarkTemplateManager(self)
        
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
        
        # 水印菜单
        watermark_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="水印", menu=watermark_menu)
        watermark_menu.add_command(label="水印设置", command=self.show_watermark_settings)
        
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
        
        # 创建可滚动的图像列表
        self.image_list_widget = ScrollableImageList(image_list_frame, self)
        self.image_list_widget.pack(fill=tk.BOTH, expand=True)
        
        # 控制面板按钮
        ttk.Button(control_frame, text="打开图像", command=self.open_image).pack(pady=5, fill=tk.X)
        ttk.Button(control_frame, text="批量导入", command=self.import_images).pack(pady=5, fill=tk.X)
        ttk.Button(control_frame, text="导入文件夹", command=self.import_folder).pack(pady=5, fill=tk.X)
        ttk.Button(control_frame, text="保存图像", command=self.save_image).pack(pady=5, fill=tk.X)
        ttk.Button(control_frame, text="重置图像", command=self.reset_image).pack(pady=5, fill=tk.X)
        ttk.Button(control_frame, text="水印设置", command=self.show_watermark_settings).pack(pady=5, fill=tk.X)
        
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
                    # 创建缩略图
                    thumbnail_photo = self.create_thumbnail(file_path)
                    # 为每个图像创建独立的水印设置
                    watermark_vars = {}
                    for key, var in self.default_watermark_vars.items():
                        if isinstance(var, tk.StringVar):
                            watermark_vars[key] = tk.StringVar(value=var.get())
                        elif isinstance(var, tk.BooleanVar):
                            watermark_vars[key] = tk.BooleanVar(value=var.get())
                        elif isinstance(var, tk.IntVar):
                            watermark_vars[key] = tk.IntVar(value=var.get())
                            
                    self.image_list.append({
                        'path': file_path,
                        'name': filename,
                        'thumbnail': thumbnail_photo,
                        'watermark_vars': watermark_vars
                    })
                    # 在图像列表中显示缩略图
                    self.image_list_widget.add_thumbnail(file_path, thumbnail_photo, filename)
                except Exception as e:
                    messagebox.showerror("错误", f"无法加载图像 {file_path}:\n{str(e)}")
        
        # 如果这是第一批图像，自动选择第一个
        if len(self.image_list) > 0 and self.current_image_index == -1:
            self.load_image(0)
    
    def create_thumbnail(self, file_path):
        """创建图像缩略图"""
        try:
            img = Image.open(file_path)
            img.thumbnail(self.thumbnail_size, Image.LANCZOS)
            # 创建透明背景
            thumbnail = Image.new('RGBA', self.thumbnail_size, (0, 0, 0, 0))
            # 计算居中位置
            x = (self.thumbnail_size[0] - img.size[0]) // 2
            y = (self.thumbnail_size[1] - img.size[1]) // 2
            # 将缩略图粘贴到透明背景上
            thumbnail.paste(img, (x, y))
            return ImageTk.PhotoImage(thumbnail)
        except Exception as e:
            # 如果创建缩略图失败，返回默认图像
            thumbnail = Image.new('RGBA', self.thumbnail_size, (128, 128, 128, 255))
            return ImageTk.PhotoImage(thumbnail)
    
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
                
                # 高亮显示当前选中的图像
                # 注意：在新的缩略图界面中，我们不需要特殊的高亮显示
            except Exception as e:
                messagebox.showerror("错误", f"无法打开图像文件:\n{str(e)}")
    
    def display_image_on_canvas(self):
        # 隐藏拖拽提示
        self.drop_label.pack_forget()
        
        if self.processed_image and self.current_image_index >= 0:
            # 应用水印（使用当前图像的水印设置）
            image_with_watermark = self.apply_watermark(self.processed_image)
            
            # 调整图像大小以适应显示区域
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            # 如果画布大小为1，说明还未正确初始化，使用默认大小
            if canvas_width <= 1:
                canvas_width = 600
            if canvas_height <= 1:
                canvas_height = 400
            
            img_width, img_height = image_with_watermark.size
            
            # 计算缩放比例
            scale_w = canvas_width / img_width
            scale_h = canvas_height / img_height
            scale = min(scale_w, scale_h, 1.0)  # 不放大图像
            
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            
            # 缩放图像
            resized_image = image_with_watermark.resize((new_width, new_height), Image.LANCZOS)
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
    
    def apply_watermark(self, image):
        """应用水印到图像"""
        if not image or self.current_image_index < 0:
            return image
            
        # 获取当前图像的水印设置
        current_image = self.image_list[self.current_image_index]
        if 'watermark_vars' not in current_image:
            return image
            
        watermark_vars = current_image['watermark_vars']
        
        # 获取水印设置
        text = watermark_vars['text'].get()
        if not text:
            return image
            
        # 创建水印图像
        watermark = Image.new('RGBA', image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(watermark)
        
        # 获取字体设置
        font_family = watermark_vars['font_family'].get()
        font_size = watermark_vars['font_size'].get()
        bold = watermark_vars['bold'].get()
        italic = watermark_vars['italic'].get()
        
        # 尝试加载字体
        font_obj = None
        try:
            # 在Windows上尝试加载系统字体
            if os.name == 'nt':  # Windows
                # 构造字体文件名
                font_filename = font_family.lower().replace(' ', '')
                # 根据粗体和斜体设置构造字体文件名
                if bold and italic:
                    font_path = f"C:/Windows/Fonts/{font_filename}bi.ttf"
                elif bold:
                    font_path = f"C:/Windows/Fonts/{font_filename}bd.ttf"  # bd instead of b
                elif italic:
                    font_path = f"C:/Windows/Fonts/{font_filename}i.ttf"
                else:
                    font_path = f"C:/Windows/Fonts/{font_filename}.ttf"
                    
                if not os.path.exists(font_path):
                    # 尝试其他可能的命名方式
                    if bold:
                        font_path = f"C:/Windows/Fonts/{font_filename}-bold.ttf"
                    if italic:
                        font_path = f"C:/Windows/Fonts/{font_filename}-italic.ttf"
                    if bold and italic:
                        font_path = f"C:/Windows/Fonts/{font_filename}-bolditalic.ttf"
                        
                if os.path.exists(font_path):
                    font_obj = ImageFont.truetype(font_path, font_size)
        except:
            pass
            
        # 如果上面的方法失败了，尝试使用 PIL 的默认字体处理方式
        if font_obj is None:
            try:
                # 尝试使用系统字体加载
                font_obj = ImageFont.truetype(font_family, font_size)
            except:
                try:
                    # 如果指定字体失败，尝试使用支持中文的默认字体
                    # 在Windows上尝试使用支持中文的字体
                    if os.name == 'nt':
                        chinese_fonts = [
                            "C:/Windows/Fonts/msyh.ttc",      # 微软雅黑
                            "C:/Windows/Fonts/simhei.ttf",    # 黑体
                            "C:/Windows/Fonts/simsun.ttc",    # 宋体
                            "C:/Windows/Fonts/msgothic.ttc"   # 微软正黑体
                        ]
                        
                        for font_path in chinese_fonts:
                            if os.path.exists(font_path):
                                try:
                                    font_obj = ImageFont.truetype(font_path, font_size)
                                    break
                                except:
                                    continue
                                
                    # 如果还是失败，使用默认字体
                    if font_obj is None:
                        font_obj = ImageFont.load_default()
                except:
                    font_obj = ImageFont.load_default()
            
        # 获取文本颜色和透明度
        color = watermark_vars['color'].get()
        # 将0-100的透明度转换为0-255
        opacity_percent = watermark_vars['opacity'].get()
        opacity = int(opacity_percent * 2.55)  # 转换为0-255范围
        
        # 解析颜色
        if color.startswith('#'):
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
        else:
            r, g, b = 0, 0, 0
            
        text_color = (r, g, b, opacity)
        
        # 获取文本尺寸
        bbox = draw.textbbox((0, 0), text, font=font_obj)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # 计算水印位置
        position = watermark_vars['position'].get()
        margin = 10
        
        if position == "top-left":
            x, y = margin, margin
        elif position == "top-right":
            x, y = image.size[0] - text_width - margin, margin
        elif position == "bottom-left":
            x, y = margin, image.size[1] - text_height - margin
        elif position == "bottom-right":
            x, y = image.size[0] - text_width - margin, image.size[1] - text_height - margin
        elif position == "center":
            x, y = (image.size[0] - text_width) // 2, (image.size[1] - text_height) // 2
        else:
            x, y = image.size[0] - text_width - margin, image.size[1] - text_height - margin
            
        # 绘制阴影
        if watermark_vars['shadow'].get():
            shadow_color = (0, 0, 0, opacity // 2)
            draw.text((x + 2, y + 2), text, font=font_obj, fill=shadow_color)
            
        # 绘制描边
        if watermark_vars['outline'].get():
            outline_color = watermark_vars['outline_color'].get()
            if outline_color.startswith('#'):
                or_val = int(outline_color[1:3], 16)
                og_val = int(outline_color[3:5], 16)
                ob_val = int(outline_color[5:7], 16)
            else:
                or_val, og_val, ob_val = 255, 255, 255
                
            outline_color_rgba = (or_val, og_val, ob_val, opacity)
            
            # 绘制描边（在文本周围绘制多个偏移的文本）
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx != 0 or dy != 0:
                        draw.text((x + dx, y + dy), text, font=font_obj, fill=outline_color_rgba)
        
        # 绘制主文本
        draw.text((x, y), text, font=font_obj, fill=text_color)
        
        # 将水印合并到图像上
        watermarked_image = Image.alpha_composite(image.convert('RGBA'), watermark)
        
        return watermarked_image.convert('RGB') if image.mode == 'RGB' else watermarked_image
    
    def show_watermark_settings(self):
        """显示水印设置对话框"""
        if self.current_image_index < 0:
            messagebox.showwarning("警告", "请先选择一张图像")
            return
            
        # 获取当前图像的水印设置
        current_image = self.image_list[self.current_image_index]
        if 'watermark_vars' not in current_image:
            # 如果当前图像没有水印设置，创建一个新的
            watermark_vars = {}
            for key, var in self.default_watermark_vars.items():
                if isinstance(var, tk.StringVar):
                    watermark_vars[key] = tk.StringVar(value=var.get())
                elif isinstance(var, tk.BooleanVar):
                    watermark_vars[key] = tk.BooleanVar(value=var.get())
                elif isinstance(var, tk.IntVar):
                    watermark_vars[key] = tk.IntVar(value=var.get())
            current_image['watermark_vars'] = watermark_vars
        else:
            watermark_vars = current_image['watermark_vars']
        
        # 创建水印设置窗口
        watermark_dialog = tk.Toplevel(self.root)
        watermark_dialog.title("水印设置")
        watermark_dialog.geometry("500x600")
        watermark_dialog.resizable(True, True)
        watermark_dialog.transient(self.root)
        watermark_dialog.grab_set()
        
        # 创建主框架
        main_frame = ttk.Frame(watermark_dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建canvas和scrollbar以支持滚动
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        # 配置滚动区域
        def on_frame_configure(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            
        scrollable_frame.bind("<Configure>", on_frame_configure)
        
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        def on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
            
        canvas.bind("<Configure>", on_canvas_configure)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 使用鼠标滚轮滚动
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            
        def _bind_to_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
            
        def _unbind_from_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")
            
        canvas.bind('<Enter>', _bind_to_mousewheel)
        canvas.bind('<Leave>', _unbind_from_mousewheel)
        
        # 水印文本设置
        text_frame = ttk.LabelFrame(scrollable_frame, text="水印文本", padding=10)
        text_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(text_frame, text="文本内容:").pack(anchor=tk.W)
        text_entry = ttk.Entry(text_frame, textvariable=watermark_vars['text'])
        text_entry.pack(fill=tk.X, pady=(0, 10))
        
        # 字体设置
        font_frame = ttk.LabelFrame(scrollable_frame, text="字体设置", padding=10)
        font_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 字体选择
        font_select_frame = ttk.Frame(font_frame)
        font_select_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(font_select_frame, text="字体:").pack(side=tk.LEFT)
        font_combo = ttk.Combobox(font_select_frame, textvariable=watermark_vars['font_family'], 
                                 values=SYSTEM_FONTS, state="readonly")
        font_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        # 字号
        size_frame = ttk.Frame(font_frame)
        size_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(size_frame, text="字号:").pack(side=tk.LEFT)
        size_spinbox = ttk.Spinbox(size_frame, from_=8, to=100, textvariable=watermark_vars['font_size'], 
                                  width=10, command=self.display_image_on_canvas)
        size_spinbox.pack(side=tk.LEFT, padx=(5, 0))
        
        # 字体样式
        style_frame = ttk.Frame(font_frame)
        style_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Checkbutton(style_frame, text="粗体", variable=watermark_vars['bold'], 
                       command=self.display_image_on_canvas).pack(side=tk.LEFT)
        ttk.Checkbutton(style_frame, text="斜体", variable=watermark_vars['italic'], 
                       command=self.display_image_on_canvas).pack(side=tk.LEFT, padx=(10, 0))
        
        # 颜色设置
        color_frame = ttk.LabelFrame(scrollable_frame, text="颜色设置", padding=10)
        color_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 文本颜色
        text_color_frame = ttk.Frame(color_frame)
        text_color_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(text_color_frame, text="文本颜色:").pack(side=tk.LEFT)
        
        def choose_text_color():
            color = colorchooser.askcolor(color=watermark_vars['color'].get(), title="选择文本颜色")
            if color[1]:  # 如果用户选择了颜色
                watermark_vars['color'].set(color[1])
                self.display_image_on_canvas()
                
        color_button = tk.Button(text_color_frame, text="选择颜色", command=choose_text_color)
        color_button.pack(side=tk.LEFT, padx=(5, 0))
        
        color_preview = tk.Label(text_color_frame, text="    ", bg=watermark_vars['color'].get(), 
                                relief="ridge", bd=1)
        color_preview.pack(side=tk.LEFT, padx=(5, 0))
        
        def update_text_color_preview(*args):
            color_preview.config(bg=watermark_vars['color'].get())
            
        watermark_vars['color'].trace('w', update_text_color_preview)
        
        # 透明度
        opacity_frame = ttk.Frame(color_frame)
        opacity_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(opacity_frame, text="透明度:").pack(side=tk.LEFT)
        # 透明度范围调整为0-100
        opacity_scale = ttk.Scale(opacity_frame, from_=0, to=100, variable=watermark_vars['opacity'], 
                                orient=tk.HORIZONTAL, command=lambda v: self.display_image_on_canvas())
        opacity_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5))
        
        # 显示整数透明度值
        opacity_value = tk.IntVar()
        opacity_value.set(watermark_vars['opacity'].get())
        
        def update_opacity_label(val):
            opacity_value.set(int(float(val)))
            
        opacity_scale.configure(command=update_opacity_label)
        opacity_label = ttk.Label(opacity_frame, textvariable=opacity_value)
        opacity_label.pack(side=tk.LEFT)
        
        # 更新透明度变量时同步标签
        def sync_opacity_label(*args):
            opacity_value.set(watermark_vars['opacity'].get())
            
        watermark_vars['opacity'].trace('w', sync_opacity_label)
        
        # 特效设置
        effect_frame = ttk.LabelFrame(scrollable_frame, text="特效设置", padding=10)
        effect_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 阴影
        ttk.Checkbutton(effect_frame, text="阴影", variable=watermark_vars['shadow'], 
                       command=self.display_image_on_canvas).pack(anchor=tk.W)
        
        # 描边
        outline_frame = ttk.Frame(effect_frame)
        outline_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Checkbutton(outline_frame, text="描边", variable=watermark_vars['outline'], 
                       command=self.display_image_on_canvas).pack(side=tk.LEFT)
        
        def choose_outline_color():
            color = colorchooser.askcolor(color=watermark_vars['outline_color'].get(), title="选择描边颜色")
            if color[1]:  # 如果用户选择了颜色
                watermark_vars['outline_color'].set(color[1])
                self.display_image_on_canvas()
                
        outline_color_button = tk.Button(outline_frame, text="描边颜色", command=choose_outline_color)
        outline_color_button.pack(side=tk.LEFT, padx=(10, 0))
        
        outline_color_preview = tk.Label(outline_frame, text="    ", bg=watermark_vars['outline_color'].get(), 
                                        relief="ridge", bd=1)
        outline_color_preview.pack(side=tk.LEFT, padx=(5, 0))
        
        def update_outline_color_preview(*args):
            outline_color_preview.config(bg=watermark_vars['outline_color'].get())
            
        watermark_vars['outline_color'].trace('w', update_outline_color_preview)
        
        # 位置设置
        position_frame = ttk.LabelFrame(scrollable_frame, text="位置设置", padding=10)
        position_frame.pack(fill=tk.X, padx=5, pady=5)
        
        position_var = watermark_vars['position']
        
        positions = [
            ("左上角", "top-left"),
            ("右上角", "top-right"),
            ("左下角", "bottom-left"),
            ("右下角", "bottom-right"),
            ("居中", "center")
        ]
        
        position_combo_frame = ttk.Frame(position_frame)
        position_combo_frame.pack(fill=tk.X)
        
        ttk.Label(position_combo_frame, text="位置:").pack(side=tk.LEFT)
        position_values = [p[0] for p in positions]
        position_keys = [p[1] for p in positions]
        
        def position_changed(event):
            selected = position_combo.get()
            for text, key in positions:
                if text == selected:
                    position_var.set(key)
                    self.display_image_on_canvas()
                    break
                    
        def update_position_combo(*args):
            current = position_var.get()
            for text, key in positions:
                if key == current:
                    position_combo.set(text)
                    break
                    
        position_combo = ttk.Combobox(position_combo_frame, values=position_values, state="readonly")
        position_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        position_combo.bind("<<ComboboxSelected>>", position_changed)
        
        # 初始化位置组合框
        update_position_combo()
        position_var.trace('w', update_position_combo)
        
        # 模板管理
        template_frame = ttk.LabelFrame(scrollable_frame, text="模板管理", padding=10)
        template_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 保存模板
        save_template_frame = ttk.Frame(template_frame)
        save_template_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(save_template_frame, text="模板名称:").pack(side=tk.LEFT)
        template_name_var = tk.StringVar()
        template_name_entry = ttk.Entry(save_template_frame, textvariable=template_name_var)
        template_name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5))
        
        def save_template():
            name = template_name_var.get().strip()
            if not name:
                messagebox.showwarning("警告", "请输入模板名称")
                return
                
            # 检查是否已存在同名模板
            if name in self.template_manager.get_template_names():
                result = messagebox.askyesno("确认", f"模板 '{name}' 已存在，是否覆盖？")
                if not result:
                    return
                    
            # 保存当前设置为模板
            settings = {}
            for key, var in watermark_vars.items():
                if isinstance(var, tk.StringVar):
                    settings[key] = var.get()
                elif isinstance(var, tk.BooleanVar):
                    settings[key] = var.get()
                elif isinstance(var, tk.IntVar):
                    settings[key] = var.get()
                    
            self.template_manager.add_template(name, settings)
            messagebox.showinfo("成功", f"模板 '{name}' 已保存")
            update_template_list()
            
        save_button = ttk.Button(save_template_frame, text="保存模板", command=save_template)
        save_button.pack(side=tk.LEFT)
        
        # 加载模板
        load_template_frame = ttk.Frame(template_frame)
        load_template_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(load_template_frame, text="选择模板:").pack(side=tk.LEFT)
        
        template_list_var = tk.StringVar()
        template_combo = ttk.Combobox(load_template_frame, textvariable=template_list_var, state="readonly")
        template_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5))
        
        def update_template_list():
            templates = self.template_manager.get_template_names()
            template_combo['values'] = templates
            if templates:
                template_combo.set(templates[0])
                
        update_template_list()
        
        def load_template():
            name = template_list_var.get()
            if not name:
                messagebox.showwarning("警告", "请选择一个模板")
                return
                
            settings = self.template_manager.get_template(name)
            if settings:
                for key, value in settings.items():
                    if key in watermark_vars:
                        var = watermark_vars[key]
                        if isinstance(var, tk.StringVar):
                            var.set(value)
                        elif isinstance(var, tk.BooleanVar):
                            var.set(value)
                        elif isinstance(var, tk.IntVar):
                            var.set(value)
                            
                self.display_image_on_canvas()
                messagebox.showinfo("成功", f"模板 '{name}' 已加载")
            else:
                messagebox.showerror("错误", f"无法加载模板 '{name}'")
                
        load_button = ttk.Button(load_template_frame, text="加载模板", command=load_template)
        load_button.pack(side=tk.LEFT)
        
        # 删除模板
        def delete_template():
            name = template_list_var.get()
            if not name:
                messagebox.showwarning("警告", "请选择一个模板")
                return
                
            result = messagebox.askyesno("确认", f"确定要删除模板 '{name}' 吗？")
            if result:
                self.template_manager.remove_template(name)
                update_template_list()
                messagebox.showinfo("成功", f"模板 '{name}' 已删除")
                
        delete_button = ttk.Button(template_frame, text="删除选中模板", command=delete_template)
        delete_button.pack(anchor=tk.W)
        
        # 将canvas和scrollbar添加到main_frame
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 按钮框架
        button_frame = ttk.Frame(watermark_dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        def apply_settings():
            self.display_image_on_canvas()
            watermark_dialog.destroy()
            
        ttk.Button(button_frame, text="确定", command=apply_settings).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="取消", command=watermark_dialog.destroy).pack(side=tk.RIGHT, padx=5)
        
        # 确保初始时正确设置滚动区域
        watermark_dialog.after(100, lambda: canvas.configure(scrollregion=canvas.bbox("all")))
        
        # 绑定文本变化事件，实时预览
        watermark_vars['text'].trace('w', lambda *args: self.display_image_on_canvas())
    
    def save_image(self):
        if self.processed_image:
            # 创建导出设置窗口
            export_dialog = tk.Toplevel(self.root)
            export_dialog.title("导出设置")
            export_dialog.geometry("400x600")
            export_dialog.resizable(True, True)  # 允许调整大小
            export_dialog.transient(self.root)
            export_dialog.grab_set()
            
            # 创建主框架
            main_frame = ttk.Frame(export_dialog)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # 创建canvas和scrollbar以支持滚动
            canvas = tk.Canvas(main_frame)
            scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)
            
            # 配置滚动区域
            def on_frame_configure(event=None):
                canvas.configure(scrollregion=canvas.bbox("all"))
                
            scrollable_frame.bind("<Configure>", on_frame_configure)
            
            canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            
            def on_canvas_configure(event):
                canvas.itemconfig(canvas_window, width=event.width)
                
            canvas.bind("<Configure>", on_canvas_configure)
            canvas.configure(yscrollcommand=scrollbar.set)
            
            # 使用鼠标滚轮滚动
            def _on_mousewheel(event):
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
                
            def _bind_to_mousewheel(event):
                canvas.bind_all("<MouseWheel>", _on_mousewheel)
                
            def _unbind_from_mousewheel(event):
                canvas.unbind_all("<MouseWheel>")
                
            canvas.bind('<Enter>', _bind_to_mousewheel)
            canvas.bind('<Leave>', _unbind_from_mousewheel)
            
            # 导出选项变量
            export_options = {
                'naming_rule': tk.StringVar(value='original'),  # original, prefix, suffix
                'prefix': tk.StringVar(value='wm_'),
                'suffix': tk.StringVar(value='_watermarked'),
                'jpeg_quality': tk.IntVar(value=95),
                'prevent_overwrite': tk.BooleanVar(value=True),
                'export_format': tk.StringVar(value='same'),  # same, jpeg, png
                'export_directory': tk.StringVar(),
                # 尺寸调整选项
                'resize_option': tk.StringVar(value='none'),  # none, pixels, percentage
                'resize_width': tk.StringVar(),
                'resize_height': tk.StringVar(),
                'resize_percentage': tk.StringVar(value='100')
            }
            
            # 命名规则框架
            naming_frame = ttk.LabelFrame(scrollable_frame, text="文件命名规则", padding=10)
            naming_frame.pack(fill=tk.X, padx=5, pady=5)
            
            # 命名规则选项
            ttk.Radiobutton(naming_frame, text="保留原文件名", 
                           variable=export_options['naming_rule'], value='original').pack(anchor=tk.W)
            
            prefix_frame = ttk.Frame(naming_frame)
            prefix_frame.pack(fill=tk.X, pady=2)
            ttk.Radiobutton(prefix_frame, text="添加前缀:", 
                           variable=export_options['naming_rule'], value='prefix').pack(side=tk.LEFT)
            ttk.Entry(prefix_frame, textvariable=export_options['prefix'], width=15).pack(side=tk.LEFT, padx=(5, 0))
            
            suffix_frame = ttk.Frame(naming_frame)
            suffix_frame.pack(fill=tk.X, pady=2)
            ttk.Radiobutton(suffix_frame, text="添加后缀:", 
                           variable=export_options['naming_rule'], value='suffix').pack(side=tk.LEFT)
            ttk.Entry(suffix_frame, textvariable=export_options['suffix'], width=15).pack(side=tk.LEFT, padx=(5, 0))
            
            # 导出格式选择
            format_frame = ttk.LabelFrame(scrollable_frame, text="导出格式", padding=10)
            format_frame.pack(fill=tk.X, padx=5, pady=5)
            
            # 获取当前图像的扩展名
            current_image = self.image_list[self.current_image_index]
            original_ext = os.path.splitext(current_image['name'])[1].lower()
            
            ttk.Radiobutton(format_frame, text=f"保持原格式 ({original_ext.upper()[1:]})", 
                           variable=export_options['export_format'], value='same').pack(anchor=tk.W)
            ttk.Radiobutton(format_frame, text="JPEG", 
                           variable=export_options['export_format'], value='jpeg').pack(anchor=tk.W)
            ttk.Radiobutton(format_frame, text="PNG", 
                           variable=export_options['export_format'], value='png').pack(anchor=tk.W)
            
            # JPEG质量设置（仅对JPEG格式有效）
            quality_frame = ttk.LabelFrame(scrollable_frame, text="JPEG质量设置", padding=10)
            # 注意：初始时不pack，由update_quality_visibility函数控制
            
            ttk.Label(quality_frame, text="质量:").pack(side=tk.LEFT)
            quality_scale = ttk.Scale(quality_frame, from_=1, to=100, 
                                     variable=export_options['jpeg_quality'], orient=tk.HORIZONTAL)
            quality_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            # 创建一个显示整数质量值的标签
            quality_value = tk.IntVar()
            quality_value.set(export_options['jpeg_quality'].get())
            
            # 当滑块值变化时更新显示
            def update_quality_label(val):
                quality_value.set(int(float(val)))
            
            quality_scale.configure(command=update_quality_label)
            quality_label = ttk.Label(quality_frame, textvariable=quality_value)
            quality_label.pack(side=tk.LEFT)
            
            # 尺寸调整选项
            resize_frame = ttk.LabelFrame(scrollable_frame, text="尺寸调整", padding=10)
            resize_frame.pack(fill=tk.X, padx=5, pady=5)
            
            # 尺寸调整选项
            ttk.Radiobutton(resize_frame, text="保持原尺寸", 
                           variable=export_options['resize_option'], value='none').pack(anchor=tk.W)
            
            # 按像素调整尺寸
            pixel_frame = ttk.Frame(resize_frame)
            pixel_frame.pack(fill=tk.X, pady=2)
            ttk.Radiobutton(pixel_frame, text="按像素调整:", 
                           variable=export_options['resize_option'], value='pixels').pack(side=tk.LEFT)
            
            pixel_inputs_frame = ttk.Frame(pixel_frame)
            pixel_inputs_frame.pack(side=tk.LEFT, padx=(10, 0))
            
            ttk.Label(pixel_inputs_frame, text="宽:").pack(side=tk.LEFT)
            width_entry = ttk.Entry(pixel_inputs_frame, textvariable=export_options['resize_width'], width=6)
            width_entry.pack(side=tk.LEFT, padx=(2, 5))
            
            ttk.Label(pixel_inputs_frame, text="高:").pack(side=tk.LEFT)
            height_entry = ttk.Entry(pixel_inputs_frame, textvariable=export_options['resize_height'], width=6)
            height_entry.pack(side=tk.LEFT, padx=(2, 0))
            
            # 按百分比调整尺寸
            percent_frame = ttk.Frame(resize_frame)
            percent_frame.pack(fill=tk.X, pady=2)
            ttk.Radiobutton(percent_frame, text="按百分比调整:", 
                           variable=export_options['resize_option'], value='percentage').pack(side=tk.LEFT)
            
            percent_input_frame = ttk.Frame(percent_frame)
            percent_input_frame.pack(side=tk.LEFT, padx=(10, 0))
            
            percent_entry = ttk.Entry(percent_input_frame, textvariable=export_options['resize_percentage'], width=6)
            percent_entry.pack(side=tk.LEFT, padx=(2, 5))
            ttk.Label(percent_input_frame, text="%").pack(side=tk.LEFT)
            
            # 导出目录和覆盖保护
            dir_frame = ttk.LabelFrame(scrollable_frame, text="导出设置", padding=10)
            dir_frame.pack(fill=tk.X, padx=5, pady=5)
            
            ttk.Checkbutton(dir_frame, text="防止覆盖原文件（默认导出到新文件夹）", 
                           variable=export_options['prevent_overwrite']).pack(anchor=tk.W, pady=(0, 5))
            
            # 函数用于根据导出格式显示或隐藏JPEG质量设置
            def update_quality_visibility(*args):
                if export_options['export_format'].get() == 'jpeg':
                    # JPEG格式始终显示质量设置
                    quality_frame.pack(fill=tk.X, padx=5, pady=5)
                elif export_options['export_format'].get() == 'same':
                    # 检查原格式是否为JPEG
                    if original_ext in ['.jpg', '.jpeg']:
                        quality_frame.pack(fill=tk.X, padx=5, pady=5)
                    else:
                        quality_frame.pack_forget()
                else:
                    # PNG等其他格式不显示质量设置
                    quality_frame.pack_forget()
                
                # 更新滚动区域
                export_dialog.update_idletasks()
                canvas.configure(scrollregion=canvas.bbox("all"))
            
            # 绑定导出格式变化事件
            export_options['export_format'].trace('w', update_quality_visibility)
            
            # 初始调用以设置正确的可见性
            update_quality_visibility()
            
            # 自定义导出目录（放在最后）
            custom_dir_frame = ttk.LabelFrame(scrollable_frame, text="自定义导出目录", padding=10)
            custom_dir_frame.pack(fill=tk.X, padx=5, pady=5)
            
            ttk.Label(custom_dir_frame, text="导出目录:").pack(anchor=tk.W)
            
            dir_entry_frame = ttk.Frame(custom_dir_frame)
            dir_entry_frame.pack(fill=tk.X, pady=2)
            
            ttk.Entry(dir_entry_frame, textvariable=export_options['export_directory'], 
                     state='readonly').pack(side=tk.LEFT, fill=tk.X, expand=True)
            ttk.Button(dir_entry_frame, text="浏览...", 
                      command=lambda: self.select_export_directory(export_options['export_directory'])).pack(side=tk.RIGHT, padx=(5, 0))
            
            # 将canvas和scrollbar添加到main_frame
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            # 导出按钮框架
            button_frame = ttk.Frame(export_dialog)
            button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
            
            def do_export():
                try:
                    # 获取当前图像的目录和文件名
                    current_image = self.image_list[self.current_image_index]
                    original_dir = os.path.dirname(current_image['path'])
                    original_name = os.path.splitext(current_image['name'])[0]
                    
                    # 根据命名规则确定文件名
                    naming_rule = export_options['naming_rule'].get()
                    if naming_rule == 'original':
                        new_name = original_name
                    elif naming_rule == 'prefix':
                        new_name = export_options['prefix'].get() + original_name
                    else:  # suffix
                        new_name = original_name + export_options['suffix'].get()
                    
                    # 确定导出格式和扩展名
                    export_format = export_options['export_format'].get()
                    if export_format == 'same':
                        ext = os.path.splitext(current_image['name'])[1]
                    elif export_format == 'jpeg':
                        ext = '.jpg'
                    else:  # png
                        ext = '.png'
                    
                    # 确定导出目录
                    custom_dir = export_options['export_directory'].get()
                    if custom_dir and os.path.isdir(custom_dir):
                        # 使用自定义目录
                        export_dir = custom_dir
                    elif export_options['prevent_overwrite'].get():
                        # 默认导出到原目录下的export子目录
                        export_dir = os.path.join(original_dir, 'export')
                        os.makedirs(export_dir, exist_ok=True)
                    else:
                        export_dir = original_dir
                    
                    # 构造完整路径
                    export_path = os.path.join(export_dir, new_name + ext)
                    
                    # 处理JPEG质量和其他保存参数
                    save_kwargs = {}
                    if ext.lower() in ['.jpg', '.jpeg']:
                        save_kwargs['quality'] = export_options['jpeg_quality'].get()
                        save_kwargs['optimize'] = True
                    
                    # 保存图像
                    # 检查是否需要转换图像模式（JPEG不支持RGBA模式）
                    image_to_save = self.processed_image
                    
                    # 处理尺寸调整
                    resize_option = export_options['resize_option'].get()
                    if resize_option == 'pixels':
                        try:
                            width = int(export_options['resize_width'].get())
                            height = int(export_options['resize_height'].get())
                            if width > 0 and height > 0:
                                image_to_save = image_to_save.resize((width, height), Image.LANCZOS)
                        except ValueError:
                            pass  # 如果输入无效，保持原尺寸
                    elif resize_option == 'percentage':
                        try:
                            percentage = float(export_options['resize_percentage'].get())
                            if percentage > 0:
                                width, height = image_to_save.size
                                new_width = int(width * percentage / 100)
                                new_height = int(height * percentage / 100)
                                image_to_save = image_to_save.resize((new_width, new_height), Image.LANCZOS)
                        except ValueError:
                            pass  # 如果输入无效，保持原尺寸
                    
                    # 应用水印（使用当前图像的水印设置）
                    image_to_save = self.apply_watermark(image_to_save)
                    
                    if ext.lower() in ['.jpg', '.jpeg'] and image_to_save.mode in ('RGBA', 'LA', 'P'):
                        # 创建白色背景
                        if image_to_save.mode == 'P':
                            image_to_save = image_to_save.convert('RGBA')
                        
                        # 创建白色背景图像
                        background = Image.new('RGB', image_to_save.size, (255, 255, 255))
                        if image_to_save.mode == 'RGBA':
                            background.paste(image_to_save, mask=image_to_save.split()[-1])  # 使用alpha通道作为掩码
                        else:
                            background.paste(image_to_save)
                        image_to_save = background
                    
                    image_to_save.save(export_path, **save_kwargs)
                    messagebox.showinfo("成功", f"图像已保存到:\n{export_path}")
                    export_dialog.destroy()
                except Exception as e:
                    messagebox.showerror("错误", f"保存图像时出错:\n{str(e)}")
            
            def save_as():
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
                        # 处理JPEG质量
                        save_kwargs = {}
                        if file_path.lower().endswith(('.jpg', '.jpeg')):
                            save_kwargs['quality'] = export_options['jpeg_quality'].get()
                            save_kwargs['optimize'] = True
                        
                        # 检查是否需要转换图像模式（JPEG不支持RGBA模式）
                        image_to_save = self.processed_image
                        
                        # 处理尺寸调整
                        resize_option = export_options['resize_option'].get()
                        if resize_option == 'pixels':
                            try:
                                width = int(export_options['resize_width'].get())
                                height = int(export_options['resize_height'].get())
                                if width > 0 and height > 0:
                                    image_to_save = image_to_save.resize((width, height), Image.LANCZOS)
                            except ValueError:
                                pass  # 如果输入无效，保持原尺寸
                        elif resize_option == 'percentage':
                            try:
                                percentage = float(export_options['resize_percentage'].get())
                                if percentage > 0:
                                    width, height = image_to_save.size
                                    new_width = int(width * percentage / 100)
                                    new_height = int(height * percentage / 100)
                                    image_to_save = image_to_save.resize((new_width, new_height), Image.LANCZOS)
                            except ValueError:
                                pass  # 如果输入无效，保持原尺寸
                        
                        # 应用水印（使用当前图像的水印设置）
                        image_to_save = self.apply_watermark(image_to_save)
                        
                        if file_path.lower().endswith(('.jpg', '.jpeg')) and image_to_save.mode in ('RGBA', 'LA', 'P'):
                            # 创建白色背景
                            if image_to_save.mode == 'P':
                                image_to_save = image_to_save.convert('RGBA')
                            
                            # 创建白色背景图像
                            background = Image.new('RGB', image_to_save.size, (255, 255, 255))
                            if image_to_save.mode == 'RGBA':
                                background.paste(image_to_save, mask=image_to_save.split()[-1])  # 使用alpha通道作为掩码
                            else:
                                background.paste(image_to_save)
                            image_to_save = background
                        
                        image_to_save.save(file_path, **save_kwargs)
                        messagebox.showinfo("成功", f"图像已保存到:\n{file_path}")
                        export_dialog.destroy()
                    except Exception as e:
                        messagebox.showerror("错误", f"保存图像时出错:\n{str(e)}")
            
            ttk.Button(button_frame, text="导出", command=do_export).pack(side=tk.RIGHT, padx=5)
            ttk.Button(button_frame, text="另存为...", command=save_as).pack(side=tk.RIGHT, padx=5)
            ttk.Button(button_frame, text="取消", command=export_dialog.destroy).pack(side=tk.RIGHT, padx=5)
            
            # 确保初始时正确设置滚动区域
            export_dialog.after(100, lambda: canvas.configure(scrollregion=canvas.bbox("all")))
            
        else:
            messagebox.showwarning("警告", "没有可保存的图像")
    
    def select_export_directory(self, directory_var):
        """选择导出目录"""
        directory = filedialog.askdirectory(title="选择导出目录")
        if directory:
            directory_var.set(directory)
    
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