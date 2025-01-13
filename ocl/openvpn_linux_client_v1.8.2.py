#!/usr/bin/env python3
"""
OCL - OpenVPN Linux Client (Bundled OpenVPN)

Author: Bastiaan Williams
Email: bastiaanwilliams@protonmail.com
Date: 2025-01-13
Version: 1.8.2
License: GPL 3

Description:
A user-friendly OpenVPN GUI client for Linux (or cross-platform),
that bundles the OpenVPN client binary.
"""

__author__ = "Bastiaan Williams"
__version__ = "1.8.2"
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
import netifaces
import sys
import queue
import json
import keyring
from pathlib import Path
from screeninfo import get_monitors
import platform

# ---- Imports for Encryption and Keyring ----
from cryptography.fernet import Fernet
 

# ---------------------------------------------------------------------
# FUNCTIONS TO HANDLE KEYRING
# ---------------------------------------------------------------------
def get_or_create_key() -> bytes:
    """
    Retrieve the Fernet key from the OS keyring, or generate a new one
    if it doesn't exist yet.
    """
    service_name = "openvpn_app"
    key_name = "my_encryption_key"

    found_key = keyring.get_password(service_name, key_name)
    if found_key is None:
        # Generate new key
        new_key = Fernet.generate_key()
        # Store it in the keyring
        keyring.set_password(service_name, key_name, new_key.decode('utf-8'))
        return new_key
    else:
        # Convert the stored string back to bytes
        return found_key.encode('utf-8')

# Get the key at startup
STORED_KEY = get_or_create_key()

def encrypt_string(plaintext: str) -> str:
    """Encrypts a string using Fernet from OS keyring and returns base64-encoded."""
    f = Fernet(STORED_KEY)
    token = f.encrypt(plaintext.encode('utf-8'))  # bytes
    return token.decode('utf-8')  # convert bytes -> str

def decrypt_string(ciphertext: str) -> str:
    """Decrypts a base64-encoded Fernet token (from OS keyring) and returns the plaintext."""
    f = Fernet(STORED_KEY)
    plaintext = f.decrypt(ciphertext.encode('utf-8'))  # bytes
    return plaintext.decode('utf-8')

# ---------------------------------------------------------------------
# CONFIG & THEME HANDLING
# ---------------------------------------------------------------------
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
    """
    Load the config.json file and decrypt saved credentials if present.
    Returns a dict with settings (in plain text).
    """
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            # If the JSON file is invalid, fallback to defaults
            data = {}

        # Provide defaults if keys are missing
        data.setdefault("show_splash", True)
        data.setdefault("theme", "dark")
        data.setdefault("remember_credentials", False)
        data.setdefault("saved_username", "")
        data.setdefault("saved_password", "")

        # Decrypt credentials if they're not empty
        if data["saved_username"]:
            try:
                data["saved_username"] = decrypt_string(data["saved_username"])
            except Exception:
                data["saved_username"] = ""

        if data["saved_password"]:
            try:
                data["saved_password"] = decrypt_string(data["saved_password"])
            except Exception:
                data["saved_password"] = ""

        return data
    else:
        # If file doesn’t exist, return our default structure
        return {
            "show_splash": True,
            "theme": "dark",
            "remember_credentials": False,
            "saved_username": "",
            "saved_password": ""
        }

def save_config(config_data):
    """
    Save the config data to config.json, encrypting credentials only in a copy.
    This avoids storing the encrypted strings in memory, preventing double-encryption.
    """
    data_to_save = {
        "show_splash": config_data.get("show_splash", True),
        "theme": config_data.get("theme", "dark"),
        "remember_credentials": config_data.get("remember_credentials", False),
    }

    if data_to_save["remember_credentials"]:
        data_to_save["saved_username"] = encrypt_string(config_data.get("saved_username", ""))
        data_to_save["saved_password"] = encrypt_string(config_data.get("saved_password", ""))
    else:
        data_to_save["saved_username"] = ""
        data_to_save["saved_password"] = ""

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(data_to_save, f, indent=4)

def get_asset_path(filename):
    return os.path.join(BASE_DIR, "images", filename)

