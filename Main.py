# main.py - Pico W Security System with Enhanced Entry Point Protection
import network
import time
import machine
from machine import RTC, Pin, I2C
from pico_i2c_lcd import I2cLcd
import ubinascii
import ntptime
import socket
import random

# LCD Configuration
I2C_ADDR = 0x27  # Change to 0x3F if needed
I2C_NUM_ROWS = 2
I2C_NUM_COLS = 16

# Initialize I2C and LCD
i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=400000)
lcd = I2cLcd(i2c, I2C_ADDR, I2C_NUM_ROWS, I2C_NUM_COLS)

# WiFi Configuration
WIFI_SSID = "your_wifi_SSID"
WIFI_PASSWORD = "your_wifi_password"

# Timezone offset in hours
TIMEZONE_OFFSET = 1  # Change this to your timezone

# Web server configuration
WEB_PORT = 80

# Door Sensor Configuration - MC-38
DOOR_SENSOR_PIN = 2  # GP2 - Physical Pin 4
door_sensor = Pin(DOOR_SENSOR_PIN, Pin.IN, Pin.PULL_UP)

# Window Sensor Configuration - MC-38
WINDOW_SENSOR_PIN = 3  # GP3 - Physical Pin 5
window_sensor = Pin(WINDOW_SENSOR_PIN, Pin.IN, Pin.PULL_UP)

# PIR Motion Sensor Configuration - MH-SR602
PIR_SENSOR_PIN = 4  # GP4 - Physical Pin 6
pir_sensor = Pin(PIR_SENSOR_PIN, Pin.IN)

# Buzzer Configuration
BUZZER_PIN = 5  # GP5 - Physical Pin 7
buzzer = machine.PWM(machine.Pin(BUZZER_PIN))

# Arm Button Configuration
ARM_BUTTON_PIN = 13  # GP13 - Physical Pin 17
arm_button = Pin(ARM_BUTTON_PIN, Pin.IN, Pin.PULL_UP)

# Keypad Configuration (4x3 matrix - 4 rows, 3 columns)
ROWS = [6, 7, 8, 9]    # GP6, GP7, GP8, GP9 (Pins 9, 10, 11, 12)
COLS = [10, 11, 12]    # GP10, GP11, GP12 (Pins 14, 15, 16)

# Keypad matrix layout for 4x3 keypad
KEYPAD_MAP = [
    ['1', '2', '3'],
    ['4', '5', '6'],
    ['7', '8', '9'],
    ['*', '0', '#']
]

# Initialize keypad rows as outputs, cols as inputs with pull-down
row_pins = [Pin(pin, Pin.OUT) for pin in ROWS]
col_pins = [Pin(pin, Pin.IN, Pin.PULL_DOWN) for pin in COLS]

# Security system variables
door_status = "UNKNOWN"
window_status = "UNKNOWN"
motion_status = "NO MOTION"
door_last_state = None
window_last_state = None
motion_last_state = None
door_change_count = 0
window_change_count = 0
motion_detection_count = 0
last_motion_time = 0
buzzer_active = False
alarm_triggered = False
alarm_start_time = 0

# System arming variables
system_armed = False
arming_in_progress = False
arm_countdown_start = 0
ARMING_DELAY = 30  # 30 seconds arming delay
last_button_press = 0
button_debounce_delay = 0.5  # 500ms debounce

# Keypad and security code variables
security_code = ""
entered_code = ""
code_generation_time = 0
CODE_VALIDITY_TIME = 300  # 5 minutes in seconds
MAX_ATTEMPTS = 3
failed_attempts = 0
last_keypress_time = 0
keypad_enabled = False

# Get Pico W MAC Address for identification only
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
pico_mac_address = ubinascii.hexlify(wlan.config('mac')).decode()
print(f"Pico W MAC: {pico_mac_address}")

def connect_wifi():
    """Connect to WiFi with status display"""
    lcd.clear()
    lcd.putstr("Connecting...")
    
    if not wlan.isconnected():
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        
        # Wait for connection with timeout
        max_wait = 20
        while max_wait > 0:
            if wlan.isconnected():
                break
            max_wait -= 1
            lcd.move_to(0, 1)
            lcd.putstr(" " * 16)  # Clear second line
            lcd.move_to(0, 1)
            lcd.putstr(f"Wait:{max_wait}")
            time.sleep(1)
    
    if wlan.isconnected():
        lcd.clear()
        lcd.putstr("WiFi Connected!")
        lcd.move_to(0, 1)
        lcd.putstr(f"IP:{wlan.ifconfig()[0]}")
        print(f"Connected to {WIFI_SSID}")
        print(f"IP Address: {wlan.ifconfig()[0]}")
        time.sleep(2)
        return True
    else:
        lcd.clear()
        lcd.putstr("WiFi Failed!")
        print("Failed to connect to WiFi")
        return False

