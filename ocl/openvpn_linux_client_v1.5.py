#!/usr/bin/env python3
"""
OCL - OpenVPN Linux Client (Bundled OpenVPN)

Author: Bastiaan Williams
Email: bastiaanwilliams@protonmail.com
Date: 2024-12-12
Version: 1.5
License: GPL 3

Description:
A user-friendly OpenVPN GUI client for Linux (or cross-platform),
that bundles the OpenVPN client binary. Also adjusted to work under
Nuitka onefile mode by detecting sys._MEIPASS for image paths.
"""

__author__ = "Bastiaan Williams"
__version__ = "1.5"
__license__ = "GPL 3"

import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import threading
import pexpect
import psutil
import time
import re
import os
import sys
import queue
import json
from pathlib import Path
from screeninfo import get_monitors
import platform

if hasattr(sys, '_MEIPASS'):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SYSTEM = platform.system().lower()
if SYSTEM.startswith("win"):
    OPENVPN_BINARY_NAME = "openvpn.exe"
elif SYSTEM.startswith("darwin"):
    OPENVPN_BINARY_NAME = "openvpn_macos"
else:
    OPENVPN_BINARY_NAME = "openvpn"

BUNDLED_OPENVPN_PATH = os.path.join(BASE_DIR, "bin", OPENVPN_BINARY_NAME)

CONFIG_DIR = Path.home() / ".openvpn_client"
CONFIG_FILE = CONFIG_DIR / "config.json"

def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {"show_splash": True}
    else:
        return {"show_splash": True}

def save_config(config):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def get_asset_path(filename):
    return os.path.join(BASE_DIR, "images", filename)

light_theme = {
    "bg": "#6999bf",
    "fg": "#000000",
    "bg_input": "#f0f0f0",
    "fg_input": "#000000",
    "highlight": "#444444",
    "button_bg": "#e0e0e0",
    "button_fg": "#000000",
    "ht": "2",
    "hb": "orange",
    "bg_but": "orange",
    "highlight_text": "#000000",
    "filetext": "orange"
}

dark_theme = {
    "bg": "#1e1e20",
    "fg": "#ffffff",
    "bg_input": "#4a4a4a",
    "fg_input": "orange",
    "highlight": "#44e602",
    "button_bg": "#3a3b3c",
    "button_fg": "#ffffff",
    "ht": "2",
    "hb": "#fe7014",
    "bg_but": "orange",
    "highlight_text": "#44e602",
    "filetext": "#fe7014"
}

