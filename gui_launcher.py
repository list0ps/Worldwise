import tkinter as tk
from tkinter import scrolledtext
import threading
import subprocess
import time
import os
import sys
from datetime import datetime
from pystray import Icon, MenuItem, Menu
from PIL import Image, ImageTk
import psutil

def resource_path(filename):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, filename)
    return os.path.join(os.path.abspath("."), filename)

BOT_NAME = "Worldwise"
SCRIPT_NAME = "Worldwise-executable.py"
LOGO_PATH = resource_path("logo.png")
VENV_PYTHON = os.path.join(os.getcwd(), "venv", "Scripts", "python.exe")

class BotGUI:
    def __init__(self, root):
        self.root = root
        self.root.overrideredirect(True)

        # Dynamic positioning: slightly left of center
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = 600
        window_height = 720
        x_offset = int((screen_width - window_width) * 0.4)
        y_offset = int((screen_height - window_height) / 2)

        self.root.geometry(f"{window_width}x{window_height}+{x_offset}+{y_offset}")
        self.root.configure(bg="#2c2f33")
        self.root.resizable(False, False)

        self.start_time = None
        self.bot_process = None
        self.psutil_proc = None

        self.build_custom_titlebar()
        self.build_gui()
        self.create_tray_icon()
        self.update_uptime()
        self.update_resource_usage()
        self.root.bind("<Escape>", lambda e: self.exit_app())  # ESC = quick exit

    def build_custom_titlebar(self):
        self.titlebar = tk.Frame(self.root, bg="#23272a", height=32)
        self.titlebar.pack(fill=tk.X, side=tk.TOP)
        self.titlebar.bind("<ButtonPress-1>", self.start_move)
        self.titlebar.bind("<B1-Motion>", self.move_window)

        title = tk.Label(self.titlebar, text=f"{BOT_NAME} Control Panel", bg="#23272a", fg="white", font=("Segoe UI", 10))
        title.pack(side=tk.LEFT, padx=10)

        self.min_btn = tk.Button(self.titlebar, text='🗕', command=self.minimize_window, bg="#23272a", fg="#7289da", bd=0)
        self.min_btn.pack(side=tk.RIGHT, padx=5)

        self.exit_btn = tk.Button(self.titlebar, text='⨉', command=self.exit_app, bg="#23272a", fg="#f04747", bd=0)
        self.exit_btn.pack(side=tk.RIGHT)

    def build_gui(self):
        try:
            image = Image.open(LOGO_PATH).resize((100, 100))
            self.logo_image = ImageTk.PhotoImage(image)
            logo_label = tk.Label(self.root, image=self.logo_image, bg="#2c2f33")
            logo_label.pack(pady=10)
        except:
            pass

        tk.Label(self.root, text=BOT_NAME, font=("Segoe UI", 16), fg="white", bg="#2c2f33").pack()

        self.status_var = tk.StringVar(value="Status: Not Running")
        self.status_label = tk.Label(self.root, textvariable=self.status_var, font=("Segoe UI", 10), fg="red", bg="#2c2f33")
        self.status_label.pack()

        self.uptime_label = tk.Label(self.root, text="Uptime: --:--:--", font=("Segoe UI", 22), fg="#43b581", bg="#2c2f33")
        self.uptime_label.pack(pady=10)

        self.resource_label = tk.Label(self.root, text="CPU: --%   RAM: -- MB", font=("Segoe UI", 10), fg="white", bg="#2c2f33")
        self.resource_label.pack()

        self.log_box = scrolledtext.ScrolledText(self.root, width=70, height=20, state='disabled', bg="#23272a", fg="white", insertbackground="white")
        self.log_box.pack(padx=10, pady=10)

        btn_style = {
            "width": 16,
            "bg": "#2f4a66",
            "fg": "white",
            "font": ("Segoe UI", 10)
        }

        btn_frame = tk.Frame(self.root, bg="#2c2f33")
        btn_frame.pack()

        self.start_btn = tk.Button(btn_frame, text="Start Bot", command=self.start_bot, **btn_style)
        self.start_btn.grid(row=0, column=0, padx=5)

        self.stop_btn = tk.Button(btn_frame, text="Stop Bot", command=self.stop_bot, state='disabled', **btn_style)
        self.stop_btn.grid(row=0, column=1, padx=5)

        self.restart_btn = tk.Button(btn_frame, text="Restart Bot", command=self.restart_bot, state='disabled', **btn_style)
        self.restart_btn.grid(row=0, column=2, padx=5)

        edit_frame = tk.Frame(self.root, bg="#2c2f33")
        edit_frame.pack(pady=(15, 10))

        tk.Button(edit_frame, text="Edit Descriptions", command=lambda: self.edit_json_file("user_descriptions.json", "Edit Descriptions"), **btn_style).pack(side=tk.LEFT, padx=10)
        tk.Button(edit_frame, text="Edit Timezones", command=lambda: self.edit_json_file("data_mappings.py", "Edit Timezones"), **btn_style).pack(side=tk.LEFT, padx=10)
        tk.Button(edit_frame, text="Open Chat Logs", command=self.open_chat_logs, **btn_style).pack(side=tk.LEFT, padx=10)

    def start_move(self, event):
        self.x_offset = event.x
        self.y_offset = event.y

    def move_window(self, event):
        self.root.geometry(f'+{event.x_root - self.x_offset}+{event.y_root - self.y_offset}')

    def minimize_window(self):
        self.root.withdraw()

    def exit_app(self):
        if self.bot_process and self.bot_process.poll() is None:
            self.bot_process.terminate()
        if hasattr(self, "tray_icon"):
            self.tray_icon.stop()
        self.root.destroy()

    def append_log(self, message):
        self.log_box.config(state='normal')
        self.log_box.insert(tk.END, message)
        self.log_box.see(tk.END)
        self.log_box.config(state='disabled')

    def read_log_output(self):
        for line in iter(self.bot_process.stdout.readline, ''):
            self.append_log(line)
        self.bot_process.stdout.close()

    def start_bot(self):
        if self.bot_process and self.bot_process.poll() is None:
            return
        try:
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            self.bot_process = subprocess.Popen(
                [VENV_PYTHON, SCRIPT_NAME],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                creationflags=creationflags
            )
            self.psutil_proc = psutil.Process(self.bot_process.pid)
            self.start_time = datetime.now()
            self.status_var.set("Status: Running")
            self.status_label.config(fg="#43b581")
            self.start_btn.config(state='disabled')
            self.stop_btn.config(state='normal')
            self.restart_btn.config(state='normal')
            threading.Thread(target=self.read_log_output, daemon=True).start()
        except Exception as e:
            self.append_log(f"[ERROR] Failed to start bot: {e}\n")

    def stop_bot(self):
        if self.bot_process and self.bot_process.poll() is None:
            try:
                self.psutil_proc.terminate()
                self.psutil_proc.wait(timeout=3)
            except Exception as e:
                self.append_log(f"[ERROR] Failed to terminate bot: {e}\n")
        self.status_var.set("Status: Stopped")
        self.status_label.config(fg="red")
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.restart_btn.config(state='disabled')
        self.append_log("[INFO] Bot stopped.\n")

    def restart_bot(self):
        self.stop_bot()
        time.sleep(1)
        self.start_bot()

    def update_uptime(self):
        if self.start_time:
            delta = datetime.now() - self.start_time
            self.uptime_label.config(text=f"Uptime: {str(delta).split('.')[0]}")
        self.root.after(1000, self.update_uptime)

    def update_resource_usage(self):
        if self.psutil_proc and self.psutil_proc.is_running():
            try:
                mem = self.psutil_proc.memory_info().rss / (1024 ** 2)
                cpu = self.psutil_proc.cpu_percent(interval=0.1)
                self.resource_label.config(text=f"CPU: {cpu:.1f}%   RAM: {mem:.1f} MB")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                self.resource_label.config(text="CPU: --%   RAM: -- MB")
        else:
            self.resource_label.config(text="CPU: --%   RAM: -- MB")
        self.root.after(3000, self.update_resource_usage)

    def create_tray_icon(self):
        icon_image = Image.open(LOGO_PATH).resize((64, 64))

        def on_restore(icon, item=None):
            self.root.deiconify()
            self.root.lift()
            self.root.attributes("-topmost", True)
            self.root.after(100, lambda: self.root.attributes("-topmost", False))

        def on_quit(icon, item=None):
            self.exit_app()

        menu = Menu(
            MenuItem("Show Panel", on_restore),
            MenuItem("Stop Bot", self.stop_bot),
            MenuItem("Force Quit", on_quit)
        )

        self.tray_icon = Icon("Worldwise", icon_image, "Worldwise", menu)

        def tray_thread():
            self.tray_icon.run(setup)

        def setup(icon):
            icon.visible = True
            icon.update_menu()

        threading.Thread(target=tray_thread, daemon=True).start()

        def update_tray_title():
            if self.start_time:
                delta = datetime.now() - self.start_time
                self.tray_icon.title = f"Uptime: {str(delta).split('.')[0]}"
            self.root.after(5000, update_tray_title)

        update_tray_title()

    def edit_json_file(self, file_path, title):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry("500x600")
        win.configure(bg="#2c2f33")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            content = ""

        text = tk.Text(win, wrap='word', bg="#23272a", fg="white", insertbackground="white")
        text.insert(tk.END, content)
        text.pack(expand=True, fill='both', padx=10, pady=10)

        tk.Button(win, text="Save Changes", command=lambda: self.save_json_file(file_path, text, win),
                  bg="#2f4a66", fg="white", font=("Segoe UI", 10)).pack(pady=10)

    def save_json_file(self, file_path, text_widget, window):
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text_widget.get("1.0", tk.END))
        window.destroy()

    def open_chat_logs(self):
        log_path = os.path.join(os.getcwd(), "chat_logs.txt")
        if os.path.exists(log_path):
            if os.name == "nt":
                os.startfile(log_path)  # Windows
            else:
                subprocess.call(["open" if sys.platform == "darwin" else "xdg-open", log_path])
        else:
            self.append_log("[INFO] chat_logs.txt does not exist yet.\n")


if __name__ == "__main__":
    root = tk.Tk()
    app = BotGUI(root)
    root.mainloop()