def sync_time_ntp():
    """Synchronize time using NTP with timezone adjustment"""
    try:
        lcd.clear()
        lcd.putstr("Syncing NTP...")
        
        # Set NTP server
        ntptime.host = "pool.ntp.org"
        
        # Synchronize time with NTP server (this sets UTC time)
        ntptime.settime()
        
        # Apply timezone offset
        if TIMEZONE_OFFSET != 0:
            rtc = machine.RTC()
            current_time = rtc.datetime()
            year, month, day, weekday, hour, minute, second, subsecond = current_time
            
            # Adjust hour for timezone
            hour = (hour + 3) % 24
            
            # Update RTC with timezone-adjusted time
            rtc.datetime((year, month, day, weekday, hour, minute, second, subsecond))
        
        lcd.clear()
        lcd.putstr("NTP Sync OK!")
        print("Time successfully synchronized via NTP")
        time.sleep(1)
        return True
        
    except Exception as e:
        lcd.clear()
        lcd.putstr("NTP Sync Failed")
        lcd.move_to(0, 1)
        error_msg = str(e)
        if "ETIMEDOUT" in error_msg:
            lcd.putstr("Timeout")
        else:
            lcd.putstr(error_msg[:16])
        print(f"NTP Error: {e}")
        time.sleep(2)
        return False

def check_arm_button():
    """Check arm button with debounce"""
    global last_button_press, arming_in_progress, system_armed, arm_countdown_start
    
    current_time = time.time()
    
    # Check if button is pressed (LOW when pressed with pull-up)
    if arm_button.value() == 0 and (current_time - last_button_press) > button_debounce_delay:
        last_button_press = current_time
        print("Arm button pressed")
        
        # If system is not armed and not already arming, start arming process
        if not system_armed and not arming_in_progress:
            # Check if entry points are closed and no motion detected
            if (door_status == "CLOSED" and window_status == "CLOSED" and 
                motion_status == "NO MOTION"):
                
                arming_in_progress = True
                arm_countdown_start = current_time
                print("Arming sequence started - 30 second countdown")
                
                # Beep to acknowledge arming start
                for _ in range(2):
                    buzzer.freq(1000)
                    buzzer.duty_u16(20000)
                    time.sleep(0.1)
                    buzzer.duty_u16(0)
                    time.sleep(0.1)
                    
            else:
                # Cannot arm - conditions not met
                print("Cannot arm system - check entry points and motion")
                lcd.clear()
                lcd.putstr("Cannot Arm!")
                if door_status != "CLOSED":
                    lcd.move_to(0, 1)
                    lcd.putstr("Close Door")
                elif window_status != "CLOSED":
                    lcd.move_to(0, 1)
                    lcd.putstr("Close Window")
                elif motion_status != "NO MOTION":
                    lcd.move_to(0, 1)
                    lcd.putstr("Motion Detected")
                time.sleep(2)
        
        # If system is armed, disarm it
        elif system_armed and not arming_in_progress:
            system_armed = False
            alarm_triggered = False
            buzzer_active = False
            buzzer.duty_u16(0)
            print("System disarmed by button")
            lcd.clear()
            lcd.putstr("System")
            lcd.move_to(0, 1)
            lcd.putstr("DISARMED")
            time.sleep(2)

def update_arming_status():
    """Update arming countdown and check if arming is complete"""
    global arming_in_progress, system_armed
    
    if arming_in_progress:
        current_time = time.time()
        time_remaining = ARMING_DELAY - (current_time - arm_countdown_start)
        
        if time_remaining > 0:
            # Still in countdown - display remaining time
            lcd.clear()
            lcd.putstr("Arming System...")
            lcd.move_to(0, 1)
            lcd.putstr(f"Exit in: {int(time_remaining)}s")
            
            # Check if conditions are still valid during countdown
            if (door_status != "CLOSED" or window_status != "CLOSED" or 
                motion_status != "NO MOTION"):
                # Conditions violated - cancel arming
                arming_in_progress = False
                print("Arming cancelled - conditions violated")
                lcd.clear()
                lcd.putstr("Arming")
                lcd.move_to(0, 1)
                lcd.putstr("CANCELLED")
                
                # Beep pattern for cancellation
                for _ in range(3):
                    buzzer.freq(800)
                    buzzer.duty_u16(25000)
                    time.sleep(0.2)
                    buzzer.duty_u16(0)
                    time.sleep(0.1)
                time.sleep(2)
                
        else:
            # Countdown complete - system is now armed
            arming_in_progress = False
            system_armed = True
            print("System ARMED and ready")
            
            # Beep pattern for armed confirmation
            for _ in range(3):
                buzzer.freq(1500)
                buzzer.duty_u16(20000)
                time.sleep(0.1)
                buzzer.duty_u16(0)
                time.sleep(0.05)
            
            lcd.clear()
            lcd.putstr("SYSTEM ARMED")
            lcd.move_to(0, 1)
            lcd.putstr("Monitoring...")
            time.sleep(2)