class SplashScreen(tk.Toplevel):
    def __init__(self, parent, image_path, message, duration=3000, config=None):
        super().__init__(parent)
        self.duration = duration
        self.config_data = config or {"show_splash": True}
        self.overrideredirect(True)

        try:
            splash_image = (
                Image.open(image_path)
                .convert("RGBA")
                .resize((550, 324), Image.Resampling.LANCZOS)
            )
            self.splash_photo = ImageTk.PhotoImage(splash_image)
        except Exception as e:
            messagebox.showerror("Splash Image Error", f"Failed to load splash image: {e}")
            self.destroy()
            parent.destroy()
            return

        self.canvas = tk.Canvas(self, width=530, height=314, highlightthickness=0)
        self.canvas.pack()

        self.canvas.create_image(0, 0, anchor="nw", image=self.splash_photo)
        self.canvas.create_text(280, 280, text=message, font=("Arial", 12), fill="white", anchor="center")

        self.dont_show_var = tk.BooleanVar(value=not self.config_data.get("show_splash", True))
        self.checkbox = tk.Checkbutton(
            self,
            text="Don't show splash",
            variable=self.dont_show_var,
            bg="#202020",
            fg="#ffffff",
            selectcolor="#202020",
            activebackground="#202020",
            activeforeground="orange",
            bd=0,
            highlightthickness=0,
            relief="flat",
            command=self.on_checkbox_toggle
        )
        self.checkbox_window = self.canvas.create_window(75, 300, window=self.checkbox, anchor="center")

        self.center_on_primary_monitor(531, 315)
        self.after(self.duration, self.destroy)

    def center_on_primary_monitor(self, width, height):
        monitors = get_monitors()
        if not monitors:
            x, y = 100, 100
        else:
            primary_monitor = monitors[0]
            x = primary_monitor.x + (primary_monitor.width - width) // 2
            y = primary_monitor.y + (primary_monitor.height - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

    def on_checkbox_toggle(self):
        self.config_data["show_splash"] = not self.dont_show_var.get()

class TrafficMonitor:
    def __init__(self, root, canvas, sent_label_item, received_label_item, theme):
        self.root = root
        self.canvas = canvas
        self.sent_label_item = sent_label_item
        self.received_label_item = received_label_item
        self.theme = theme
        self.monitoring = True
        self.initial_sent = 0
        self.initial_recv = 0

    def monitor_traffic(self):
        try:
            initial = psutil.net_io_counters()
            self.initial_sent = initial.bytes_sent
            self.initial_recv = initial.bytes_recv

            while self.monitoring:
                stats = psutil.net_io_counters()
                total_sent = (stats.bytes_sent - self.initial_sent) / (1024 * 1024)
                total_recv = (stats.bytes_recv - self.initial_recv) / (1024 * 1024)

                self.root.after(0, self.update_labels, total_sent, total_recv)
                time.sleep(1)
        except Exception as e:
            print(f"Traffic Monitor Error: {e}")
            self.monitoring = False

    def update_labels(self, total_sent, total_recv):
        self.canvas.itemconfig(self.sent_label_item, text=f"📤 Sent: {total_sent:.2f} MB")
        self.canvas.itemconfig(self.received_label_item, text=f"📥 Received: {total_recv:.2f} MB")

    def start_monitoring(self):
        self.monitoring = True
        monitor_thread = threading.Thread(target=self.monitor_traffic, daemon=True)
        monitor_thread.start()

    def stop_monitoring(self):
        self.monitoring = False

class OpenVPNClientApp:
    def __init__(self, root):
        self.root = root
        self.root.withdraw()

        self.config = load_config()

        saved_theme = self.config.get("theme", "dark")
        self.current_theme = dark_theme if saved_theme == "dark" else light_theme

        self.vpn_process = None
        self.monitoring = False
        self.mfa_code = None
        self.connected = False
        self.queue = queue.Queue()

        try:
            self.dark_mode_img = ImageTk.PhotoImage(
                Image.open(get_asset_path("light_mode_icon.png")).convert("RGBA")
                .resize((30, 30), Image.Resampling.LANCZOS)
            )
            self.light_mode_img = ImageTk.PhotoImage(
                Image.open(get_asset_path("dark_mode_icon.png")).convert("RGBA")
                .resize((30, 30), Image.Resampling.LANCZOS)
            )
            self.connect_button_image_dark = ImageTk.PhotoImage(
                Image.open(get_asset_path("on3.png")).convert("RGBA")
                .resize((70, 70), Image.Resampling.LANCZOS)
            )
            self.disconnect_button_image_dark = ImageTk.PhotoImage(
                Image.open(get_asset_path("off3.png")).convert("RGBA")
                .resize((70, 70), Image.Resampling.LANCZOS)
            )
            self.cover_network_image = ImageTk.PhotoImage(
                Image.open(get_asset_path("cover_network.png")).convert("RGBA")
                .resize((330, 160), Image.Resampling.LANCZOS)
            )
            self.connect_button_image_light = ImageTk.PhotoImage(
                Image.open(get_asset_path("on3.png")).convert("RGBA")
                .resize((70, 70), Image.Resampling.LANCZOS)
            )
            self.disconnect_button_image_light = ImageTk.PhotoImage(
                Image.open(get_asset_path("off3.png")).convert("RGBA")
                .resize((70, 70), Image.Resampling.LANCZOS)
            )
            self.logo_dark = ImageTk.PhotoImage(
                Image.open(get_asset_path("openvpnlogo.png")).convert("RGBA")
                .resize((290, 72), Image.Resampling.LANCZOS)
            )
            self.logo_light = self.logo_dark  
            self.bg_image_dark = ImageTk.PhotoImage(
                Image.open(get_asset_path("background_dark.png")).convert("RGBA")
                .resize((330, 650), Image.Resampling.LANCZOS)
            )
            self.bg_image_light = ImageTk.PhotoImage(
                Image.open(get_asset_path("background_light.png")).convert("RGBA")
                .resize((330, 650), Image.Resampling.LANCZOS)
            )
        except Exception as e:
            messagebox.showerror("Image Load Error", f"Failed to load images: {e}")
            self.root.destroy()
            return

        if self.config.get("show_splash", True):
            self.show_splash_screen()
        else:
            self.initialize_main_window()

    def show_splash_screen(self):
        splash_image_path = get_asset_path("splash.jpg")
        splash = SplashScreen(
            self.root,
            splash_image_path,
            "OpenVPN Linux Client version 1.5",
            duration=3000,
            config=self.config
        )
        splash.update()
        self.root.after(splash.duration, self.on_splash_close, splash)

    def on_splash_close(self, splash):
        save_config(self.config)
        self.initialize_main_window()

    def initialize_main_window(self):
        self.root.deiconify()
        self.apply_theme(self.current_theme)
        self.create_widgets()

    def apply_theme(self, theme):
        self.current_theme = theme

    def create_widgets(self):
        menu_bar = tk.Menu(self.root)
        self.root.config(menu=menu_bar)

        app_menu = tk.Menu(menu_bar, tearoff=False)
        menu_bar.add_cascade(label="Menu", menu=app_menu)
        # ---------------- NEW: Add Config File command ----------------
        app_menu.add_command(label="Add Config File", command=self.menu_add_config_file)
        # -------------------------------------------------------------
        app_menu.add_command(label="About", command=self.show_about)
        app_menu.add_command(label="Settings", command=self.show_settings)
        app_menu.add_separator()
        app_menu.add_command(label="Quit", command=self.quit_app)

        self.canvas = tk.Canvas(self.root, width=330, height=575, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        chosen_bg = self.bg_image_dark if self.current_theme == dark_theme else self.bg_image_light
        self.bg_item = self.canvas.create_image(0, 0, anchor="nw", image=chosen_bg)

        chosen_logo = self.logo_dark if self.current_theme == dark_theme else self.logo_light
        self.logo_item = self.canvas.create_image(20, 10, anchor="nw", image=chosen_logo)

        current_icon = self.dark_mode_img if self.current_theme == dark_theme else self.light_mode_img
        self.toggle_button_theme = tk.Button(
            self.canvas,
            image=current_icon,
            bg=self.current_theme["bg"],
            fg=self.current_theme["fg"],
            activebackground=self.current_theme["bg"],
            activeforeground=self.current_theme["fg"],
            bd=0,
            highlightthickness=0,
            relief="flat",
            command=self.toggle_theme
        )
        self.toggle_button_theme.image = current_icon
        self.canvas.create_window(285, 110, window=self.toggle_button_theme, anchor="nw")

              
        self.config_path_var = tk.StringVar(value="None (select in Menu)")
        self.canvas.create_text(
            30, 140,
            text="Current OpenVPN config file:",
            font=("Arial", 10),
            fill=self.current_theme["fg"],
            anchor="nw"
        )
        self.config_text_item = self.canvas.create_text(
            30, 156,
            text=self.config_path_var.get(),
            font=("Arial", 9),
            fill=self.current_theme["filetext"],
            anchor="nw",
            width=240
        )

        self.canvas.create_text(
            30, 210,
            text="\U0001F464 Username:",
            font=("Arial", 12),
            fill=self.current_theme["fg"],
            anchor="nw"
        )
        self.username_var = tk.StringVar()
        self.username_entry = tk.Entry(
            self.canvas,
            highlightthickness=self.current_theme.get("ht", 0),
            highlightbackground=self.current_theme.get("hb", "orange"),
            bg=self.current_theme["bg_input"],
            fg=self.current_theme["fg_input"],
            font=("Arial", 18),
            textvariable=self.username_var,
            width=20
        )
        self.canvas.create_window(30, 230, window=self.username_entry, anchor="nw")

        self.canvas.create_text(
            30, 280,
            text="\U0001F512 Password:",
            font=("Arial", 12),
            fill=self.current_theme["fg"],
            anchor="nw"
        )
        self.password_var = tk.StringVar()
        self.password_entry = tk.Entry(
            self.canvas,
            highlightthickness=self.current_theme.get("ht", 1),
            highlightbackground=self.current_theme.get("hb", "#fe7014"),
            bg=self.current_theme["bg_input"],
            fg=self.current_theme["fg_input"],
            font=("Arial", 18),
            textvariable=self.password_var,
            show="*",
            width=20
        )
        self.canvas.create_window(30, 300, window=self.password_entry, anchor="nw")

        current_connect_image = (
            self.connect_button_image_dark
            if self.current_theme == dark_theme
            else self.connect_button_image_light
        )
        self.toggle_button_connect = tk.Button(
            self.canvas,
            image=current_connect_image,
            command=self.toggle_vpn,
            borderwidth=0,
            highlightthickness=0,
            bg=self.current_theme["bg"],
            fg=self.current_theme["fg"],
            activebackground=self.current_theme["bg"],
            activeforeground=self.current_theme["fg"],
            cursor="hand2",
        )
        self.toggle_button_connect.image = current_connect_image
        self.canvas.create_window(128, 358, window=self.toggle_button_connect, anchor="nw")

        self.canvas.create_text(
            165, 485,
            text="📶 Network Traffic",
            font=("Arial", 12, "bold"),
            fill="#8ec4e9",
            anchor="center"
        )
        self.sent_label_item = self.canvas.create_text(
            100, 502,
            text="📤 Sent: 0.00 MB",
            font=("Arial", 9),
            fill=self.current_theme["fg"],
            anchor="center"
        )
        self.received_label_item = self.canvas.create_text(
            230, 502,
            text="📥 Received: 0.00 MB",
            font=("Arial", 9),
            fill=self.current_theme["fg"],
            anchor="center"
        )
        self.canvas.create_text(
            165, 532,
            text="VPN STATUS:",
            font=("Arial", 10),
            fill=self.current_theme["fg"],
            anchor="center"
        )
        self.status_text_item = self.canvas.create_text(
            165, 550,
            text=" \U0001F513 Not Connected ",
            font=("Arial", 12, "bold"),
            fill="#fe7014",
            anchor="center"
        )
        self.cover_network_image_item = self.canvas.create_image(
            0, 420,
            anchor="nw",
            image=self.cover_network_image
        )
        self.traffic_monitor = TrafficMonitor(
            self.root,
            self.canvas,
            self.sent_label_item,
            self.received_label_item,
            self.current_theme
        )

    # ------------------ MENU ACTIONS ------------------
    def menu_add_config_file(self):
        """
        Called when user clicks "Add Config File" from the menu.
        This will open the file dialog so the user can select a config file,
        just like the Browse button below.
        """
        self.browse_config()

    def quit_app(self):
        self.root.destroy()

    def show_about(self):
        """Open a themed 'About' window."""
        about_win = tk.Toplevel(self.root)
        about_win.title("About")
        
        # Same background color as the current theme
        about_win.configure(bg=self.current_theme["bg"])
        
        # Set a reasonable size (optional). Adjust to your liking
        about_win.geometry("320x220")
        about_win.resizable(False, False)

        # Construct the about text
        about_text = (
            "OpenVPN Linux Client (Bundled)\n"
            f"Version: {__version__}\n"
            "Author: Bastiaan Williams\n"
            "Email: bastiaanwilliams@protonmail.com\n"
            "License: GPL 3\n\n"
            "A user-friendly OpenVPN GUI client for Linux."
        )

        # Create a label with the same theme colors
        tk.Label(
            about_win,
            text=about_text,
            bg=self.current_theme["bg"],
            fg=self.current_theme["fg"],
            font=("Arial", 10),
            justify="left"
        ).pack(pady=10, padx=20)

        # Add a "Close" button that also follows the theme
        def close_about():
            about_win.destroy()

        tk.Button(
            about_win,
            text="Close",
            command=close_about,
            bg=self.current_theme.get("button_bg", "gray"),
            fg=self.current_theme.get("button_fg", "black"),
            activebackground=self.current_theme.get("button_bg", "gray"),
            activeforeground=self.current_theme.get("button_fg", "black"),
            font=("Arial", 10, "bold")
        ).pack(pady=5)

        # (Optional) to make this window "modal," so user must close About before returning
        about_win.grab_set()
        self.root.wait_window(about_win)


    def show_settings(self):
        settings_win = tk.Toplevel(self.root)
        settings_win.title("Settings")
        settings_win.configure(bg=self.current_theme["bg"])
        settings_win.geometry("300x250")

        tk.Label(
            settings_win,
            text="Show splash on startup?",
            fg=self.current_theme["fg"],
            bg=self.current_theme["bg"],
            font=("Arial", 10, "bold")
        ).pack(pady=(10, 0))

        self.splash_var = tk.BooleanVar(value=self.config.get("show_splash", True))
        tk.Checkbutton(
            settings_win,
            text="Enable splash screen",
            variable=self.splash_var,
            onvalue=True,
            offvalue=False,
            bg=self.current_theme["bg"],
            fg=self.current_theme["fg"],
            selectcolor="#444444"
        ).pack(pady=(0, 10))

        tk.Label(
            settings_win,
            text="Choose theme:",
            fg=self.current_theme["fg"],
            bg=self.current_theme["bg"],
            font=("Arial", 10, "bold")
        ).pack()

        self.theme_var = tk.StringVar()
        self.theme_var.set("dark" if self.current_theme == dark_theme else "light")

        tk.Radiobutton(
            settings_win,
            text="Dark",
            variable=self.theme_var,
            value="dark",
            bg=self.current_theme["bg"],
            fg=self.current_theme["fg"],
            selectcolor="#444444"
        ).pack(anchor="w", padx=30)

        tk.Radiobutton(
            settings_win,
            text="Light",
            variable=self.theme_var,
            value="light",
            bg=self.current_theme["bg"],
            fg=self.current_theme["fg"],
            selectcolor="#444444"
        ).pack(anchor="w", padx=30)

        def save_settings():
            self.config["show_splash"] = self.splash_var.get()
            self.config["theme"] = self.theme_var.get()  
            save_config(self.config)

            if self.theme_var.get() == "dark":
                self.apply_theme(dark_theme)
            else:
                self.apply_theme(light_theme)

            self.apply_theme_to_widgets()

            messagebox.showinfo("Settings", "Settings saved.")
            settings_win.destroy()

        tk.Button(
            settings_win,
            text="Save",
            command=save_settings,
            bg="orange",
            fg="white",
            font=("Arial", 10, "bold")
            
        ).pack(pady=20)

    # ---------------------------------------------------

    def browse_config(self):
        config_file = filedialog.askopenfilename(
            title="Select OpenVPN Config File",
            filetypes=[("OpenVPN Config Files", "*.ovpn")],
        )
        if config_file:
            self.config_path_var.set(config_file)
        else:
            self.config_path_var.set("None")
        self.canvas.itemconfig(self.config_text_item, text=self.config_path_var.get())

    def toggle_vpn(self):
        if not self.connected:
            self.start_vpn()
        else:
            self.stop_vpn()

    def start_vpn(self):
        self.mfa_code = None
        config_file = self.config_path_var.get()
        username = self.username_var.get()
        password = self.password_var.get()

        if not config_file or config_file == "None" or not username or not password:
            messagebox.showerror("Error", "Config file, username, and password are required!")
            return

        self.toggle_button_connect.config(state="disabled")
        threading.Thread(target=self.run_vpn, args=(config_file, username, password), daemon=True).start()
        self.monitoring = True
        self.traffic_monitor.start_monitoring()
        self.root.after(100, self.process_queue)

    def run_vpn(self, config_file, username, password):
        try:
            cmd = f"\"{BUNDLED_OPENVPN_PATH}\" --config \"{config_file}\""
            self.vpn_process = pexpect.spawn(cmd, encoding='utf-8')
            self.vpn_process.logfile = open("pexpect_log.txt", "w")

            self.vpn_process.expect(re.compile(r"Enter Auth Username.*:", re.IGNORECASE), timeout=60)
            self.vpn_process.sendline(username)

            self.vpn_process.expect(re.compile(r"Enter Auth Password.*:", re.IGNORECASE), timeout=60)
            self.vpn_process.sendline(password)

            mfa_prompt_pattern = re.compile(r"CHALLENGE:", re.IGNORECASE)
            result = self.vpn_process.expect([mfa_prompt_pattern, pexpect.TIMEOUT, pexpect.EOF], timeout=30)

            if result == 0:
                self.queue.put("SHOW_MFA")
                while self.mfa_code is None:
                    time.sleep(0.1)
                if self.vpn_process and self.vpn_process.isalive():
                    self.vpn_process.sendline(self.mfa_code.strip())

            while True:
                if not self.vpn_process.isalive():
                    raise Exception("OpenVPN process terminated unexpectedly.")

                try:
                    line = self.vpn_process.readline().strip()
                except pexpect.EOF:
                    break
                print(f"OpenVPN: {line}")

                if "AUTH_FAILED" in line:
                    self.root.after(0, lambda: messagebox.showwarning(
                        "Error",
                        "Authentication failed. Please check your credentials."
                    ))
                    raise Exception("Authentication failed. Please check your credentials.")

                if "Initialization Sequence Completed" in line:
                    self.connected = True
                    self.root.after(0, self.update_ui_on_connect)
                    break
        except Exception as e:
            print(f"VPN Error: {e}")
            self.root.after(0, lambda: messagebox.showerror("Error", f"VPN Error: {e}"))
            self.root.after(0, self.update_ui_on_disconnect)
        finally:
            self.reset_buttons()

    def update_ui_on_connect(self):
        if self.current_theme == dark_theme:
            new_image = self.disconnect_button_image_dark
        else:
            new_image = self.disconnect_button_image_light
        self.toggle_button_connect.config(image=new_image)
        self.toggle_button_connect.image = new_image
        self.canvas.itemconfig(
            self.status_text_item,
            text=" \U0001F512 Connected ",
            fill=self.current_theme["highlight_text"]
        )

    def stop_vpn(self):
        if self.vpn_process and self.vpn_process.isalive():
            try:
                self.vpn_process.sendcontrol('c')
                self.vpn_process.expect(pexpect.EOF, timeout=10)
            except pexpect.TIMEOUT:
                self.vpn_process.terminate(force=True)

            self.vpn_process.close(force=True)
            self.vpn_process = None

        self.connected = False
        self.monitoring = False
        self.traffic_monitor.stop_monitoring()
        self.update_ui_on_disconnect()

    def update_ui_on_disconnect(self):
        if self.current_theme == dark_theme:
            new_image = self.connect_button_image_dark
        else:
            new_image = self.connect_button_image_light
        self.toggle_button_connect.config(image=new_image)
        self.toggle_button_connect.image = new_image
        self.canvas.itemconfig(self.status_text_item, text=" Disconnected ", fill="red")

    def reset_buttons(self):
        self.toggle_button_connect.config(state="normal")

    def process_queue(self):
        try:
            while not self.queue.empty():
                message = self.queue.get_nowait()
                if message == "SHOW_MFA":
                    self.show_mfa_popup()
        except Exception as e:
            print(f"Queue processing error: {e}")
        finally:
            if self.monitoring:
                self.root.after(100, self.process_queue)

    def show_mfa_popup(self):
        def submit_mfa():
            code = mfa_code_var.get().strip()
            if code:
                self.mfa_code = code
                mfa_window.destroy()
            else:
                messagebox.showerror("Error", "2FA code cannot be empty!")

        mfa_window = tk.Toplevel(self.root)
        mfa_window.title("Your 2FA Code")
        mfa_window.configure(bg=self.current_theme["bg"])
        mfa_window.geometry("300x340")
        mfa_window.resizable(False, False)

        try:
            second_logo_image = (
                Image.open(get_asset_path("2fa.png"))
                .convert("RGBA")
                .resize((200, 100), Image.Resampling.LANCZOS)
            )
            self.second_logo = ImageTk.PhotoImage(second_logo_image)
            tk.Label(mfa_window, image=self.second_logo, bg=self.current_theme["bg"]).pack(pady=10)
        except Exception as e:
            messagebox.showerror("Image Load Error", f"Failed to load 2FA logo: {e}")
            mfa_window.destroy()
            return

        tk.Label(
            mfa_window,
            text="\U0001F511 Your 2FA Code:",
            font=("Arial", 14),
            bg=self.current_theme["bg"],
            fg=self.current_theme["fg"]
        ).pack(pady=10)

        mfa_code_var = tk.StringVar()
        mfa_entry = tk.Entry(
            mfa_window,
            bg=self.current_theme["bg_input"],
            fg="orange",
            font=("Arial", 34),
            width=6,
            textvariable=mfa_code_var
        )
        mfa_entry.pack(pady=10)
        mfa_entry.focus_set()

        tk.Button(
            mfa_window,
            text="Submit",
            command=submit_mfa,
            bg="orange",
            fg="white",
            font=("Arial", 10, "bold"),
            cursor="hand2"
        ).pack(pady=10)

        mfa_window.grab_set()
        self.root.wait_window(mfa_window)

    def toggle_theme(self):
        if self.current_theme == dark_theme:
            self.apply_theme(light_theme)
            self.config["theme"] = "light"
        else:
            self.apply_theme(dark_theme)
            self.config["theme"] = "dark"

        save_config(self.config)
        self.apply_theme_to_widgets()

    def apply_theme_to_widgets(self):
        if self.current_theme == dark_theme:
            self.canvas.itemconfig(self.bg_item, image=self.bg_image_dark)
        else:
            self.canvas.itemconfig(self.bg_item, image=self.bg_image_light)

        if self.current_theme == dark_theme:
            self.toggle_button_theme.config(
                image=self.dark_mode_img,
                bg=self.current_theme["bg"],
                fg=self.current_theme["fg"],
                activebackground=self.current_theme["bg"],
                activeforeground=self.current_theme["fg"]
            )
            self.toggle_button_theme.image = self.dark_mode_img
        else:
            self.toggle_button_theme.config(
                image=self.light_mode_img,
                bg=self.current_theme["bg"],
                fg=self.current_theme["fg"],
                activebackground=self.current_theme["bg"],
                activeforeground=self.current_theme["fg"]
            )
            self.toggle_button_theme.image = self.light_mode_img

        self.canvas.itemconfig(self.config_text_item, fill=self.current_theme["filetext"])
        self.canvas.itemconfig(self.sent_label_item, fill=self.current_theme["fg"])
        self.canvas.itemconfig(self.received_label_item, fill=self.current_theme["fg"])
        self.canvas.itemconfig(self.status_text_item, fill=self.current_theme["highlight_text"])

       
        self.username_entry.config(bg=self.current_theme["bg_input"], fg=self.current_theme["fg_input"])
        self.password_entry.config(bg=self.current_theme["bg_input"], fg=self.current_theme["fg_input"])

        if self.connected:
            if self.current_theme == dark_theme:
                new_image = self.disconnect_button_image_dark
                self.canvas.itemconfig(self.status_text_item, text=" \U0001F512 Connected ", fill="#71e900")
            else:
                new_image = self.disconnect_button_image_light
                self.canvas.itemconfig(self.status_text_item, text=" \U0001F512 Connected ", fill="#71e900")
        else:
            if self.current_theme == dark_theme:
                new_image = self.connect_button_image_dark
                self.canvas.itemconfig(self.status_text_item, text=" \U0001F513 Not Connected ", fill="orange")
            else:
                new_image = self.connect_button_image_light
                self.canvas.itemconfig(self.status_text_item, text=" \U0001F513 Not Connected ", fill="orange")

        self.toggle_button_connect.config(
            image=new_image,
            bg=self.current_theme["bg"],
            fg=self.current_theme["fg"],
            activebackground=self.current_theme["bg"],
            activeforeground=self.current_theme["fg"]
        )
        self.toggle_button_connect.image = new_image

        self.canvas.itemconfig(self.sent_label_item, fill=self.current_theme["fg"])
        self.canvas.itemconfig(self.received_label_item, fill=self.current_theme["fg"])


if __name__ == "__main__":
    root = tk.Tk()
    app = OpenVPNClientApp(root)
    root.title("OpenVPN - Linux Client (Bundled)")
    root.geometry("330x575")
    root.resizable(False, False)
    root.mainloop()

