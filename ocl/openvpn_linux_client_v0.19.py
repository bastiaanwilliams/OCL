#!/usr/bin/env python3
"""
OpenVPN Linux Client

Author: Bastiaan Williams
Email: bastiaanwilliams@protonmail.com
Date: 2024-12-12
Version: 0.19
License: GPL 3

Description:
A user-friendly OpenVPN GUI client for Linux, built with Python3 and Tkinter.
This application provides an intuitive graphical interface for managing
OpenVPN connections, including features like configuration file selection,
authentication handling (including MFA), network traffic monitoring, and 
theme customization.
"""

__author__ = "Bastiaan Williams"
__version__ = "0.19"
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
import queue
import subprocess
from screeninfo import get_monitors  # Import screeninfo
import json
from pathlib import Path

# Configuration handling
CONFIG_DIR = Path.home() / ".openvpn_client"
CONFIG_FILE = CONFIG_DIR / "config.json"

def load_config():
    """Load configuration from the config file. If not exists, return default config."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            # If the config file is corrupted, reset to default
            return {"show_splash": True}
    else:
        return {"show_splash": True}

def save_config(config):
    """Save configuration to the config file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

# Define light and dark themes
light_theme = {
    "bg": "#2772a4",
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
        self.duration = duration  # Duration in milliseconds
        self.config_data = config or {"show_splash": True}

        # Remove window decorations
        self.overrideredirect(True)

        # Load splash image
        try:
            # Convert to RGBA to preserve transparency if present
            splash_image = (
                Image.open(image_path)
                .convert("RGBA")
                .resize((400, 280), Image.Resampling.LANCZOS)
            )
            self.splash_photo = ImageTk.PhotoImage(splash_image)
        except Exception as e:
            messagebox.showerror("Splash Image Error", f"Failed to load splash image: {e}")
            self.destroy()
            parent.destroy()
            return

        # Create a canvas to hold the image and message
        self.canvas = tk.Canvas(self, width=400, height=350, highlightthickness=0)
        self.canvas.pack()

        # Display the splash image
        self.canvas.create_image(0, 0, anchor="nw", image=self.splash_photo)

        # Display the message
        self.canvas.create_text(200, 260, text=message, font=("Arial", 14), fill="white", anchor="center")

        # Add the "Don't show splash next time" checkbox
        self.dont_show_var = tk.BooleanVar(value=not self.config_data.get("show_splash", True))
        self.checkbox = tk.Checkbutton(
            self,
            text="Don't show splash next time",
            variable=self.dont_show_var,
            fg="#000000",
            selectcolor="#ffffff",
            activebackground=self.get_bg_color(),
            activeforeground=self.get_fg_color(),
            command=self.on_checkbox_toggle
        )
        self.checkbox_window = self.canvas.create_window(200, 300, window=self.checkbox, anchor="center")

        # Center the splash screen on the primary monitor
        self.center_on_primary_monitor(400, 320)  # Increased height to accommodate checkbox

        # Schedule to destroy the splash screen after the duration
        self.after(self.duration, self.destroy)

    def get_bg_color(self):
        # Assuming 'self.master' is the main window which has 'current_theme'
        if hasattr(self.master, 'current_theme'):
            return self.master.current_theme.get("bg", "#1e1e20")
        return "#1e1e20"  # Default dark background

    def get_fg_color(self):
        if hasattr(self.master, 'current_theme'):
            return self.master.current_theme.get("fg", "#ffffff")
        return "#ffffff"  # Default white foreground

    def center_on_primary_monitor(self, width, height):
        # Retrieve monitor information
        monitors = get_monitors()
        if not monitors:
            # Default to 800x600 if no monitor information is available
            x, y = 100, 100
        else:
            # Assume the first monitor is the primary monitor
            primary_monitor = monitors[0]
            x = primary_monitor.x + (primary_monitor.width - width) // 2
            y = primary_monitor.y + (primary_monitor.height - height) // 2

        self.geometry(f"{width}x{height}+{x}+{y}")

    def on_checkbox_toggle(self):
        # If the checkbox is checked, set 'show_splash' to False
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
            # Initialize the baseline byte counts
            initial = psutil.net_io_counters()
            self.initial_sent = initial.bytes_sent
            self.initial_recv = initial.bytes_recv

            while self.monitoring:
                stats = psutil.net_io_counters()

                # Calculate total bytes sent and received since monitoring started
                total_sent = (stats.bytes_sent - self.initial_sent) / (1024 * 1024)  # MB
                total_recv = (stats.bytes_recv - self.initial_recv) / (1024 * 1024)  # MB

                # Schedule GUI updates on the main thread
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
        self.root.withdraw()  # Hide the main window during splash

        # Load configuration
        self.config = load_config()

        # Initialize variables
        self.vpn_process = None
        self.monitoring = False
        self.mfa_code = None
        self.connected = False
        self.queue = queue.Queue()

        # Start with dark theme
        self.current_theme = dark_theme

        # Load images
        try:
            # Convert to RGBA to preserve transparency
            self.dark_mode_img = ImageTk.PhotoImage(
                Image.open("images/light_mode_icon.png").convert("RGBA")
                .resize((30, 30), Image.Resampling.LANCZOS)
            )
            self.light_mode_img = ImageTk.PhotoImage(
                Image.open("images/dark_mode_icon.png").convert("RGBA")
                .resize((30, 30), Image.Resampling.LANCZOS)
            )

            self.connect_button_image_dark = ImageTk.PhotoImage(
                Image.open("images/on3.png").convert("RGBA")
                .resize((70, 70), Image.Resampling.LANCZOS)
            )
            self.disconnect_button_image_dark = ImageTk.PhotoImage(
                Image.open("images/off3.png").convert("RGBA")
                .resize((70, 70), Image.Resampling.LANCZOS)
            )

            self.cover_network_image = ImageTk.PhotoImage(
                Image.open("images/cover_network.png").convert("RGBA")
                .resize((330, 160), Image.Resampling.LANCZOS)
            )

            self.connect_button_image_light = ImageTk.PhotoImage(
                Image.open("images/on3.png").convert("RGBA")
                .resize((70, 70), Image.Resampling.LANCZOS)
            )
            self.disconnect_button_image_light = ImageTk.PhotoImage(
                Image.open("images/off3.png").convert("RGBA")
                .resize((70, 70), Image.Resampling.LANCZOS)
            )

            self.logo_dark = ImageTk.PhotoImage(
                Image.open("images/openvpnlogo.png").convert("RGBA")
                .resize((290, 72), Image.Resampling.LANCZOS)
            )
            self.logo_light = ImageTk.PhotoImage(
                Image.open("images/openvpnlogo_light.png").convert("RGBA")
                .resize((290, 72), Image.Resampling.LANCZOS)
            )

            # Load background images
            self.bg_image_dark = ImageTk.PhotoImage(
                Image.open("images/background_dark.png").convert("RGBA")
                .resize((330, 650), Image.Resampling.LANCZOS)
            )
            self.bg_image_light = ImageTk.PhotoImage(
                Image.open("images/background_light.png").convert("RGBA")
                .resize((330, 650), Image.Resampling.LANCZOS)
            )
        except Exception as e:
            messagebox.showerror("Image Load Error", f"Failed to load images: {e}")
            self.root.destroy()
            return

        # Decide whether to show the splash screen based on config
        if self.config.get("show_splash", True):
            self.show_splash_screen()
        else:
            self.initialize_main_window()

    def show_splash_screen(self):
        splash = SplashScreen(self.root, "images/splash.jpg", "OpenVPN Linux Client BETA version 0.19", duration=3000, config=self.config)
        splash.update()
        # After the splash duration, proceed to initialize the main app and save the config
        self.root.after(splash.duration, self.on_splash_close, splash)

    def on_splash_close(self, splash):
        # Save the updated configuration based on the splash screen's checkbox
        save_config(self.config)
        self.initialize_main_window()

    def initialize_main_window(self):
        self.root.deiconify()  # Show the main window
        self.apply_theme(self.current_theme)
        self.create_widgets()

    def apply_theme(self, theme):
        self.current_theme = theme

    def create_widgets(self):
        # Create a canvas for everything
        self.canvas = tk.Canvas(self.root, width=330, height=575, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # Background image
        chosen_bg = self.bg_image_dark if self.current_theme == dark_theme else self.bg_image_light
        self.bg_item = self.canvas.create_image(0, 0, anchor="nw", image=chosen_bg)

        # Logo
        chosen_logo = self.logo_dark if self.current_theme == dark_theme else self.logo_light
        self.logo_item = self.canvas.create_image(20, 10, anchor="nw", image=chosen_logo)

        # Theme toggle button
        current_icon = self.dark_mode_img if self.current_theme == dark_theme else self.light_mode_img
        self.toggle_button_theme = tk.Button(
            self.canvas,
            image=current_icon,
            bg=self.current_theme["bg"],            # Normal background
            fg=self.current_theme["fg"],            # Normal foreground
            activebackground=self.current_theme["bg"],     # Match the normal background on hover
            activeforeground=self.current_theme["fg"],     # (Optional) match the normal foreground
            bd=0,
            highlightthickness=0,
            relief="flat",
            command=self.toggle_theme
        )
        self.toggle_button_theme.image = current_icon
        self.canvas.create_window(145, 110, window=self.toggle_button_theme, anchor="nw")

        # Config section
        self.canvas.create_text(
            30, 160,
            text="Select your OpenVPN Config File:",
            font=("Arial", 9),
            fill=self.current_theme["fg"],
            anchor="nw"
        )

        self.button_browse = tk.Button(
            self.canvas,
            text="Browse",
            command=self.browse_config,
            bg=self.current_theme["button_bg"],
            fg=self.current_theme["button_fg"],
            font=("Arial", 10, "bold"),
            cursor="hand2",
            highlightthickness=1,
            bd=0
        )
        self.canvas.create_window(240, 150, window=self.button_browse, anchor="nw")

        self.config_path_var = tk.StringVar(value="None")
        self.canvas.create_text(
            30, 180,
            text="Current config:",
            font=("Arial", 9),
            fill=self.current_theme["fg"],
            anchor="nw"
        )
        # Wrap the config path so it doesn't run off-screen
        self.config_text_item = self.canvas.create_text(
            120, 180,
            text=self.config_path_var.get(),
            font=("Arial", 9),
            fill=self.current_theme["filetext"],
            anchor="nw",
            width=180
        )

        # Username and Password
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

        # Connect/Disconnect Button
        current_connect_image = self.connect_button_image_dark
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

        # Network Traffic (Centered)
        self.canvas.create_text(
            165, 485,
            text="📶 Network Traffic",
            font=("Arial", 12, "bold"),
            fill="#8ec4e9",
            anchor="center"
        )

        # Sent and Received Labels
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

        # VPN Status (Centered)
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

        # Initialize Traffic Monitor (but do not start yet)
        self.traffic_monitor = TrafficMonitor(
            self.root,
            self.canvas,
            self.sent_label_item,
            self.received_label_item,
            self.current_theme
        )

    def browse_config(self):
        config_file = filedialog.askopenfilename(
            title="Select OpenVPN Config File",
            filetypes=[("OpenVPN Config Files", "*.ovpn")],
        )
        if config_file:
            self.config_path_var.set(config_file)
        else:
            self.config_path_var.set("None")

        # Update the config text item
        self.canvas.itemconfig(self.config_text_item, text=self.config_path_var.get())

    def toggle_vpn(self):
        if not self.connected:
            self.start_vpn()
        else:
            self.stop_vpn()

    def start_vpn(self):
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
            self.vpn_process = pexpect.spawn(f"/usr/sbin/openvpn --config '{config_file}'", encoding='utf-8')
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
                    raise Exception("Authentication failed. Please check your credentials.")
                    tkinter.messagebox.showwarning(title="Error", message="Authentication failed. Please check your credentials.", **options)
                if "Initialization Sequence Completed" in line:
                    self.connected = True
                    self.root.after(0, self.update_ui_on_connect)
                    break

        except Exception as e:
            print(f"VPN Error: {e}")
            messagebox.showerror("Error", f"VPN Error: {e}")
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
        if self.vpn_process:
            self.vpn_process.terminate(force=True)
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
                Image.open("images/2fa.png")
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
        mfa_entry.focus_set()  # Focus on the entry so user can type immediately

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
        else:
            self.apply_theme(dark_theme)
        self.apply_theme_to_widgets()

    def apply_theme_to_widgets(self):
        # Update background image
        if self.current_theme == dark_theme:
            self.canvas.itemconfig(self.bg_item, image=self.bg_image_dark)
        else:
            self.canvas.itemconfig(self.bg_item, image=self.bg_image_light)

        # Update the theme toggle button image
        if self.current_theme == dark_theme:
            self.toggle_button_theme.config(
                image=self.dark_mode_img,
                bg=self.current_theme["bg"],
                fg=self.current_theme["fg"],
                activebackground=self.current_theme["bg"],      # Make hover same as normal background
                activeforeground=self.current_theme["fg"]       # Make hover text same as normal foreground
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

        # Update text items on the canvas
        self.canvas.itemconfig(self.config_text_item, fill=self.current_theme["filetext"])
        self.canvas.itemconfig(self.sent_label_item, fill=self.current_theme["fg"])
        self.canvas.itemconfig(self.received_label_item, fill=self.current_theme["fg"])
        self.canvas.itemconfig(self.status_text_item, fill=self.current_theme["highlight_text"])

        # Update the "Browse" button
        self.button_browse.config(
            bg=self.current_theme["button_bg"],
            fg=self.current_theme["button_fg"],
            activebackground=self.current_theme["button_bg"],  # Match normal bg on hover
            activeforeground=self.current_theme["button_fg"]
        )

        # Update username and password entries
        self.username_entry.config(bg=self.current_theme["bg_input"], fg=self.current_theme["fg_input"])
        self.password_entry.config(bg=self.current_theme["bg_input"], fg=self.current_theme["fg_input"])

        # Decide on the correct connect/disconnect image based on connection status + theme
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

        # Update connect/disconnect button
        self.toggle_button_connect.config(
            image=new_image,
            bg=self.current_theme["bg"],
            fg=self.current_theme["fg"],
            activebackground=self.current_theme["bg"],   # Match normal bg on hover
            activeforeground=self.current_theme["fg"]
        )
        self.toggle_button_connect.image = new_image

        # Update traffic and config text colors
        self.canvas.itemconfig(self.sent_label_item, fill=self.current_theme["fg"])
        self.canvas.itemconfig(self.received_label_item, fill=self.current_theme["fg"])
        self.canvas.itemconfig(self.config_text_item, fill=self.current_theme["fg"])


if __name__ == "__main__":
    root = tk.Tk()
    # Initialize the main app, which will handle the splash screen
    app = OpenVPNClientApp(root)
    root.title("OpenVPN - Linux Client")
    root.geometry("330x575")  # Set the initial window size
    root.resizable(False, False)  # Prevent resizing
    root.mainloop()