def generate_security_code():
    """Generate a new 5-digit security code"""
    global security_code, code_generation_time
    security_code = ''.join(str(random.randint(0, 9)) for _ in range(5))
    code_generation_time = time.time()
    print(f"New security code generated: {security_code}")
    return security_code

def is_security_code_valid():
    """Check if the current security code is still valid"""
    if not security_code:
        return False
    return (time.time() - code_generation_time) < CODE_VALIDITY_TIME

def read_keypad():
    """Read keypad input and return pressed key"""
    global last_keypress_time
    
    for row_idx, row_pin in enumerate(row_pins):
        # Set current row high
        for rp in row_pins:
            rp.value(0)
        row_pin.value(1)
        
        # Check each column
        for col_idx, col_pin in enumerate(col_pins):
            if col_pin.value() == 1:
                # Debounce
                current_time = time.time()
                if current_time - last_keypress_time > 0.3:  # 300ms debounce
                    last_keypress_time = current_time
                    # Return the corresponding key
                    return KEYPAD_MAP[row_idx][col_idx]
                time.sleep(0.1)  # Additional debounce delay
    
    return None

def handle_keypad_input():
    """Handle keypad input for security code entry"""
    global entered_code, failed_attempts, alarm_triggered, buzzer_active, keypad_enabled, system_armed
    
    if not keypad_enabled:
        return
    
    key = read_keypad()
    
    if key:
        print(f"Key pressed: {key}")
        
        if key == '#':
            # Submit code
            if entered_code == security_code and is_security_code_valid():
                # Correct code - disarm alarm
                alarm_triggered = False
                system_armed = False
                buzzer_active = False
                buzzer.duty_u16(0)
                failed_attempts = 0
                entered_code = ""
                keypad_enabled = False
                print("Alarm disarmed with correct code!")
                lcd.clear()
                lcd.putstr("Alarm DISARMED")
                lcd.move_to(0, 1)
                lcd.putstr("System Secure")
                time.sleep(3)
            else:
                # Incorrect code
                failed_attempts += 1
                entered_code = ""
                print(f"Invalid code! Attempt {failed_attempts}/{MAX_ATTEMPTS}")
                lcd.clear()
                lcd.putstr("INVALID CODE!")
                lcd.move_to(0, 1)
                lcd.putstr(f"Try {failed_attempts}/{MAX_ATTEMPTS}")
                time.sleep(2)
                
                if failed_attempts >= MAX_ATTEMPTS:
                    # Too many failed attempts - lockout
                    lcd.clear()
                    lcd.putstr("TOO MANY TRIES")
                    lcd.move_to(0, 1)
                    lcd.putstr("SYSTEM LOCKED")
                    print("System locked due to too many failed attempts")
                    time.sleep(5)
                    keypad_enabled = False
                    
        elif key == '*':
            # Clear entered code
            entered_code = ""
            print("Code entry cleared")
            lcd.clear()
            lcd.putstr("Code Cleared")
            time.sleep(1)
            
        elif key in '0123456789':
            # Digit pressed
            if len(entered_code) < 5:
                entered_code += key
                print(f"Code entered: {entered_code} (Displaying: {'*' * len(entered_code)})")
                
                # Show asterisks on LCD as user types
                lcd.clear()
                lcd.putstr("Enter Code:")
                lcd.move_to(0, 1)
                
                # Show asterisks for entered digits
                display_code = '*' * len(entered_code)
                lcd.putstr(display_code)
                
                # Add a blinking cursor if not all digits entered
                if len(entered_code) < 5:
                    lcd.putstr('_')
                
                # Brief display to show the update
                time.sleep(0.3)

def read_door_sensor():
    """Read the door sensor and return status"""
    global door_status, door_last_state, door_change_count, alarm_triggered, keypad_enabled
    
    current_state = door_sensor.value()
    
    if current_state == 0:
        new_status = "CLOSED"
        status_emoji = ""
    else:
        new_status = "OPEN"
        status_emoji = ""
    
    # Detect state change
    if new_status != door_last_state:
        door_change_count += 1
        door_last_state = new_status
        print(f"Door status changed to: {new_status}")
        
        # Trigger alarm if system is armed and door is opened
        if system_armed and new_status == "OPEN" and not alarm_triggered:
            alarm_triggered = True
            alarm_start_time = time.time()
            keypad_enabled = True
            generate_security_code()  # Generate new code for disarm
            print("ALARM TRIGGERED! Door opened while armed.")
    
    door_status = new_status
    return new_status, status_emoji

def read_window_sensor():
    """Read the window sensor and return status"""
    global window_status, window_last_state, window_change_count, alarm_triggered, keypad_enabled
    
    current_state = window_sensor.value()
    
    if current_state == 0:
        new_status = "CLOSED"
        status_emoji = ""
    else:
        new_status = "OPEN"
        status_emoji = ""
    
    # Detect state change
    if new_status != window_last_state:
        window_change_count += 1
        window_last_state = new_status
        print(f"Window status changed to: {new_status}")
        
        # Trigger alarm if system is armed and window is opened
        if system_armed and new_status == "OPEN" and not alarm_triggered:
            alarm_triggered = True
            alarm_start_time = time.time()
            keypad_enabled = True
            generate_security_code()  # Generate new code for disarm
            print("ALARM TRIGGERED! Window opened while armed.")
    
    window_status = new_status
    return new_status, status_emoji

