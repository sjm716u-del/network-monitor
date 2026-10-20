#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网络监测器 - Network Monitor
实时网速监控，支持按程序显示网络流量，波浪形图表
"""

import tkinter as tk
from tkinter import ttk
import psutil
import time
import threading
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from collections import deque, defaultdict

# ─── 颜色主题 ───
BG_COLOR = "#1a1a2e"
CARD_COLOR = "#16213e"
TEXT_COLOR = "#e0e0e0"
ACCENT_COLOR = "#0f3460"
DOWNLOAD_COLOR = "#00d2ff"
UPLOAD_COLOR = "#ff6b6b"
GRID_COLOR = "#2a2a4a"
HEADER_COLOR = "#e94560"
BTN_COLOR = "#0f3460"
BTN_HOVER = "#1a4a8a"


def format_speed(bytes_per_sec):
    if bytes_per_sec < 1024:
        return f"{bytes_per_sec:.0f} B/s"
    elif bytes_per_sec < 1024 ** 2:
        return f"{bytes_per_sec / 1024:.1f} KB/s"
    elif bytes_per_sec < 1024 ** 3:
        return f"{bytes_per_sec / 1024 ** 2:.2f} MB/s"
    else:
        return f"{bytes_per_sec / 1024 ** 3:.2f} GB/s"


def format_bytes(total_bytes):
    if total_bytes < 1024:
        return f"{total_bytes:.0f} B"
    elif total_bytes < 1024 ** 2:
        return f"{total_bytes / 1024:.1f} KB"
    elif total_bytes < 1024 ** 3:
        return f"{total_bytes / 1024 ** 2:.1f} MB"
    else:
        return f"{total_bytes / 1024 ** 3:.2f} GB"


class NetworkMonitor:
    def __init__(self, root):
        self.root = root
        self.root.title("网络监测器 - Network Monitor")
        self.root.geometry("960x750")
        self.root.configure(bg=BG_COLOR)
        self.root.minsize(800, 600)

        self.max_points = 120
        self.download_history = deque([0] * self.max_points, maxlen=self.max_points)
        self.upload_history = deque([0] * self.max_points, maxlen=self.max_points)

        self.last_net = psutil.net_io_counters()
        self.last_time = time.time()
        self.last_total_down = self.last_net.bytes_recv
        self.last_total_up = self.last_net.bytes_sent

        # 按程序统计
        self.process_net = defaultdict(lambda: {"name": "", "recv": 0, "sent": 0, "recv_delta": 0, "sent_delta": 0})

        self.peak_down = 0
        self.peak_up = 0

        self._build_ui()
        self._start_update()

    def _build_ui(self):
        # ── 标题栏 ──
        header = tk.Frame(self.root, bg=HEADER_COLOR, height=50)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text="🌐 网络监测器", font=("Microsoft YaHei", 16, "bold"),
                 bg=HEADER_COLOR, fg="white").pack(side=tk.LEFT, padx=15, pady=10)
        self.status_label = tk.Label(header, text="● 监控中", font=("Microsoft YaHei", 10),
                                     bg=HEADER_COLOR, fg="#00ff88")
        self.status_label.pack(side=tk.RIGHT, padx=15, pady=10)

        # ── 主内容区 ──
        main_frame = tk.Frame(self.root, bg=BG_COLOR)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # ── 顶部速度卡片 ──
        cards_frame = tk.Frame(main_frame, bg=BG_COLOR)
        cards_frame.pack(fill=tk.X, pady=(0, 10))

        # 下载卡片
        self.down_card = tk.Frame(cards_frame, bg=CARD_COLOR, padx=20, pady=15,
                                  highlightbackground=DOWNLOAD_COLOR, highlightthickness=2)
        self.down_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        tk.Label(self.down_card, text="⬇ 下载速度", font=("Microsoft YaHei", 11),
                 bg=CARD_COLOR, fg=DOWNLOAD_COLOR).pack(anchor=tk.W)
        self.down_speed_label = tk.Label(self.down_card, text="0 B/s",
                                         font=("Microsoft YaHei", 28, "bold"),
                                         bg=CARD_COLOR, fg="white")
        self.down_speed_label.pack(anchor=tk.W)
        self.down_total_label = tk.Label(self.down_card, text="总计: 0 B",
                                         font=("Microsoft YaHei", 9),
                                         bg=CARD_COLOR, fg="#888888")
        self.down_total_label.pack(anchor=tk.W)
        self.down_peak_label = tk.Label(self.down_card, text="峰值: 0 B/s",
                                        font=("Microsoft YaHei", 9),
                                        bg=CARD_COLOR, fg="#888888")
        self.down_peak_label.pack(anchor=tk.W)

        # 上传卡片
        self.up_card = tk.Frame(cards_frame, bg=CARD_COLOR, padx=20, pady=15,
                                highlightbackground=UPLOAD_COLOR, highlightthickness=2)
        self.up_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        tk.Label(self.up_card, text="⬆ 上传速度", font=("Microsoft YaHei", 11),
                 bg=CARD_COLOR, fg=UPLOAD_COLOR).pack(anchor=tk.W)
        self.up_speed_label = tk.Label(self.up_card, text="0 B/s",
                                       font=("Microsoft YaHei", 28, "bold"),
                                       bg=CARD_COLOR, fg="white")
        self.up_speed_label.pack(anchor=tk.W)
        self.up_total_label = tk.Label(self.up_card, text="总计: 0 B",
                                       font=("Microsoft YaHei", 9),
                                       bg=CARD_COLOR, fg="#888888")
        self.up_total_label.pack(anchor=tk.W)
        self.up_peak_label = tk.Label(self.up_card, text="峰值: 0 B/s",
                                      font=("Microsoft YaHei", 9),
                                      bg=CARD_COLOR, fg="#888888")
        self.up_peak_label.pack(anchor=tk.W)

        # ── 波浪形图表 ──
        chart_frame = tk.Frame(main_frame, bg=CARD_COLOR,
                               highlightbackground=ACCENT_COLOR, highlightthickness=1)
        chart_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # 图表标题栏 + 刷新按钮
        chart_header = tk.Frame(chart_frame, bg=CARD_COLOR)
        chart_header.pack(fill=tk.X, padx=10, pady=(8, 0))
        tk.Label(chart_header, text="📈 实时网速曲线", font=("Microsoft YaHei", 11, "bold"),
                 bg=CARD_COLOR, fg=TEXT_COLOR).pack(side=tk.LEFT)

        # 刷新按钮
        self.refresh_btn = tk.Button(
            chart_header, text="🔄 刷新图表", font=("Microsoft YaHei", 9),
            bg=BTN_COLOR, fg="white", activebackground=BTN_HOVER, activeforeground="white",
            relief=tk.FLAT, padx=12, pady=4, cursor="hand2",
            command=self._reset_chart
        )
        self.refresh_btn.pack(side=tk.RIGHT)
        self.refresh_btn.bind("<Enter>", lambda e: self.refresh_btn.config(bg=BTN_HOVER))
        self.refresh_btn.bind("<Leave>", lambda e: self.refresh_btn.config(bg=BTN_COLOR))

        # 图表
        self.fig = Figure(figsize=(9, 3.2), dpi=100, facecolor=CARD_COLOR)
        self.ax = self.fig.add_subplot(111)
        self._setup_chart()

        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # ── 底部：程序网络列表 ──
        bottom_frame = tk.Frame(main_frame, bg=CARD_COLOR,
                                highlightbackground=ACCENT_COLOR, highlightthickness=1)
        bottom_frame.pack(fill=tk.BOTH, expand=True)

        bottom_header = tk.Frame(bottom_frame, bg=CARD_COLOR)
        bottom_header.pack(fill=tk.X, padx=10, pady=(8, 4))
        tk.Label(bottom_header, text="📊 各程序网络流量", font=("Microsoft YaHei", 12, "bold"),
                 bg=CARD_COLOR, fg=TEXT_COLOR).pack(side=tk.LEFT)

        # 刷新列表按钮
        self.refresh_list_btn = tk.Button(
            bottom_header, text="🔄 刷新列表", font=("Microsoft YaHei", 9),
            bg=BTN_COLOR, fg="white", activebackground=BTN_HOVER, activeforeground="white",
            relief=tk.FLAT, padx=12, pady=3, cursor="hand2",
            command=self._refresh_process_list
        )
        self.refresh_list_btn.pack(side=tk.RIGHT)
        self.refresh_list_btn.bind("<Enter>", lambda e: self.refresh_list_btn.config(bg=BTN_HOVER))
        self.refresh_list_btn.bind("<Leave>", lambda e: self.refresh_list_btn.config(bg=BTN_COLOR))

        tree_frame = tk.Frame(bottom_frame, bg=CARD_COLOR)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Custom.Treeview",
                         background=CARD_COLOR, foreground=TEXT_COLOR,
                         fieldbackground=CARD_COLOR, rowheight=28,
                         font=("Microsoft YaHei", 10))
        style.configure("Custom.Treeview.Heading",
                         background=ACCENT_COLOR, foreground="white",
                         font=("Microsoft YaHei", 10, "bold"))
        style.map("Custom.Treeview",
                   background=[("selected", ACCENT_COLOR)],
                   foreground=[("selected", "white")])

        self.tree = ttk.Treeview(tree_frame,
                                  columns=("pid", "name", "download", "upload", "down_speed", "up_speed"),
                                  show="headings", style="Custom.Treeview")
        self.tree.heading("pid", text="PID")
        self.tree.heading("name", text="程序名称")
        self.tree.heading("download", text="总下载")
        self.tree.heading("upload", text="总上传")
        self.tree.heading("down_speed", text="下载速度")
        self.tree.heading("up_speed", text="上传速度")

        self.tree.column("pid", width=60, anchor=tk.CENTER)
        self.tree.column("name", width=200, anchor=tk.W)
        self.tree.column("download", width=120, anchor=tk.E)
        self.tree.column("upload", width=120, anchor=tk.E)
        self.tree.column("down_speed", width=120, anchor=tk.E)
        self.tree.column("up_speed", width=120, anchor=tk.E)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _setup_chart(self):
        self.ax.clear()
        self.ax.set_facecolor(CARD_COLOR)
        self.ax.set_xlim(0, self.max_points)
        self.ax.set_ylim(0, 1)
        self.ax.set_yticks([])
        self.ax.set_xticks([0, 30, 60, 90, 120])
        self.ax.set_xticklabels(["-120s", "-90s", "-60s", "-30s", "现在"],
                                 color="#888888", fontsize=8)
        self.ax.grid(True, color=GRID_COLOR, linestyle="--", alpha=0.5)

        x = list(range(self.max_points))
        self.down_line, = self.ax.plot(x, [0] * self.max_points, color=DOWNLOAD_COLOR,
                                        linewidth=2, label="下载")
        self.up_line, = self.ax.plot(x, [0] * self.max_points, color=UPLOAD_COLOR,
                                      linewidth=2, label="上传")
        self.ax.fill_between(x, 0, [0] * self.max_points, color=DOWNLOAD_COLOR, alpha=0.12)
        self.ax.fill_between(x, 0, [0] * self.max_points, color=UPLOAD_COLOR, alpha=0.12)

        self.ax.legend(loc="upper left", fontsize=9, facecolor=CARD_COLOR,
                        edgecolor=ACCENT_COLOR, labelcolor=TEXT_COLOR)

    def _reset_chart(self):
        """刷新/重置图表 - 清空历史数据"""
        self.download_history.clear()
        self.upload_history.clear()
        for _ in range(self.max_points):
            self.download_history.append(0)
            self.upload_history.append(0)
        self.peak_down = 0
        self.peak_up = 0
        self._setup_chart()
        self.canvas.draw_idle()

    def _refresh_process_list(self):
        """手动刷新程序列表"""
        self._update_process_list()

    def _get_process_network(self):
        """获取各进程的网络连接数"""
        pid_conns = defaultdict(int)
        pid_names = {}

        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    pid = proc.info['pid']
                    name = proc.info['name'] or "Unknown"
                    pid_names[pid] = name
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue

            for conn in psutil.net_connections(kind='inet'):
                if conn.pid:
                    pid_conns[conn.pid] += 1
        except Exception:
            pass

        return pid_conns, pid_names

    def _update_data(self):
        """后台线程更新数据"""
        while True:
            try:
                now = time.time()
                current_net = psutil.net_io_counters()
                dt = now - self.last_time

                if dt > 0:
                    down_speed = max(0, (current_net.bytes_recv - self.last_net.bytes_recv) / dt)
                    up_speed = max(0, (current_net.bytes_sent - self.last_net.bytes_sent) / dt)
                else:
                    down_speed = 0
                    up_speed = 0

                self.download_history.append(down_speed)
                self.upload_history.append(up_speed)

                self.last_total_down = current_net.bytes_recv
                self.last_total_up = current_net.bytes_sent

                if down_speed > self.peak_down:
                    self.peak_down = down_speed
                if up_speed > self.peak_up:
                    self.peak_up = up_speed

                # 按进程连接数分配流量
                current_pid_conns, pid_names = self._get_process_network()
                total_conns = sum(current_pid_conns.values())

                if total_conns > 0:
                    for pid, conn_count in current_pid_conns.items():
                        name = pid_names.get(pid, f"PID:{pid}")
                        ratio = conn_count / total_conns

                        data = self.process_net[name]
                        data["name"] = name
                        data["recv"] += down_speed * dt * ratio
                        data["sent"] += up_speed * dt * ratio
                        data["recv_delta"] = down_speed * ratio
                        data["sent_delta"] = up_speed * ratio
                        self.process_net[name] = data

                self.last_net = current_net
                self.last_time = now

            except Exception:
                pass

            time.sleep(1)

    def _update_ui(self):
        """主线程更新UI"""
        try:
            if len(self.download_history) == 0:
                return

            down_speed = self.download_history[-1]
            up_speed = self.upload_history[-1]

            self.down_speed_label.config(text=format_speed(down_speed))
            self.up_speed_label.config(text=format_speed(up_speed))
            self.down_total_label.config(text=f"总计: ↓ {format_bytes(self.last_total_down)}")
            self.up_total_label.config(text=f"总计: ↑ {format_bytes(self.last_total_up)}")
            self.down_peak_label.config(text=f"峰值: {format_speed(self.peak_down)}")
            self.up_peak_label.config(text=f"峰值: {format_speed(self.peak_up)}")

            # 更新图表
            max_val = max(max(self.download_history), max(self.upload_history), 1024)
            self.ax.set_ylim(0, max_val * 1.2)

            x = list(range(self.max_points))
            down_data = list(self.download_history)
            up_data = list(self.upload_history)

            self.down_line.set_ydata(down_data)
            self.up_line.set_ydata(up_data)

            self.ax.collections.clear()
            self.ax.fill_between(x, 0, down_data, color=DOWNLOAD_COLOR, alpha=0.12)
            self.ax.fill_between(x, 0, up_data, color=UPLOAD_COLOR, alpha=0.12)

            self.canvas.draw_idle()

            # 更新程序列表
            self._update_process_list()

        except Exception:
            pass

        self.root.after(1000, self._update_ui)

    def _update_process_list(self):
        """更新程序网络列表"""
        for item in self.tree.get_children():
            self.tree.delete(item)

        sorted_procs = sorted(self.process_net.items(),
                               key=lambda x: x[1].get("recv", 0) + x[1].get("sent", 0),
                               reverse=True)

        for name, data in sorted_procs[:20]:
            if data.get("recv", 0) > 0 or data.get("sent", 0) > 0:
                self.tree.insert("", tk.END, values=(
                    "",
                    name,
                    format_bytes(data.get("recv", 0)),
                    format_bytes(data.get("sent", 0)),
                    format_speed(data.get("recv_delta", 0)),
                    format_speed(data.get("sent_delta", 0))
                ))

    def _start_update(self):
        t = threading.Thread(target=self._update_data, daemon=True)
        t.start()
        self.root.after(1000, self._update_ui)


def main():
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    app = NetworkMonitor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
