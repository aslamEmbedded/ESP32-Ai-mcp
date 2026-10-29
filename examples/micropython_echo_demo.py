"""
MicroPython ESP32 Interactive Demo
Upload this as 'main.py' to your ESP32 to test bidirectional serial I/O.
"""

import time
import sys
from machine import Pin

# On most ESP32 boards, onboard LED is GPIO 2
led = Pin(2, Pin.OUT)

print("\n--- ESP32 MicroPython Ready ---")
print("Listening for serial commands: 'LED_ON', 'LED_OFF', 'STATUS', 'PING'")

counter = 0

while True:
    # Heartbeat output every 5 seconds
    counter += 1
    if counter % 50 == 0:
        print(f"[ESP32 Heartbeat] Uptime cycles: {counter}")
    
    # Non-blocking check for serial input
    time.sleep(0.1)