def read_motion_sensor():
    """Read the PIR motion sensor and return status"""
    global motion_status, motion_last_state, motion_detection_count, last_motion_time, alarm_triggered, keypad_enabled
    
    current_state = pir_sensor.value()
    
    if current_state == 1:
        new_status = "MOTION DETECTED"
        status_emoji = ""
        
        # Only count new motion events (not continuous detection)
        if new_status != motion_last_state:
            motion_detection_count += 1
            last_motion_time = time.time()
            print("Motion detected!")
            
            # Trigger alarm if system is armed and all entry points are closed
            if system_armed and door_status == "CLOSED" and window_status == "CLOSED" and not alarm_triggered:
                alarm_triggered = True
                alarm_start_time = time.time()
                keypad_enabled = True
                generate_security_code()  # Generate new code for disarm
                print("ALARM TRIGGERED! Motion detected while armed.")
                
    else:
        new_status = "NO MOTION"
        status_emoji = ""
    
    # Detect state change
    if new_status != motion_last_state:
        motion_last_state = new_status
        print(f"Motion status: {new_status}")
    
    motion_status = new_status
    return new_status, status_emoji

def read_all_sensors():
    """Read all sensors"""
    door_status, door_emoji = read_door_sensor()
    window_status, window_emoji = read_window_sensor()
    motion_status, motion_emoji = read_motion_sensor()
    return door_status, door_emoji, window_status, window_emoji, motion_status, motion_emoji

def control_buzzer():
    """Control buzzer based on alarm state"""
    global buzzer_active
    
    if alarm_triggered and not buzzer_active:
        # Activate buzzer - alternating tones for alarm effect
        buzzer_active = True
        print("Alarm buzzer activated!")
        
    elif alarm_triggered and buzzer_active:
        # Continue alarm sound
        for freq in [1000, 1500]:
            buzzer.freq(freq)
            buzzer.duty_u16(30000)  # 50% volume
            time.sleep(0.3)
            buzzer.duty_u16(0)  # Brief pause
            time.sleep(0.1)
            
    elif buzzer_active and not alarm_triggered:
        # Stop buzzer
        buzzer.duty_u16(0)
        buzzer_active = False
        print("Alarm buzzer deactivated")

def get_security_status():
    """Get overall security status"""
    door_status, _, window_status, _, motion_status, _ = read_all_sensors()
    
    # Determine security level
    if alarm_triggered:
        return "ALARM TRIGGERED", "", "#ff0000"  # Red - highest alert
    elif system_armed:
        return "SYSTEM ARMED", "", "#ff9500"  # Orange - armed and ready
    elif arming_in_progress:
        return "ARMING...", "", "#4a86e8"  # Blue - arming in progress
    elif door_status == "OPEN" or window_status == "OPEN":
        return "UNSECURE", "", "#ff9500"  # Orange - unsecured
    elif motion_status == "MOTION DETECTED":
        return "ACTIVE", "", "#4a86e8"  # Blue - motion but open entry
    else:
        return "READY TO ARM", "", "#51cf66"  # Green - ready to arm

def generate_random_digits():
    """Generate 5 random digits"""
    return ''.join(str(random.randint(0, 9)) for _ in range(5))

def format_time(hour, minute, second):
    """Format time as HH:MM:SS"""
    return f"{hour:02d}:{minute:02d}:{second:02d}"

def format_date(year, month, day):
    """Format date as YYYY-MM-DD"""
    return f"{year:04d}-{month:02d}-{day:02d}"

def get_day_name(weekday):
    """Convert weekday number to name"""
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    return days[weekday] if 0 <= weekday < len(days) else "Unknown"

def get_current_datetime():
    """Get current date and time as formatted strings"""
    rtc = machine.RTC()
    current_time = rtc.datetime()
    year, month, day, weekday, hour, minute, second, subsecond = current_time
    
    time_str = format_time(hour, minute, second)
    date_str = format_date(year, month, day)
    day_str = get_day_name(weekday)
    
    return time_str, date_str, day_str

def display_current_time():
    """Display current time and date on LCD"""
    time_str, date_str, day_str = get_current_datetime()
    
    lcd.clear()
    lcd.putstr(time_str.center(16))
    lcd.move_to(0, 1)
    display_line = f"{date_str} {day_str[:3]}"
    lcd.putstr(display_line.center(16))

