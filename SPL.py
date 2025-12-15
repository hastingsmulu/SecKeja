/*
 * Scheduled Perimeter Light (SPL)
 * Arduino Nano Sketch for 4-Channel PIR Motion Sensing System
 *
 * FUNCTION:
 * 1. Reads time from a DS1302 RTC module.
 * 2. Activates sensor processing only between 7 PM (19:00) and 7 AM (07:00).
 * 3. Monitors four independent HC-SR501 PIR sensors.
 * 4. Activates a corresponding OMRON SSR for each sensor upon detection.
 * 5. Keeps the light ON for a minimum duration (defined by LIGHT_ON_DURATION_SECONDS).
 * 6. Ensures all lights are OFF outside of the scheduled window.
 */

#include <DS1302RTC.h> // Library for the DS1302 RTC module

// --- PIN DEFINITIONS ---
// DS1302 RTC Pins (connected to Digital Pins D2, D3, D4)
// NOTE: You must use a library compatible with the DS1302, like the "DS1302RTC" library.
const int kCePin   = 4;  // RST/CE pin (Chip Enable)
const int kIoPin   = 3;  // DAT/I/O pin (Data Input/Output)
const int kSclkPin = 2;  // CLK pin (Clock)
DS1302RTC rtc(kCePin, kIoPin, kSclkPin);

// PIR SENSOR INPUT PINS (Long-distance signals coming in)
const int PIR_PINS[] = {5, 6, 7, 8}; // D5, D6, D7, D8

// SSR RELAY OUTPUT PINS (Connected to the 4-channel SSR module)
// Ensure these pins match the inputs (e.g., PIR 1 controls Relay 1)
const int RELAY_PINS[] = {9, 10, 11, 12}; // D9, D10, D11, D12

const int NUM_SENSORS = 4; // Total number of sensors/lights

// --- TIMING AND CONTROL VARIABLES ---
// Light will stay on for this duration after the last motion is detected
const int LIGHT_ON_DURATION_SECONDS = 300; // 5 minutes (300 seconds)

// Stores the time (in milliseconds) when each light should turn OFF
unsigned long lightTimer[NUM_SENSORS]; 

// --- TIME WINDOW DEFINITIONS (24-Hour Format) ---
const int ACTIVATE_HOUR = 19; // 7 PM
const int DEACTIVATE_HOUR = 7; // 7 AM


// =================================================================
// SETUP
// =================================================================
void setup() {
  Serial.begin(9600);
  
  // Set all PIR pins as INPUT
  for (int i = 0; i < NUM_SENSORS; i++) {
    pinMode(PIR_PINS[i], INPUT);
  }

  // Set all Relay pins as OUTPUT
  // IMPORTANT: Solid State Relays (SSRs) are typically activated by LOW and deactivated by HIGH.
  // Verify your specific OMRON module's logic. We assume HIGH = OFF here.
  for (int i = 0; i < NUM_SENSORS; i++) {
    pinMode(RELAY_PINS[i], OUTPUT);
    digitalWrite(RELAY_PINS[i], HIGH); // Turn all lights OFF initially (HIGH)
    lightTimer[i] = 0; // Initialize timers to zero
  }
  
  // --- RTC Initialization ---
  Serial.println("System Initialized.");
  // NOTE: You must upload a separate "setTime" sketch once to set the correct time on the DS1302.
}


// =================================================================
// MAIN LOOP
// =================================================================
void loop() {
  
  // PART 1: TIME CHECK (The Gatekeeper)
  Time t;
  rtc.getTime(t); // Read the current time
  
  // Check if current hour is within the active window (7 PM to 7 AM)
  // (19, 20, 21, 22, 23) OR (0, 1, 2, 3, 4, 5, 6)
  bool isNightTime = (t.hour >= ACTIVATE_HOUR || t.hour < DEACTIVATE_HOUR);

  if (isNightTime) {
    // NIGHT TIME: Process sensors and control lights
    checkSensorsAndControlLights();
  } else {
    // DAY TIME: Ensure ALL lights are OFF and reset timers
    for (int i = 0; i < NUM_SENSORS; i++) {
      // Turn OFF the light (send HIGH)
      digitalWrite(RELAY_PINS[i], HIGH); 
      // Reset timer so it doesn't immediately turn on again at 7 PM
      lightTimer[i] = 0; 
    }
    // Small delay to reduce CPU usage during the long inactive period
    delay(100); 
  }
}


// =================================================================
// SENSOR AND LIGHT CONTROL FUNCTION
// =================================================================
void checkSensorsAndControlLights() {
  // Use millis() for non-blocking timing
  unsigned long currentTime = millis(); 

  for (int i = 0; i < NUM_SENSORS; i++) {
    
    // 1. Read the PIR sensor state (HIGH = Motion Detected)
    int sensorState = digitalRead(PIR_PINS[i]);

    // 2. Check for motion
    if (sensorState == HIGH) {
      // Motion detected: Recalculate the turn-off time
      // timer is set to current time PLUS the duration needed (converted to milliseconds)
      lightTimer[i] = currentTime + ((unsigned long)LIGHT_ON_DURATION_SECONDS * 1000UL);
      
      // Turn the corresponding light ON (send LOW)
      digitalWrite(RELAY_PINS[i], LOW); 
    }

    // 3. Check if the light's timer has expired
    // The light should only turn OFF if the current time has passed the lightTimer value
    if (currentTime > lightTimer[i] && lightTimer[i] != 0) {
      // Timer expired: Turn the light OFF (send HIGH)
      digitalWrite(RELAY_PINS[i], HIGH); 
      lightTimer[i] = 0; // Clear the timer after turning off
    }
    
    // NOTE: The delay() is intentionally omitted here to ensure rapid, non-blocking 
    // checks for all four sensors and smooth timing.
  }
}
