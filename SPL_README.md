This project implements a robust, scheduled security lighting controller using an Arduino Nano, four long-distance PIR motion sensors, a Real-Time Clock (RTC) module, and four Solid State Relays (SSRs).

The system is designed to overcome common challenges associated with long sensor cables, ensuring reliable operation.

## Features

* **Scheduled Activation:** The system is **ACTIVE only between 7:00 PM (19:00) and 7:00 AM (07:00)**, using a DS1302 Real-Time Clock.
* **4 Independent Channels:** Monitors and controls four separate motion-sensing zones and corresponding floodlights.
* **Long-Distance Stability:** Utilizes power stabilization techniques (capacitors, higher voltage) to ensure reliable signaling over **4-5 meter cables**.
* **Solid State Control:** Uses quiet, fast, and long-lasting OMRON Solid State Relays (SSRs) for switching AC lights.
* **Non-Blocking Logic:** Uses `millis()` for timing to ensure smooth, simultaneous operation of all four lighting channels.

## Hardware and Components

| Component | Model / Type | Quantity | Notes |
| :--- | :--- | :--- | :--- |
| **Microcontroller** | Arduino Nano V3.0 (ATmega328P) | 1 | Provides USB programming and 5V logic. |
| **PIR Sensor** | HC-SR501 | 4 | Passive Infrared Motion Detector. |
| **Real-Time Clock** | DS1302 RTC Module | 1 | Used for scheduling the ON/OFF times. |
| **Relay Module** | 5V 4-Channel OMRON SSR Module | 1 | Switches AC power to floodlights safely. |
| **Power Supply** | 12V DC (Min 1A) | 1 | Power source for the entire system. |
| **Power Converter** | DC-DC Buck Converter (12V to 5V) | 1 | Provides clean, stable 5V for the Nano and SSRs. |
| **Cable** | CAT5/CAT6 Ethernet Cable | ~5 meters x 4 | Essential for long-distance noise reduction. |
| **Capacitors** | 10µF - 100µF Electrolytic + 0.1µF Ceramic | 4 sets | **CRUCIAL** for noise filtering at each sensor. |

## Wiring Diagram and Connections

### 1. Power and Ground (The Foundation)

* **12V Power Supply:** Connects to the input of the DC-DC Buck Converter.
* **Buck Converter (Output):** Provides **5V** to the Arduino Nano (VCC pin) and the SSR Module (VCC pin).
* **HC-SR501 Power:** Connect a dedicated **12V line** from the power supply directly to the `VCC` pin of all four HC-SR501 sensors (using the long cable). This overcomes voltage drop.
* **Common Ground:** **ALL GND pins** (12V PSU, Buck Converter, Nano GND, SSR GND, all four HC-SR501 GNDs) **MUST BE CONNECTED TOGETHER**. This is essential for signal integrity.

### 2. Digital Pin Assignments (Arduino Nano)

| Pin Type | Component | Function | Arduino Pin(s) |
| :--- | :--- | :--- | :--- |
| **RTC** (Input) | DS1302 | CLK, I/O, RST | D2, D3, D4 |
| **Sensor Input** | PIR 1 - PIR 4 | Motion Signal IN | D5, D6, D7, D8 |
| **Relay Output** | SSR 1 - SSR 4 | Light Control OUT | D9, D10, D11, D12 |

### 3. Long-Cable Integrity (Crucial Steps)

To ensure the HC-SR501 signals are stable over 5 meters:

1.  **Cable:** Use a twisted pair (CAT5/CAT6) for each sensor connection.
2.  **Power Filter:** At the **sensor end** of the cable, solder a **10µF - 100µF electrolytic capacitor** and a **0.1µF ceramic capacitor** across the sensor's VCC and GND pins. 
3.  **Signal Damping:** Add a **100Ω - 220Ω resistor** in series with the `OUT` pin wire, close to the sensor.

## Software and Code

### 1. Dependencies

Install the appropriate library for the DS1302 RTC module using the Arduino Library Manager. A common library is **`DS1302RTC`**.

### 2. Initial Setup (Setting the Time)

The DS1302 chip needs to be set with the current time once. You must upload a separate, simple sketch (not the main one) to perform this initialization.

### 3. Main Sketch (`SPL.ino`)

The main code is structured to first check the time and then process sensor logic only during the active window.

The core logic uses the `lightTimer` array and `millis()` to ensure that when motion is detected, the corresponding light stays on for a minimum of 300 seconds (5 minutes), even if the sensor momentarily loses detection.

### 4. Customization

* **Schedule:** Change `ACTIVATE_HOUR` and `DEACTIVATE_HOUR` constants to adjust the active time.
* **Duration:** Change `LIGHT_ON_DURATION_SECONDS` to adjust how long the floodlights stay on after motion is detected.
* **Relay Logic:** If your SSR module activates on a HIGH signal, swap `HIGH` and `LOW` commands in the `checkSensorsAndControlLights()` function. (Currently set to **LOW = ON**).

## ⚠️ Safety Warning

**This project involves wiring components to the high-voltage (AC) side of the OMRON SSR module.**

* **Always disconnect mains power before wiring the SSR module.**
* Ensure the high-voltage and low-voltage sections are physically separated in a protective, grounded enclosure.
* If you are unfamiliar with wiring AC power, please consult a qualified electrician.