def display_alarm_status():
    """Display alarm status on LCD"""
    if alarm_triggered:
        lcd.clear()
        lcd.putstr("ALARM TRIGGERED!")
        lcd.move_to(0, 1)
        if keypad_enabled:
            # Show code entry status with asterisks
            lcd.putstr("Code:" + '*' * len(entered_code))
            # Add cursor if not all digits entered
            if len(entered_code) < 5:
                lcd.putstr('_')
        else:
            lcd.putstr("System Locked")
    elif arming_in_progress:
        # Handled in update_arming_status()
        pass
    elif keypad_enabled and not alarm_triggered:
        lcd.clear()
        lcd.putstr("Enter Code:")
        lcd.move_to(0, 1)
        lcd.putstr('*' * len(entered_code))
        # Add cursor if not all digits entered
        if len(entered_code) < 5:
            lcd.putstr('_')
    elif system_armed:
        lcd.clear()
        lcd.putstr("SYSTEM ARMED")
        lcd.move_to(0, 1)
        lcd.putstr("Monitoring...")

def create_web_page():
    """Create the HTML web page with all sensors and status"""
    time_str, date_str, day_str = get_current_datetime()
    random_digits = generate_random_digits()
    door_status, door_emoji = read_door_sensor()
    window_status, window_emoji = read_window_sensor()
    motion_status, motion_emoji = read_motion_sensor()
    security_status, security_emoji, security_color = get_security_status()
    
    # Calculate time since last motion and code expiry
    time_since_motion = int(time.time() - last_motion_time) if last_motion_time > 0 else "N/A"
    code_expiry = int(CODE_VALIDITY_TIME - (time.time() - code_generation_time)) if security_code and is_security_code_valid() else 0
    
    # Calculate arming countdown if in progress
    arming_countdown = 0
    if arming_in_progress:
        arming_countdown = max(0, ARMING_DELAY - (time.time() - arm_countdown_start))
    
    # Determine status colors
    door_color = "#ff6b6b" if door_status == "OPEN" else "#51cf66"
    window_color = "#ff6b6b" if window_status == "OPEN" else "#51cf66"
    motion_color = "#ff6b6b" if motion_status == "MOTION DETECTED" else "#51cf66"
    
    html = """<!DOCTYPE html>
<html>
<head>
    <title>Pico W Security System</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { 
            font-family: Arial, sans-serif; 
            text-align: center; 
            margin: 20px; 
            background: linear-gradient(135deg, #353638 0%, #292929 100%);
            color: white;
            min-height: 100vh;
        }
        .container {
            background: rgba(255,255,255,0.1);
            padding: 25px;
            border-radius: 15px;
            backdrop-filter: blur(10px);
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            max-width: 800px;
            margin: 0 auto;
        }
        .security-status {
            font-size: 1.8em;
            margin: 15px 0;
            padding: 15px;
            border-radius: 10px;
            background: rgba(255,255,255,0.2);
            border: 3px solid """ + security_color + """;
            font-weight: bold;
        }
        .arming-section {
            margin: 20px 0;
            padding: 20px;
            background: rgba(255,255,255,0.15);
            border-radius: 10px;
            border: 2px solid #4a86e8;
        }
        .arming-timer {
            font-size: 2.5em;
            font-weight: bold;
            color: #4a86e8;
            margin: 10px 0;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .disarm-section {
            margin: 20px 0;
            padding: 20px;
            background: rgba(255,255,255,0.15);
            border-radius: 10px;
            border: 2px solid #ffeb3b;
        }
        .security-code {
            font-size: 3em;
            font-weight: bold;
            color: #ffeb3b;
            margin: 10px 0;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            letter-spacing: 5px;
        }
        .code-info {
            font-size: 1em;
            margin: 10px 0;
            color: #a8e6cf;
        }
        .keypad-display {
            margin: 15px 0;
            padding: 15px;
            background: rgba(0,0,0,0.3);
            border-radius: 10px;
            font-family: monospace;
        }
        .entered-code {
            font-size: 2em;
            letter-spacing: 10px;
            margin: 10px 0;
        }
        .sensors-grid {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 15px;
            margin: 20px 0;
        }
        .sensor-card {
            padding: 20px;
            border-radius: 10px;
            background: rgba(255,255,255,0.15);
            transition: all 0.3s ease;
            min-height: 120px;
        }
        .sensor-alert {
            background: rgba(255,107,107,0.3);
            border: 2px solid #ff6b6b;
            animation: pulse 1s infinite;
        }
        .sensor-normal {
            background: rgba(81,207,102,0.3);
            border: 2px solid #51cf66;
        }
        .sensor-warning {
            background: rgba(255,149,0,0.3);
            border: 2px solid #ff9500;
        }
        .sensor-emoji {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        .sensor-name {
            font-size: 1.1em;
            font-weight: bold;
            margin: 5px 0;
        }
        .sensor-status {
            font-size: 1em;
            margin: 5px 0;
            font-weight: bold;
        }
        .sensor-counter {
            font-size: 0.8em;
            color: #ddd;
            margin-top: 8px;
        }
        .buzzer-status {
            margin: 15px 0;
            padding: 10px;
            border-radius: 8px;
            background: rgba(255,255,255,0.2);
            font-weight: bold;
        }
        .buzzer-active {
            background: rgba(255,0,0,0.3);
            color: #ff6b6b;
        }
        .buzzer-inactive {
            background: rgba(81,207,102,0.3);
        }
        .keypad-status {
            margin: 15px 0;
            padding: 10px;
            border-radius: 8px;
            background: rgba(255,255,255,0.2);
        }
        .attempts-warning {
            color: #ff6b6b;
            font-weight: bold;
        }
        .arm-button-info {
            margin: 15px 0;
            padding: 10px;
            border-radius: 8px;
            background: rgba(255,255,255,0.2);
            font-size: 0.9em;
        }
        .time {
            font-size: 2em;
            margin: 10px 0;
        }
        .date {
            font-size: 1.5em;
            margin: 10px 0;
        }
        .day {
            font-size: 1.2em;
            margin: 10px 0;
            color: #a8e6cf;
        }
        .info {
            margin-top: 20px;
            font-size: 0.9em;
            color: #ccc;
            border-top: 1px solid rgba(255,255,255,0.2);
            padding-top: 15px;
        }
        .refresh-btn {
            background: #4ecdc4;
            color: white;
            border: none;
            padding: 12px 25px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 1em;
            margin: 10px 5px;
            transition: background 0.3s;
        }
        .refresh-btn:hover {
            background: #45b7af;
        }
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.7; }
            100% { opacity: 1; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Home Security System</h1>
        
        <!-- Security Status -->
        <div class="security-status">
            <div style="font-size: 1.2em;">System Status</div>
            <div style="font-size: 1.5em; color: """ + security_color + """;">
                """ + security_emoji + """ """ + security_status + """
            </div>
        </div>
        
        <!-- Arming Section -->
        """ + ("""
        <div class="arming-section">
            <h2>⏱️ ARMING IN PROGRESS</h2>
            <div class="arming-timer" id="armingTimer">
                """ + str(int(arming_countdown)) + """s
            </div>
            <div class="code-info">
                Exit the premises now!<br>
                System will arm in <span id="armingSeconds">""" + str(int(arming_countdown)) + """</span> seconds
            </div>
        </div>
        """ if arming_in_progress else "") + """
        
        <!-- Disarm Section -->
        """ + ("""
        <div class="disarm-section">
            <h2> ALARM ACTIVE - DISARM REQUIRED</h2>
            <div class="security-code" id="securityCode">
                """ + (security_code if is_security_code_valid() else "EXPIRED") + """
            </div>
            <div class="code-info">
                """ + ("Enter this code on keypad to disarm" if is_security_code_valid() else "Code expired - new motion required") + """
                <br>Expires in: """ + str(code_expiry) + """ seconds
                <br>Failed attempts: """ + str(failed_attempts) + """ / """ + str(MAX_ATTEMPTS) + """
            </div>
            
            <!-- Keypad Entry Display -->
            <div class="keypad-display">
                <h3> Keypad Entry</h3>
                <div class="entered-code">
                    """ + ('*' * len(entered_code)) + (('_' * (5 - len(entered_code))) if len(entered_code) < 5 else "") + """
                </div>
                <div class="code-info">
                    Digits entered: """ + str(len(entered_code)) + """ / 5<br>
                    Press # to submit | Press * to clear
                </div>
            </div>
        </div>
        """ if alarm_triggered else "") + """
        
        <!-- Buzzer Status -->
        <div class="buzzer-status """ + ('buzzer-active' if buzzer_active else 'buzzer-inactive') + """">
             Buzzer: """ + ('ACTIVE' if buzzer_active else 'INACTIVE') + """
        </div>
        
        <!-- Keypad Status -->
        <div class="keypad-status">
            Keypad: """ + ('ENABLED - Enter code #' if keypad_enabled else 'DISABLED') + """
            """ + ("""<br><span class="attempts-warning">Failed attempts: """ + str(failed_attempts) + """</span>""" if failed_attempts > 0 else "") + """
        </div>
        
        <!-- Arm Button Info -->
        <div class="arm-button-info">
             Arm Button: GP""" + str(ARM_BUTTON_PIN) + """ | """ + ("ENTER PASSWORD TO DISARM" if system_armed else "PRESS BUTTON TO ARM") + """
            <br>Arming requires: All entry points CLOSED + NO MOTION
        </div>
        
        <!-- Sensors Grid -->
        <div class="sensors-grid">
            <!-- Door Sensor -->
            <div class="sensor-card """ + ('sensor-alert' if door_status == 'OPEN' else 'sensor-normal') + """">
                <div class="sensor-emoji">""" + door_emoji + """</div>
                <div class="sensor-name">Front Door</div>
                <div class="sensor-status" style="color: """ + door_color + """;">
                    """ + door_status + """
                </div>
                <div class="sensor-counter">Changes: """ + str(door_change_count) + """</div>
            </div>
            
            <!-- Window Sensor -->
            <div class="sensor-card """ + ('sensor-alert' if window_status == 'OPEN' else 'sensor-normal') + """">
                <div class="sensor-emoji">""" + window_emoji + """</div>
                <div class="sensor-name">Window</div>
                <div class="sensor-status" style="color: """ + window_color + """;">
                    """ + window_status + """
                </div>
                <div class="sensor-counter">Changes: """ + str(window_change_count) + """</div>
            </div>
            
            <!-- Motion Sensor -->
            <div class="sensor-card """ + ('sensor-warning' if motion_status == 'MOTION DETECTED' else 'sensor-normal') + """">
                <div class="sensor-emoji">""" + motion_emoji + """</div>
                <div class="sensor-name">Motion Sensor</div>
                <div class="sensor-status" style="color: """ + motion_color + """;">
                    """ + motion_status + """
                </div>
                <div class="sensor-counter">
                    Detections: """ + str(motion_detection_count) + """<br>
                    Last: """ + str(time_since_motion) + """s ago
                </div>
            </div>
        </div>
        
        <!-- Random Digits Section -->
        <div class="security-code" id="randomDigits">
            """ + random_digits + """
        </div>
        
        <!-- Time Information -->
        <div class="time" id="currentTime">
             """ + time_str + """
        </div>
        
        <div class="date" id="currentDate">
            """ + date_str + """
        </div>
        
        <div class="day" id="currentDay">
            """ + day_str + """
        </div>
        
        <!-- Refresh Button -->
        <button class="refresh-btn" onclick="location.reload()">
             Refresh Status
        </button>
        
        <!-- System Information -->
        <div class="info">
            <p> Door: GP""" + str(DOOR_SENSOR_PIN) + """ | 🪟 Window: GP""" + str(WINDOW_SENSOR_PIN) + """ | ️ Motion: GP""" + str(PIR_SENSOR_PIN) + """ |  Buzzer: GP""" + str(BUZZER_PIN) + """ |  Arm Button: GP""" + str(ARM_BUTTON_PIN) + """</p>
            <p> Keypad: Rows[GP""" + str(ROWS[0]) + """,GP""" + str(ROWS[1]) + """,GP""" + str(ROWS[2]) + """,GP""" + str(ROWS[3]) + """] Cols[GP""" + str(COLS[0]) + """,GP""" + str(COLS[1]) + """,GP""" + str(COLS[2]) + """]</p>
            <p>️ Server: Raspberry Pi Pico W |  MAC: """ + pico_mac_address + """</p>
            <p> IP: """ + wlan.ifconfig()[0] + """ |  Auto-refresh every 30 seconds</p>
        </div>
    </div>
    
    <script>
        // Auto-refresh page every 30 seconds
        setTimeout(function() {
            location.reload();
        }, 30000);
        
        // Add urgency effect for alert sensors
        document.querySelectorAll('.sensor-alert, .sensor-warning').forEach(sensor => {
            setInterval(() => {
                sensor.style.transform = sensor.style.transform ? '' : 'scale(1.02)';
            }, 800);
        });
        
        // Update arming timer every second
        """ + ("""
        setInterval(function() {
            const timerElement = document.getElementById('armingTimer');
            const secondsElement = document.getElementById('armingSeconds');
            let remainingTime = """ + str(int(arming_countdown)) + """ - 1;
            if (remainingTime <= 0) {
                location.reload(); // Refresh when countdown completes
            } else {
                timerElement.textContent = remainingTime + 's';
                secondsElement.textContent = remainingTime;
            }
        }, 1000);
        """ if arming_in_progress else "") + """
        
        // Update code expiry timer every second
        """ + ("""
        setInterval(function() {
            const codeElement = document.getElementById('securityCode');
            const codeInfo = document.querySelector('.code-info');
            let expiryTime = """ + str(code_expiry) + """ - 1;
            if (expiryTime <= 0) {
                codeElement.textContent = 'EXPIRED';
                codeInfo.innerHTML = 'Code expired - new motion required<br>Failed attempts: """ + str(failed_attempts) + """ / """ + str(MAX_ATTEMPTS) + """';
            } else {
                codeInfo.innerHTML = 'Enter this code on keypad to disarm<br>Expires in: ' + expiryTime + ' seconds<br>Failed attempts: """ + str(failed_attempts) + """ / """ + str(MAX_ATTEMPTS) + """';
            }
        }, 1000);
        """ if alarm_triggered else "") + """
    </script>
</body>
</html>"""
    return html

