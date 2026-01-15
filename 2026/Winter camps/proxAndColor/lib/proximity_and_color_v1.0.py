__version__ = "1.0"

from machine import I2C, Pin
import time

class APDS9960:
    # Key Addresses
    ADDRESS = 0x39

    # Register Constants
    ENABLE   = 0x80 # Power, Proximity, ALS, Gesture
    ID       = 0x92 # Device ID
    ATIME    = 0x81 # ALS Integration Time
    WTIME    = 0x83 # Wait Time
    CONFIG2  = 0x90 # Configuration Register Two
    CONTROL  = 0x8F # Gain and Drive Strength
    
    # Data Registers
    PDATA    = 0x9C # Proximity Data
    CDATA    = 0x94 # Clear Channel Data (start of RGBC)

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
        """Initialize sensor settings for balanced speed and sensitivity."""
        # 1. Power ON + Proximity + Color (Enable bit 0, 1, 2)
        self.i2c.writeto_mem(self.ADDRESS, self.ENABLE, b'\x07')
        
        # 2. Set Integration Time (ATIME)
        # 0xDB = 100ms. Lower value = faster updates but less sensitivity.
        self.i2c.writeto_mem(self.ADDRESS, self.ATIME, b'\xDB')
        
        # 3. Set Gain (CONTROL)
        # Bits 0-1: ALS Gain (0x02 = 16x)
        # Bits 2-3: Prox Gain (0x08 = 4x)
        # 0x02 | 0x08 = 0x0A
        self.i2c.writeto_mem(self.ADDRESS, self.CONTROL, b'\x0A')

    def get_proximity(self):
        """Returns proximity value (0-255, where 255 is closest)."""
        return self.i2c.readfrom_mem(self.ADDRESS, self.PDATA, 1)[0]

    def get_color(self):
        """Returns (Clear, R, G, B) normalized to 0-255."""
        data = self.i2c.readfrom_mem(self.ADDRESS, self.CDATA, 8)
        # Unpack 16-bit values
        c = data[0] | (data[1] << 8)
        r = data[2] | (data[3] << 8)
        g = data[4] | (data[5] << 8)
        b = data[6] | (data[7] << 8)

        if c > 0:
            # Normalize against Clear channel to get better color ratios
            r_norm = min(int((r / c) * 255), 255)
            g_norm = min(int((g / c) * 255), 255)
            b_norm = min(int((b / c) * 255), 255)
            return c, r_norm, g_norm, b_norm
        return 0, 0, 0, 0