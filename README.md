![Alt text](https://github.com/bastiaanwilliams/OCL/blob/main/logo.png) </br>
<b>OpenVPN Client Gui for Linux with MFA/2FA support.</b><br/>
<br/>
A very simple user-friendly OpenVPN client for Linux with MFA/2FA support, built with Python3 and Tkinter. This application provides a graphical interface for 
the cli openvpn client (/usr/bin/openvpn) on Linux. Managing OpenVPN connections including features like configuration file selection, 
authentication handling (including MFA/2FA), network traffic monitoring, dark/light theme, store credentials savely (through keyring) etc.<br/><br/>
<br/><br/>
<b><b>Newest Version 1.8.2</b> – Added a menu structure and updated style/themes</b><br/>
The newest version of the OCL code includes a menu (top bar) with entries for:<br/>
Add Config File<br/>
About<br/>
Settings<br/>
Quit<br/><br/>
The Settings menu item opens a themed Settings window, letting you enable/disable the splash screen and pick between Dark or Light themes.
After saving, these preferences are written to a JSON file (config.json) in ~/.openvpn_client/, and the theme is applied instantly to the entire interface.
On relaunch, the app remembers these preferences, so it continues in the chosen theme and respects the splash screen setting.
This design provides a user-friendly and persistent settings experience, allowing users to customize the look and feel of your OpenVPN Linux Client with minimal effort.<br/><br/>
<b>Version 1.0 – New Bundled OpenVPN Approach</b><br/>
<br/>In this v1.0 release, OCL now bundles its own OpenVPN client binary inside a dedicated bin/ folder, rather than relying on a system-wide installation of OpenVPN. This change provides the following benefits:<br/>
<br/>
Self-Contained: Users no longer need to install OpenVPN separately; the client executable (version OpenVPN 2.5.9 x86_64-pc-linux-gnu [SSL (OpenSSL)] [LZO] [LZ4] [EPOLL] [PKCS11] [MH/PKTINFO] [AEAD] built on Feb 14 2023) is included within the bin distribution.<br/>
Consistent Version: Every user runs the exact same version of OpenVPN, preventing version mismatches across different systems or distros.<br/>
Easier Setup: Fewer prerequisites—just clone the repository (or unzip the release package) and run the script.<br/><br/>
Folder Structure<br/>
scss<br/>
Copy code<br/>
my_openvpn_app/<br/>
├── bin/<br/>
│   ├── openvpn         (Linux binary)<br/>
│   ├── openvpn.exe     (Windows binary, if needed)<br/>
│   └── openvpn_macos   (Mac binary, if needed)<br/>
├── images/<br/>
│   ├── background_dark.png<br/>
│   ├── background_light.png<br/>
│   ├── ...<br/>
├── openvpn_gui.py (Main program)<br/>
├── README.md<br/>
└── ...<br/><br/>
bin/: Holds the compiled OpenVPN binaries (one per supported platform).><br/>
images/: Contains UI images (like backgrounds, icons, logos).<br/>
openvpn_gui.py: Main Python script that calls bin/openvpn instead of relying on /usr/sbin/openvpn.<br/><br/>
<b>How It Works</b><br/>
Startup: When you run openvpn_gui.py, it detects your operating system (Windows, macOS, Linux, etc.) and chooses the appropriate binary from bin/.<br/>
Connection: The script spawns the bundled OpenVPN binary (openvpn.exe or openvpn) with your chosen .ovpn configuration.<br/>
No System Dependencies: You do not need to install OpenVPN via package managers—everything is self-contained here.<br/><br/>
License & Compliance<br/>
Because OpenVPN is licensed under the GPLv2, we include its binaries and provide (or offer) corresponding source code. Check our LICENSE_OPENVPN file for details, or see the official OpenVPN GitHub for source code and additional licensing information.<br/>
<br/><br/>
![Alt text](https://github.com/bastiaanwilliams/OCL/blob/main/screenshot2.png)
![Alt text](https://github.com/bastiaanwilliams/OCL/blob/main/screenshot1.png)



<b>Features:</b><br/>
Easy Configuration: Browse and select your OpenVPN .ovpn configuration files effortlessly.
Secure Authentication: Enter your username and password securely, with support for Multi-Factor Authentication (MFA).
Real-Time Traffic Monitoring: Monitor the total amount of data sent and received since the VPN connection was established.
Theme Customization: Toggle between light and dark themes to suit your preferences.
Splash Screen: A sleek splash screen that can be disabled for future launches.
Cross-Platform Compatibility: Designed to work seamlessly on most Linux distributions.
See screenshots.<br/>
<br/><br/>
Used Modules:<br/>
import tkinter as tk<br/>
from tkinter import filedialog, messagebox<br/>
from PIL import Image, ImageTk<br/>
import threading<br/>
import pexpect<br/>
import psutil<br/>
import time<br/>
import re<br/>
import os<br/>
import netifaces<br/>
import sys<br/>
import queue<br/>
import json<br/>
import keyring
from pathlib import Path<br/>
from screeninfo import get_monitors<br/>
import platform<br/>
<br/>
# ---- NEW IMPORTS FOR ENCRYPTION ----<br/>
from cryptography.fernet import Fernet<br/>
<br/><br/><br/>
<b>Install Pythonm modules with pip3 preferable in a virtual environment:</b><br/>
python3 -m venv venv<br/>
source venv/bin/activate<br/>
pip3 install Pillow<br/>
pip3 install pexpect<br/>
pip3 install psutils<br/>
pip3 install screeninfo<br/>
pip3 install netifaces<br/>
pip3 install cryptography<br/>
pip3 install keyring<br/>
<br/>

<b>Requirements</b><br/>
-Python 3.6 or higher<br/>
-Python Libraries and Pip Modules<br/>
<br/>
The following Python libraries and pip modules are required to run the OpenVPN Linux Client:
<br/>
Standard Libraries:<br/>
<br/>
-tkinter (usually comes pre-installed with Python on most Linux distributions)<br/>
-json<br/>
-pathlib<br/>
-os<br/>
-re<br/>
-subprocess<br/>
-queue<br/>
-time<br/>
-threading<br/>

<b>Third-Party Libraries:</b><br/><br/>
<br/>
-Pillow (pip install Pillow)<br/>
-pexpect (pip install pexpect)<br/>
-psutil (pip install psutil)<br/>
-screeninfo (pip install screeninfo)<br/>
<br/><br/>
<b>Installation of Dependencies:</b><br/>
Before running the application, ensure that all required libraries are installed. <br/>
You can install the necessary pip modules using the following command:<br/>
<br/><br/>
pip3 install Pillow pexpect psutil screeninfo<br/>
Note: tkinter is typically included with Python on most Linux distributions. <br/>
If it's not installed, you can install it using your distribution's package manager. <br/>
For example, on Debian/Ubuntu-based systems:<br/>
<br/><br/>
sudo apt-get install python3-tk<br/>
Installation<br/>
Clone the Repository<br/>
<br/>
git clone https://github.com/yourusername/openvpn-linux-client.git<br/>
cd openvpn-linux-client<br/>
Install Dependencies<br/>
<br/><br/>
As mentioned in the Requirements section, install the necessary pip modules:<br/>
<br/><br/>
pip3 install Pillow pexpect psutil screeninfo<br/>
Ensure OpenVPN is Installed<br/>
<br/>
<b>NOTE: </b>The client relies on the OpenVPN binary. Install OpenVPN using your distribution's package manager if it's not already installed.
<br/>
<b>Debian/Ubuntu:</b><br/>
sudo apt-get update<br/>
sudo apt-get install openvpn<br/>
<br/>
<b>Fedora:</b><br/>
sudo dnf install openvpn<br/>
<br/>
<b>Arch Linux:</b><br/>
sudo pacman -S openvpn<br/>
Prepare OpenVPN Configuration<br/>
<br/>
Obtain your .ovpn configuration file from your VPN provider and ensure it's accessible on your system.

<b>Usage:</b><br/>
Run the Application:<br/>
Copy the project folder (ocl) to your computer. Navigate to the project directory and execute the main Python script:<br/>
python3 openvpn_client.py<br/>
<br/>
Or use the executable:<br/>
(Create with Nuitka: python3 -m nuitka --onefile --enable-plugin=tk-inter --include-data-dir=./images=./images --include-data-dir=./bin=./bin openvpn_linux_client.py)<br/>
<br/>
./openvpn_linux_client.bin<br/>
<br/>
Select Configuration File:<br/>
Click the Browse button to locate and select your OpenVPN .ovpn configuration file.<br/>
The selected configuration path will be displayed. If the path is too long, it will wrap to ensure readability.<br/>
<br/><br/>
Enter Credentials:<br/>
Username: Enter your VPN username.<br/>
Password: Enter your VPN password. The input is masked for security.<br/>
Connect to VPN<br/>
<br/>
Click the Connect button to initiate the VPN connection.<br/>
If Multi-Factor Authentication (MFA) is required, a popup will appear prompting you to enter your 2FA code.<br/>
<br/>
Monitor Network Traffic:<br/>
Once connected, the application will display the total amount of data sent and received since the connection was established.
<br/><br/>
Toggle Theme:<br/>
Use the theme toggle button to switch between light and dark themes based on your preference.<br/>
<br/><br/>
Disconnect from VPN:<br/>
Click the Disconnect button to terminate the VPN connection.<br/>
<br/><br/>
Configuration:<br/>
The application stores its configuration in a JSON file located at ~/.openvpn_client/config.json. <br/>
This file includes settings like whether to show the splash screen on startup.<br/>
<br/><br/>
Example config.json:<br/>
json<br/>
Copy code<br/>
{<br/>
    "show_splash": false<br/>
}<br/>
To reset the configuration, you can delete the config.json file, and the application will recreate it with default settings upon the next launch.<br/>
<br/><br/>
Contributing:<br/>
Contributions are welcome! If you encounter any issues or have suggestions for improvements, please open an issue or submit a pull request.<br/>
<br/><br/>
Fork the Repository<br/>
Create a New Branch<br/>
git checkout -b feature/YourFeatureName<br/>
Make Your Changes<br/>
Commit Your Changes<br/>
git commit -m "Add some feature"<br/>
Push to the Branch<br/>
git push origin feature/YourFeatureName<br/>
Open a Pull Request<br/>
<br/><br/>