light_theme = {
    "bg": "#6999bf",
    "fg": "#000000",
    "fg_ip": "#1474FE",
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
    "fg_ip": "#FEF014",
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

# ---------------------------------------------------------------------
# SPLASH SCREEN
# ---------------------------------------------------------------------
class SplashScreen(tk.Toplevel):
    def __init__(self, parent, image_path, message, duration=2500, config=None):
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
        self.canvas.create_text(280, 280, text=message, font=("Arial", 11), fill="white", anchor="center")

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

# ---------------------------------------------------------------------
# TRAFFIC MONITOR
# ---------------------------------------------------------------------
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

# ---------------------------------------------------------------------
# MAIN APPLICATION
# ---------------------------------------------------------------------
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

        # We'll store the VPN IP string here, initially blank
        self.VPNIP = ""

        # Load images
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

            self.connect_button_image_light = ImageTk.PhotoImage(
                Image.open(get_asset_path("on3.png")).convert("RGBA")
                .resize((70, 70), Image.Resampling.LANCZOS)
            )
            self.disconnect_button_image_light = ImageTk.PhotoImage(
                Image.open(get_asset_path("off3.png")).convert("RGBA")
                .resize((70, 70), Image.Resampling.LANCZOS)
            )

            self.cover_network_image = ImageTk.PhotoImage(
                Image.open(get_asset_path("cover_network.png")).convert("RGBA")
                .resize((330, 160), Image.Resampling.LANCZOS)
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

    # -----------------------------------------------------------------
    # SPLASH
    # -----------------------------------------------------------------
    def show_splash_screen(self):
        splash_image_path = get_asset_path("splash.jpg")
        splash = SplashScreen(
            self.root,
            splash_image_path,
            f"OpenVPN Linux Client ver.{__version__}",
            duration=2500,
            config=self.config
        )
        splash.update()
        self.root.after(splash.duration, self.on_splash_close, splash)

    def on_splash_close(self, splash):
        save_config(self.config)
        self.initialize_main_window()

    # -----------------------------------------------------------------
    # GET TUN IP
    # -----------------------------------------------------------------
    def get_tun_ip(self, interface='tun0'):
        """Return the IPv4 address of the TUN interface, or None if not found."""
        try:
            iface_info = netifaces.ifaddresses(interface)
            if netifaces.AF_INET in iface_info:
                ipv4_info = iface_info[netifaces.AF_INET][0]
                return ipv4_info.get('addr')
        except ValueError:
            pass
        return None

    # -----------------------------------------------------------------
    # MAIN WINDOW
    # -----------------------------------------------------------------
    def initialize_main_window(self):
        self.root.deiconify()
        self.apply_theme(self.current_theme)
        self.create_widgets()

    def apply_theme(self, theme):
        self.current_theme = theme

    def create_widgets(self):
        # Menu
        menu_bar = tk.Menu(self.root)
        self.root.config(menu=menu_bar)

        app_menu = tk.Menu(menu_bar, tearoff=False)
        menu_bar.add_cascade(label="Menu", menu=app_menu)
        app_menu.add_command(label="📄 Choose OpenVPN Config File", command=self.menu_add_config_file)
        app_menu.add_command(label="❔ About", command=self.show_about)
        app_menu.add_command(label="⚙️ Settings", command=self.show_settings)
        app_menu.add_separator()
        app_menu.add_command(label="❌ Quit", command=self.quit_app)

        # Canvas
        self.canvas = tk.Canvas(self.root, width=330, height=575, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        chosen_bg = self.bg_image_dark if self.current_theme == dark_theme else self.bg_image_light
        self.bg_item = self.canvas.create_image(0, 0, anchor="nw", image=chosen_bg)

        chosen_logo = self.logo_dark if self.current_theme == dark_theme else self.logo_light
        self.logo_item = self.canvas.create_image(20, 10, anchor="nw", image=chosen_logo)

        # THEME TOGGLE BUTTON
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

        # CONFIG PATH LABEL
        self.config_path_var = tk.StringVar(value="None. Choose a ovpn file, Menu -> Choose ovpn file")
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

        # USERNAME
        self.canvas.create_text(
            30, 210,
            text="\U0001F464 Username:",
            font=("Arial", 12),
            fill=self.current_theme["fg"],
            anchor="nw"
        )
        self.username_var = tk.StringVar(value=self.config.get("saved_username", ""))
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

        # PASSWORD
        self.canvas.create_text(
            30, 280,
            text="\U0001F512 Password:",
            font=("Arial", 12),
            fill=self.current_theme["fg"],
            anchor="nw"
        )
        self.password_var = tk.StringVar(value=self.config.get("saved_password", ""))

        # Start with the password hidden by default (show="*")
        self.password_entry = tk.Entry(
            self.canvas,
            highlightthickness=self.current_theme.get("ht", 1),
            highlightbackground=self.current_theme.get("hb", "#fe7014"),
            bg=self.current_theme["bg_input"],
            fg=self.current_theme["fg_input"],
            font=("Arial", 18),
            textvariable=self.password_var,
            show="*",   # Hide password
            width=20
        )
        self.canvas.create_window(30, 300, window=self.password_entry, anchor="nw")

        # SHOW/HIDE PASSWORD CHECKBOX
        self.show_password_var = tk.BooleanVar(value=False)
        def toggle_password():
            if self.show_password_var.get():
                self.password_entry.config(show="")
            else:
                self.password_entry.config(show="*")

        self.show_password_check = tk.Checkbutton(
            self.canvas,
            text="🔎 show password",
            variable=self.show_password_var,
            command=toggle_password,
            highlightthickness=0,
            border=0,
            bg=self.current_theme["bg"],
            fg=self.current_theme["fg"],
            activebackground=self.current_theme["bg"],
            activeforeground=self.current_theme["fg"],
            selectcolor="#444444"
        )
        self.canvas.create_window(155, 280, window=self.show_password_check, anchor="nw")

        # REMEMBER ME
        self.remember_me_var = tk.BooleanVar(value=self.config.get("remember_credentials", False))
        self.remember_me_checkbox = tk.Checkbutton(
            self.canvas,
            text="Save my Credentials",
            variable=self.remember_me_var,
            onvalue=True,
            offvalue=False,
            highlightthickness=0,
            border=0,
            bg=self.current_theme["bg"],
            fg=self.current_theme["fg"],
            activebackground=self.current_theme["bg"],
            activeforeground=self.current_theme["fg"],
            selectcolor="#444444"
        )
        self.canvas.create_window(30, 338, window=self.remember_me_checkbox, anchor="nw")

        # CONNECT BUTTON
        current_connect_image = (
            self.connect_button_image_dark
            if self.current_theme == dark_theme
            else self.connect_button_image_light
        )
        self.toggle_button_connect = tk.Button(
            self.canvas,
            image=current_connect_image,
            command=self.toggle_vpn,
            border=0,
            highlightthickness=0,
            bg=self.current_theme["bg"],
            fg=self.current_theme["fg"],
            activebackground=self.current_theme["bg"],
            activeforeground=self.current_theme["fg"],
            cursor="hand2",
        )
        self.toggle_button_connect.image = current_connect_image
        self.canvas.create_window(128, 368, window=self.toggle_button_connect, anchor="nw")

        # NETWORK TRAFFIC
        self.canvas.create_text(
            165, 465,
            text="📶 Network Traffic",
            font=("Arial", 12, "bold"),
            fill="#8ec4e9",
            anchor="center"
        )
        self.sent_label_item = self.canvas.create_text(
            100, 487,
            text="📤 Sent: 0.00 MB",
            font=("Arial", 9),
            fill=self.current_theme["fg"],
            anchor="center"
        )
        self.received_label_item = self.canvas.create_text(
            230, 487,
            text="📥 Received: 0.00 MB",
            font=("Arial", 9),
            fill=self.current_theme["fg"],
            anchor="center"
        )

        # LABEL FOR THE VPN IP
        self.vpnip_label_item = self.canvas.create_text(
            165, 502,
            text=self.VPNIP,
            font=("Arial", 10, "bold"),
            fill="#FEEC14",
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

    # -----------------------------------------------------------------
    # MENU ACTIONS
    # -----------------------------------------------------------------
    def menu_add_config_file(self):
        self.browse_config()

    def quit_app(self):
        self.root.destroy()

    def show_about(self):
        about_win = tk.Toplevel(self.root)
        about_win.title("About")
        about_win.configure(bg=self.current_theme["bg"])
        about_win.geometry("320x220")
        about_win.resizable(False, False)

        about_text = (
            "OpenVPN Linux Client (Bundled)\n"
            f"Version: {__version__}\n"
            "Author: Bastiaan Williams\n"
            "Email: bastiaanwilliams@protonmail.com\n"
            "License: GPL 3\n\n"
            "A user-friendly OpenVPN GUI client for Linux."
        )

        tk.Label(
            about_win,
            text=about_text,
            bg=self.current_theme["bg"],
            fg=self.current_theme["fg"],
            font=("Arial", 10),
            justify="left"
        ).pack(pady=10, padx=20)

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

        about_win.grab_set()
        self.root.wait_window(about_win)

    def show_settings(self):
        settings_win = tk.Toplevel(self.root)
        settings_win.title("Settings")
        settings_win.configure(bg=self.current_theme["bg"])
        settings_win.geometry("300x250")
        settings_win.resizable(False, False)

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

        settings_win.grab_set()
        self.root.wait_window(settings_win)

    # -----------------------------------------------------------------
    # BROWSE CONFIG
    # -----------------------------------------------------------------
    def browse_config(self):
        config_file = filedialog.askopenfilename(
            title="Select OpenVPN Config File",
            filetypes=[("OpenVPN Config Files", "*.ovpn")],
        )
        if config_file:
            self.config_path_var.set(config_file)
        else:
            # If user cancels, show the hint
            self.config_path_var.set("None. Choose a ovpn file, Menu -> Choose ovpn file")
        self.canvas.itemconfig(self.config_text_item, text=self.config_path_var.get())

    # -----------------------------------------------------------------
    # OPENVPN START/STOP
    # -----------------------------------------------------------------
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

        # If user hasn't chosen a config file, it's basically the hint string:
        if config_file.startswith("None. Choose"):
            messagebox.showerror(
                "Error",
                "No config file selected. Please choose a .ovpn file from the Menu."
            )
            return

        if not config_file or config_file == "None":
            messagebox.showerror("Error", "Config file, username, and password are required!")
            return

        if not username or not password:
            messagebox.showerror("Error", "Username and password are required!")
            return

        # Store user preference about "Remember Me"
        if self.remember_me_var.get():
            self.config["remember_credentials"] = True
            self.config["saved_username"] = username  # plain text in memory
            self.config["saved_password"] = password
        else:
            self.config["remember_credentials"] = False
            self.config["saved_username"] = ""
            self.config["saved_password"] = ""

        save_config(self.config)

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

            # Basic username/password prompts
            self.vpn_process.expect(re.compile(r"Enter Auth Username.*:", re.IGNORECASE), timeout=60)
            self.vpn_process.sendline(username)

            self.vpn_process.expect(re.compile(r"Enter Auth Password.*:", re.IGNORECASE), timeout=60)
            self.vpn_process.sendline(password)

            # Check for 2FA CHALLENGE
            mfa_prompt_pattern = re.compile(r"CHALLENGE:", re.IGNORECASE)
            result = self.vpn_process.expect([mfa_prompt_pattern, pexpect.TIMEOUT, pexpect.EOF], timeout=30)

            if result == 0:
                self.queue.put("SHOW_MFA")
                while self.mfa_code is None:
                    time.sleep(0.1)
                if self.vpn_process and self.vpn_process.isalive():
                    self.vpn_process.sendline(self.mfa_code.strip())

            # Wait for success or fail
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
                    raise Exception("Authentication failed.")

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
        messagebox.showinfo(message="Successfully connected.")
        if self.current_theme == dark_theme:
            new_image = self.disconnect_button_image_dark
        else:
            new_image = self.disconnect_button_image_light

        self.toggle_button_connect.config(image=new_image)
        self.toggle_button_connect.image = new_image
        self.canvas.itemconfig(
            self.status_text_item,
            text=" \U0001F512 - CONNECTED - ",
            font=("Arial", 18, "bold"),
            fill=self.current_theme["highlight_text"],
        )

        # Fetch the TUN IP now that we're connected
        tun_ip = self.get_tun_ip("tun0")
        if tun_ip:
            self.VPNIP = f"VPN IP: {tun_ip}"
        else:
            self.VPNIP = ""

        # Update the label
        self.canvas.itemconfig(
            self.vpnip_label_item,
            text=self.VPNIP,
            font=("Arial", 10, "bold"),
            fill=self.current_theme["fg"],
            anchor="center"
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
        self.canvas.itemconfig(self.status_text_item, text=" - DISCONNECTED -", fill="red")

        # Clear the VPN IP on disconnect
        self.VPNIP = ""
        self.canvas.itemconfig(self.vpnip_label_item, text=self.VPNIP)

    def reset_buttons(self):
        self.toggle_button_connect.config(state="normal")

    # -----------------------------------------------------------------
    # MFA POPUP
    # -----------------------------------------------------------------
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

    # -----------------------------------------------------------------
    # THEME TOGGLE
    # -----------------------------------------------------------------
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

        # Toggle button icon
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

        # File text, status text, etc.
        self.canvas.itemconfig(self.config_text_item, fill=self.current_theme["filetext"])
        self.canvas.itemconfig(self.sent_label_item, fill=self.current_theme["fg"])
        self.canvas.itemconfig(self.received_label_item, fill=self.current_theme["fg"])

        # Update "VPN STATUS" text color
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

        self.username_entry.config(bg=self.current_theme["bg_input"], fg=self.current_theme["fg_input"])
        self.password_entry.config(bg=self.current_theme["bg_input"], fg=self.current_theme["fg_input"])


# ---------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = OpenVPNClientApp(root)
    root.title("OpenVPN - Linux Client (Bundled)")
    root.geometry("330x575")
    root.resizable(False, False)
    root.mainloop()
