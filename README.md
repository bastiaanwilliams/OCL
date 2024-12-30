# OCL

<b>OpenVPN Linux Client with MFA/2FA support.</b><br/>
<br/>
A very simple user-friendly OpenVPN client for Linux with MFA/2FA support, built with Python3 and Tkinter. This application provides a graphical interface for 
managing OpenVPN connections, including features like configuration file selection, authentication handling (including MFA), network traffic monitoring, 
and theme customization.<br/><br/>


![Alt text](https://github.com/bastiaanwilliams/OCL/blob/main/screenshot1.png)
![Alt text](https://github.com/bastiaanwilliams/OCL/blob/main/screenshot2.png)
![Alt text](https://github.com/bastiaanwilliams/OCL/blob/main/screenshot3.png)
![Alt text](https://github.com/bastiaanwilliams/OCL/blob/main/screenshot4.png)
![Alt text](https://github.com/bastiaanwilliams/OCL/blob/main/screenshot5.png)

<b>Features:</b><br/>
Easy Configuration: Browse and select your OpenVPN .ovpn configuration files effortlessly.
Secure Authentication: Enter your username and password securely, with support for Multi-Factor Authentication (MFA).
Real-Time Traffic Monitoring: Monitor the total amount of data sent and received since the VPN connection was established.
Theme Customization: Toggle between light and dark themes to suit your preferences.
Splash Screen: A sleek splash screen that can be disabled for future launches.
Cross-Platform Compatibility: Designed to work seamlessly on most Linux distributions.
See screenshots.<br/>
<br/>

Install Pythonm modules with pip3 preferable in a virtual environment:<br/>
python3 -m venv venv<br/>
source venv/bin/activate<br/>
pip3 install Pillow<br/>
pip3 install pexpect<br/>
pip3 install psutils<br/>
pip3 install screeninfo<br/>
<br/>

Requirements<br/>
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

Third-Party Libraries:<br/><br/>
<br/>
-Pillow (pip install Pillow)<br/>
-pexpect (pip install pexpect)<br/>
-psutil (pip install psutil)<br/>
-screeninfo (pip install screeninfo)<br/>
<br/><br/>
Installation of Dependencies:<br/>
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
<br/><br/>
The client relies on the OpenVPN binary. Install OpenVPN using your distribution's package manager if it's not already installed.
<br/>
Debian/Ubuntu:<br/>
sudo apt-get update<br/>
sudo apt-get install openvpn<br/>
<br/><br/>
Fedora:<br/>
sudo dnf install openvpn<br/>
<br/><br/>
Arch Linux:<br/>
sudo pacman -S openvpn<br/>
Prepare OpenVPN Configuration<br/>
<br/><br/>
Obtain your .ovpn configuration file from your VPN provider and ensure it's accessible on your system.

<b>Usage:</b><br/>
Run the Application:<br/>
Copy the project folder (ocl) to your computer. Navigate to the project directory and execute the main Python script:<br/>
python3 openvpn_client.py<br/>
<br/>
Or use the executable:<br/>
(Create with Nuitka: python3 -m nuitka --onefile --enable-plugin=tk-inter openvpn_linux_client.py)<br/>
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