def start_web_server():
    """Start the web server"""
    try:
        # Create socket
        addr = socket.getaddrinfo('0.0.0.0', WEB_PORT)[0][-1]
        server_socket = socket.socket()
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(addr)
        server_socket.listen(1)
        
        print(f"Web server started on http://{wlan.ifconfig()[0]}:{WEB_PORT}")
        
        # Display server info on LCD
        lcd.clear()
        lcd.putstr("Web Server ON")
        lcd.move_to(0, 1)
        lcd.putstr(f"Port:{WEB_PORT}")
        time.sleep(2)
        
        return server_socket
        
    except Exception as e:
        print(f"Failed to start web server: {e}")
        lcd.clear()
        lcd.putstr("Server Error")
        lcd.move_to(0, 1)
        lcd.putstr(str(e)[:16])
        return None

def handle_web_requests(server_socket):
    """Handle incoming web requests"""
    try:
        while True:
            # Check for client connection with timeout
            try:
                server_socket.settimeout(1.0)  # 1 second timeout
                client, addr = server_socket.accept()
            except OSError:
                # Timeout occurred, continue to check display and sensors
                return True  # Continue running
            
            print(f"Client connected from: {addr}")
            
            # Receive request
            request = client.recv(1024)
            request_str = request.decode('utf-8')
            print(f"Request: {request_str.split('\\r\\n')[0]}")
            
            # Generate and send response
            response = create_web_page()
            client.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
            client.send(response)
            client.close()
            
            print("Response sent to client")
            
    except Exception as e:
        print(f"Error handling web request: {e}")
        return True  # Continue running

