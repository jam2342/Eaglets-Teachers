# initially writen for gesture_recognition_v1.0

from machine import I2C, Pin
import time
# Assuming the class above is in the same file or imported
from apds9960 import APDS9960 

# 1. Setup I2C and Pins
i2c = I2C(1, sda=Pin(18), scl=Pin(19), freq=400000)
int_pin = Pin(21, Pin.IN, Pin.PULL_UP) # Physical Pin 27

sensor = APDS9960(i2c)

print("System Online. Swipe over sensor...")

while True:
    if int_pin.value() == 0:
        raw_data = sensor.read_gesture()
        result = sensor.calculate_direction(raw_data)
        
        if result:
            print(f"[{time.ticks_ms()}] GESTURE: {result}")
            # LONG SLEEP: This is the 'Cool down' period. 
            # It prevents the 'exit' of your hand from triggering a second gesture.
            time.sleep(0.4) 
            
        # Manually clear FIFO one last time before re-enabling
        while sensor.get_fifo_level() > 0:
            sensor.read_gesture()
            
    time.sleep(0.01)
