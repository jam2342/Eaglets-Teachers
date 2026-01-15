# initially writen for proximity_and_color_v1.0

from machine import I2C, Pin
import time
from apds9960 import APDS9960 

# 1. Setup I2C and Pins
i2c = I2C(1, sda=Pin(18), scl=Pin(19), freq=400000)
int_pin = Pin(21, Pin.IN, Pin.PULL_UP) # Physical Pin 27

sensor = APDS9960(i2c)

print("System Online. Swipe over sensor...")

try:  
    while True:
        prox = sensor.get_proximity()
        clear, r, g, b = sensor.get_color()
        
        # Formatted Output
        output = "Prox: {:3} | R: {:3} G: {:3} B: {:3} | Ambient: {:5}".format(
            prox, r, g, b, clear
        )
        print(output, end="\r") # Use \r to update the same line in terminal
        
        time.sleep(0.1)
            
except KeyboardInterrupt:
    print("\nStopping...")
except Exception as e:
    print(f"\nError: {e}")