def display_welcome():
    """Display welcome message"""
    lcd.clear()
    lcd.putstr("Security System")
    lcd.move_to(0, 1)
    lcd.putstr("Arm Button Ready")
    time.sleep(2)

def test_sensors():
    """Test all sensors during startup"""
    lcd.clear()
    lcd.putstr("Testing Sensors")
    door_status, door_emoji = read_door_sensor()
    window_status, window_emoji = read_window_sensor()
    motion_status, motion_emoji = read_motion_sensor()
    lcd.move_to(0, 1)
    lcd.putstr(f"D:{door_status[0]} W:{window_status[0]} M:{motion_status[0]}")
    print(f"Initial test - Door: {door_status}, Window: {window_status}, Motion: {motion_status}")
    time.sleep(2)

def main():
    """Main program loop"""
    # Display welcome message
    display_welcome()
    
    # Test all sensors
    test_sensors()
    
    # Connect to WiFi
    if not connect_wifi():
        # If WiFi fails, show error and retry every 30 seconds
        while True:
            lcd.clear()
            lcd.putstr("WiFi Failed")
            lcd.move_to(0, 1)
            lcd.putstr("Retry in 30s")
            time.sleep(30)
            if connect_wifi():
                break
    
    # Synchronize time with NTP
    if not sync_time_ntp():
        # If NTP sync fails, retry every 2 minutes
        while True:
            lcd.clear()
            lcd.putstr("NTP Sync Fail")
            lcd.move_to(0, 1)
            lcd.putstr("Retry in 2m")
            time.sleep(120)
            if sync_time_ntp():
                break
    
    # Start web server
    server_socket = start_web_server()
    if not server_socket:
        print("Failed to start web server")
        return
    
    # Main security loop
    last_sync = time.time()
    last_display_update = time.time()
    last_motion_check = time.time()
    last_keypad_check = time.time()
    last_button_check = time.time()
    sync_interval = 3600  # Sync every hour
    display_interval = 0.5  # Update display every 0.5 seconds
    motion_check_interval = 0.1  # Check motion every 100ms
    keypad_check_interval = 0.05  # Check keypad every 50ms
    button_check_interval = 0.1  # Check button every 100ms
    
    while True:
        current_time = time.time()
        
        # Update display at regular intervals
        if current_time - last_display_update >= display_interval:
            if arming_in_progress:
                update_arming_status()
            elif alarm_triggered or keypad_enabled or system_armed:
                display_alarm_status()
            else:
                display_current_time()
            last_display_update = current_time
        
        # Check arm button
        if current_time - last_button_check >= button_check_interval:
            check_arm_button()
            last_button_check = current_time
        
        # Check motion sensor frequently
        if current_time - last_motion_check >= motion_check_interval:
            read_all_sensors()
            control_buzzer()
            last_motion_check = current_time
        
        # Check keypad input frequently
        if current_time - last_keypad_check >= keypad_check_interval:
            handle_keypad_input()
            last_keypad_check = current_time
        
        # Handle web requests (non-blocking)
        if not handle_web_requests(server_socket):
            break
        
        # Check if it's time to resync time
        if current_time - last_sync >= sync_interval:
            lcd.clear()
            lcd.putstr("Resyncing NTP...")
            if sync_time_ntp():
                last_sync = current_time
            else:
                last_sync = current_time - sync_interval + 600

# Run the program
try:
    main()
except KeyboardInterrupt:
    # Stop buzzer and cleanup
    buzzer.duty_u16(0)
    lcd.clear()
    lcd.putstr("System stopped")
    print("Security system stopped by user")
except Exception as e:
    # Stop buzzer and cleanup
    buzzer.duty_u16(0)
    lcd.clear()
    lcd.putstr("Fatal Error")
    lcd.move_to(0, 1)
    lcd.putstr("Reset...")
    print(f"Fatal error: {e}")
    time.sleep(5)
    machine.reset()
