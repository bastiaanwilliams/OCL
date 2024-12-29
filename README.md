# OCL

OpenVPN MFA Linux Client 

A user-friendly OpenVPN client for Linux with MFA/2FA support, built with Python3 and Tkinter. This application provides an intuitive graphical interface for 
managing OpenVPN connections, including features like configuration file selection, authentication handling (including MFA), network traffic monitoring, 
and theme customization.

Features
Easy Configuration: Browse and select your OpenVPN .ovpn configuration files effortlessly.
Secure Authentication: Enter your username and password securely, with support for Multi-Factor Authentication (MFA).
Real-Time Traffic Monitoring: Monitor the total amount of data sent and received since the VPN connection was established.
Theme Customization: Toggle between light and dark themes to suit your preferences.
Splash Screen: A sleek splash screen that can be disabled for future launches.
Cross-Platform Compatibility: Designed to work seamlessly on most Linux distributions.
See screenshots.

Install Pythonm modules with pip3 preferable in a virtual environment:
python3 -m venv venv
source venv/bin/activate
pip3 install Pillow
pip3 install pexpect
pip3 install psutils
pip3 install screeninfo


Requirements
-Python 3.6 or higher
-Python Libraries and Pip Modules

The following Python libraries and pip modules are required to run the OpenVPN Linux Client:

Standard Libraries:

-tkinter (usually comes pre-installed with Python on most Linux distributions)
-json
-pathlib
-os
-re
-subprocess
-queue
-time
-threading
-Third-Party Libraries:

-Pillow (pip install Pillow)
-pexpect (pip install pexpect)
-psutil (pip install psutil)
-screeninfo (pip install screeninfo)

Installation of Dependencies:
Before running the application, ensure that all required libraries are installed. 
You can install the necessary pip modules using the following command:


pip3 install Pillow pexpect psutil screeninfo
Note: tkinter is typically included with Python on most Linux distributions. 
If it's not installed, you can install it using your distribution's package manager. 
For example, on Debian/Ubuntu-based systems:


sudo apt-get install python3-tk
Installation
Clone the Repository


git clone https://github.com/yourusername/openvpn-linux-client.git
cd openvpn-linux-client
Install Dependencies

As mentioned in the Requirements section, install the necessary pip modules:


pip3 install Pillow pexpect psutil screeninfo
Ensure OpenVPN is Installed

The client relies on the OpenVPN binary. Install OpenVPN using your distribution's package manager if it's not already installed.

Debian/Ubuntu:
sudo apt-get update
sudo apt-get install openvpn

Fedora:
sudo dnf install openvpn

Arch Linux:
sudo pacman -S openvpn
Prepare OpenVPN Configuration

Obtain your .ovpn configuration file from your VPN provider and ensure it's accessible on your system.

Usage
Run the Application

Navigate to the project directory and execute the main Python script:

python3 openvpn_client.py
Upon launching, a splash screen will appear. You can choose to disable it for future launches by checking the "Don't show splash next time" checkbox.

Select Configuration File:
Click the Browse button to locate and select your OpenVPN .ovpn configuration file.
The selected configuration path will be displayed. If the path is too long, it will wrap to ensure readability.
Enter Credentials

Username: Enter your VPN username.
Password: Enter your VPN password. The input is masked for security.
Connect to VPN

Click the Connect button to initiate the VPN connection.
If Multi-Factor Authentication (MFA) is required, a popup will appear prompting you to enter your 2FA code.
Monitor Network Traffic

Once connected, the application will display the total amount of data sent and received since the connection was established.

Toggle Theme:
Use the theme toggle button to switch between light and dark themes based on your preference.
Disconnect from VPN

Click the Disconnect button to terminate the VPN connection.
Configuration
The application stores its configuration in a JSON file located at ~/.openvpn_client/config.json. T
his file includes settings like whether to show the splash screen on startup.

Example config.json:
json
Copy code
{
    "show_splash": false
}
To reset the configuration, you can delete the config.json file, and the application will recreate it with default settings upon the next launch.

Contributing
Contributions are welcome! If you encounter any issues or have suggestions for improvements, please open an issue or submit a pull request.

Fork the Repository
Create a New Branch
git checkout -b feature/YourFeatureName
Make Your Changes
Commit Your Changes
git commit -m "Add some feature"
Push to the Branch
git push origin feature/YourFeatureName
Open a Pull Request

License
This project is licensed under the GPL License.

Acknowledgements
Python
Tkinter
Pillow
pexpect
psutil
screeninfo

