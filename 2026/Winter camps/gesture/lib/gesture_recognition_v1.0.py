__version__ = "1.0"

from machine import I2C, Pin
import time

class APDS9960:
    # Key Addresses
    ADDRESS = 0x39
    
    # Registers (from Adafruit/Datasheet)
    ENABLE   = 0x80 # Power, Proximity, ALS, Gesture
    ID       = 0x92 # Device ID
    GSTATUS  = 0xAF
    GFLVL    = 0xAE
    GFIFO_U  = 0xFC
    GCONF4   = 0xAB
    
    # Initialization constants matching Adafruit's Defaults
    DEFAULTS = {
        0xA0: b'\x05', # GPENTH: Enter gesture engine at >= 5 prox
        0xA1: b'\x1E', # GEXTH: Exit gesture engine if counts drop < 30
        0xA2: b'\x82', # GCONF1: 8 datasets to trigger INT
        0xA3: b'\x41', # GCONF2: Gain 4x, 100mA LED
        0xA6: b'\x85', # GPULSE: 16us, 6 pulses
        0xAB: b'\x02', # GCONF4: GIEN=1 (Interrupts enabled)
    }

    def __init__(self, i2c):
        self.i2c = i2c
        # Verify ID (should be 0xAB for APDS9960)
        self._verify_sensor()
        
        self.reset()
        self._setup_sensor()

    def _write(self, reg, val):
        self.i2c.writeto_mem(self.ADDRESS, reg, val)

    def _verify_sensor(self):
        """Check if sensor is connected and correct ID."""
        for _ in range(3):
            try:
                device_id = self.i2c.readfrom_mem(self.ADDRESS, self.ID, 1)[0]
                if device_id == 0xAB:
                    return
            except OSError:
                time.sleep(0.1)
        raise RuntimeError("APDS-9960 not found. Check wiring/address.")
    
    def reset(self):
        self._write(self.ENABLE, b'\x00') # Power OFF
        time.sleep(0.025)
        self._write(self.ENABLE, b'\x01') # Power ON (PON)
        time.sleep(0.01)

    def _setup_sensor(self):
        # Load the defaults used in the Adafruit library
        for reg, val in self.DEFAULTS.items():
            self._write(reg, val)
        # Enable Proximity and Gesture engines
        self._write(self.ENABLE, b'\x45') # PON, PEN, GEN
        # Force Gesture Mode ON
        self._write(self.GCONF4, b'\x03')

    def is_gesture_valid(self):
        status = self.i2c.readfrom_mem(self.ADDRESS, self.GSTATUS, 1)[0]
        return status & 0x01

    def get_fifo_level(self):
        return self.i2c.readfrom_mem(self.ADDRESS, self.GFLVL, 1)[0]

    def read_gesture(self):
        level = self.get_fifo_level()
        if level > 0:
            return self.i2c.readfrom_mem(self.ADDRESS, self.GFIFO_U, level * 4)
        return None
    
    def calculate_direction(self, raw_data):
        """
        Time-Slice Logic: Compares the very beginning of the swipe 
        to the very end to determine true vector.
        """
        # Each dataset is 4 bytes. We need at least 4 datasets (16 bytes)
        if not raw_data or len(raw_data) < 16:
            return None

        # 1. Grab the "Start" of the gesture (First 3 datasets)
        s_u, s_d, s_l, s_r = 0, 0, 0, 0
        for i in range(0, 12, 4):
            s_u += raw_data[i]
            s_d += raw_data[i+1]
            s_l += raw_data[i+2]
            s_r += raw_data[i+3]

        # 2. Grab the "End" of the gesture (Last 3 datasets)
        e_u, e_d, e_l, e_r = 0, 0, 0, 0
        last_idx = len(raw_data) - 12
        for i in range(last_idx, len(raw_data), 4):
            e_u += raw_data[i]
            e_d += raw_data[i+1]
            e_l += raw_data[i+2]
            e_r += raw_data[i+3]

        # 3. Calculate the Delta (How the signal shifted over time)
        ud_delta = (e_d - s_d) - (e_u - s_u)
        lr_delta = (e_r - s_r) - (e_l - s_l)

        abs_ud = abs(ud_delta)
        abs_lr = abs(lr_delta)

        # 4. Filter and Determine
        # We ignore the 'weak' axis to prevent double-outputs
        THRESHOLD = 20 
        RATIO = 1.3

        if abs_ud > abs_lr * RATIO and abs_ud > THRESHOLD:
            # If delta is positive, it means signal increased on DOWN over time
            return "DOWN" if ud_delta < 0 else "UP"
            
        elif abs_lr > abs_ud * RATIO and abs_lr > THRESHOLD:
            # If delta is positive, it means signal increased on RIGHT over time
            return "RIGHT" if lr_delta > 0 else "LEFT"

        return None