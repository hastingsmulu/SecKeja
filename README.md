# SecKeja
House Security System Using Raspberry Pi Pico W, Mini PIR sensor, 16x2 LCD with I2C, A Buzzer and   Magnetic Reed Switch
# SecKeja - Advanced Home Security System


A sophisticated home security system built on Raspberry Pi Pico W featuring multi-sensor monitoring, web interface, keypad access control, and real-time alerts.

## 🚀 Advanced Features

- **Multi-Sensor Integration**: Door, window, and motion detection with MC-38 magnetic sensors and MH-SR602 PIR
- **Web Dashboard**: Real-time monitoring via responsive web interface
- **Keypad Access Control**: 4x3 matrix keypad for secure system arming/disarming
- **Smart Arming Logic**: 30-second exit delay with pre-arm safety checks
- **Audible Alarms**: PWM-controlled buzzer with distinct alert patterns
- **Time Synchronization**: Automatic NTP time sync with timezone support
- **Security Codes**: Auto-generated 5-digit codes with expiration
- **LCD Status Display**: 16x2 I2C LCD for local status monitoring

## 🛠 Hardware Components

### Core Components
- Raspberry Pi Pico W
- 16x2 LCD Display with I2C Module (0x27/0x3F)
- Mini PIR Motion Sensor (MH-SR602)
- Magnetic Reed Switches (MC-38) ×2
- 4x3 Matrix Keypad
- Buzzer (PWM compatible)
- Tactile Button (Arm/Disarm)
- Jumper Wires & Breadboard
- Power Supply

### Pin Configuration
| Component | GPIO Pin | Physical Pin | Purpose |
|-----------|----------|--------------|---------|
| LCD I2C SDA | GP0 | Pin 1 | LCD Data |
| LCD I2C SCL | GP1 | Pin 2 | LCD Clock |
| Door Sensor | GP2 | Pin 4 | MC-38 Magnetic Switch |
| Window Sensor | GP3 | Pin 5 | MC-38 Magnetic Switch |
| PIR Sensor | GP4 | Pin 6 | MH-SR602 Motion |
| Buzzer | GP5 | Pin 7 | PWM Alarm |
| Keypad Rows | GP6-9 | Pins 9-12 | 4x3 Matrix Rows |
| Keypad Cols | GP10-12 | Pins 14-16 | 4x3 Matrix Columns |
| Arm Button | GP13 | Pin 17 | System Arm/Disarm |

## 📋 Prerequisites

- Raspberry Pi Pico W with MicroPython firmware
- `pico_i2c_lcd` library for LCD control
- Network connection for NTP and web interface
- Thonny IDE or similar development environment

## 🔧 Installation & Setup

### 1. Hardware Assembly

1. **LCD Display**:
   - Connect VCC to 3.3V, GND to GND
   - SDA to GP0, SCL to GP1

2. **Security Sensors**:
   - Door MC-38: GP2 with pull-up resistor
   - Window MC-38: GP3 with pull-up resistor  
   - PIR MH-SR602: GP4 (VCC=3.3V, GND=GND)

3. **User Interface**:
   - Keypad rows: GP6, GP7, GP8, GP9
   - Keypad columns: GP10, GP11, GP12 (with pull-down)
   - Arm button: GP13 with pull-up resistor
   - Buzzer: GP5 (PWM)

### 2. Software Configuration

1. **Upload Required Files**:
   - `main.py` (main security system)
   - `pico_i2c_lcd.py` (LCD library)

2. **Configure WiFi**:
   ```python
   WIFI_SSID = "your_wifi_SSID"
   WIFI_PASSWORD = "your_wifi_password"
   ```

3. **Set Timezone**:
   ```python
   TIMEZONE_OFFSET =   # Adjust for your timezone
   ```

### 3. Initial Startup

1. Power on the system
2. Watch for WiFi connection status on LCD
3. System will sync time via NTP
4. Web server starts automatically
5. Test sensors during initialization

## 🎮 System Operation

### Arming the System

1. **Pre-arm Check**: Ensure all entry points are closed and no motion detected
2. **Press Arm Button**: GP13 button starts 30-second countdown
3. **Exit Premises**: Leave during countdown period
4. **System Armed**: Monitors all sensors continuously

### Disarming Options

1. **Keypad Code**: Enter 5-digit security code (displayed on web interface)
2. **Arm Button**: Physical button press (when not in alarm state)
3. **Web Interface**: Monitor status remotely

### Alarm Triggers

- **Door/Window Open**: When system is armed
- **Motion Detection**: When system is armed and entry points secure
- **Multiple Failed Codes**: After 3 incorrect attempts

## 🌐 Web Interface

Access the system via: `http://[PICO_IP_ADDRESS]:80`

### Dashboard Features
- Real-time sensor status with color-coded alerts
- Security code display with countdown timer
- Arming countdown visualization  
- Keypad entry status
- System information and statistics
- Auto-refresh every 30 seconds

## ⚙️ Configuration Options

### Security Settings
```python
ARMING_DELAY = 30           # 30-second exit delay
CODE_VALIDITY_TIME = 300    # 5-minute code validity
MAX_ATTEMPTS = 3            # Maximum failed code attempts
TIMEZONE_OFFSET = 3         # Timezone adjustment
```

### Sensor Settings
```python
DOOR_SENSOR_PIN = 2
WINDOW_SENSOR_PIN = 3  
PIR_SENSOR_PIN = 4
BUZZER_PIN = 5
ARM_BUTTON_PIN = 13
```

## 📁 Project Structure

```
SecKeja/
├── main.py                 # Main security system code
├── pico_i2c_lcd.py        # I2C LCD control library
├── README.md              # This documentation
└── dependencies.txt       # Required libraries
```

## 🔧 Troubleshooting

### Common Issues

1. **LCD Not Displaying**:
   - Check I2C address (0x27 or 0x3F)
   - Verify SDA/SCL connections
   - Ensure proper power supply

2. **Sensors Not Triggering**:
   - Verify GPIO pin assignments
   - Check pull-up/pull-down resistors
   - Test sensor functionality individually

3. **WiFi Connection Failed**:
   - Verify SSID and password
   - Check network availability
   - Monitor connection status on LCD

4. **Web Interface Unavailable**:
   - Confirm IP address display
   - Check firewall settings
   - Verify port 80 availability

### System Indicators

- **LCD Messages**: Real-time status and errors
- **Buzzer Patterns**: Distinct sounds for different events
- **Web Dashboard**: Comprehensive system overview

## 🔄 Advanced Features

### Smart Security Logic
- Pre-arm safety checks prevent arming with open entry points
- Motion detection only triggers alarm when entry points are secure
- Automatic code regeneration for enhanced security
- Failed attempt tracking with system lockout

### Web Interface Capabilities
- Responsive design for mobile and desktop
- Real-time sensor status updates
- Security code management
- System statistics and event logging

## 🚨 Safety & Security Notes

- This is an educational project - not for critical security applications
- Always test system functionality before relying on it
- Keep security codes confidential
- Regular maintenance and testing recommended
- Consider battery backup for power outages

## 🤝 Contributing

Contributions welcome! Please feel free to submit pull requests or open issues for:
- Additional sensor support
- Enhanced web interface features
- Improved security protocols
- Bug fixes and optimizations

## 📄 License

This project is licensed under the MIT License - see details in the LICENSE file.


**Built with ❤️ using Raspberry Pi Pico W and MicroPython**

*For technical support or questions, please refer to the code comments or create an issue in the project repository.*
