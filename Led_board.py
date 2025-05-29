from machine import (Pin,
                     Timer,
                     reset,
                     unique_id,
                     I2C)
import time
import ubinascii


class AHT10:
    def __init__(self, scl=22, sda=21, addr=0x38):
        self.i2c = I2C(0, scl=Pin(scl), sda=Pin(sda))
        self.addr = addr
        self._init_sensor()

    def _init_sensor(self):
        try:
            self.i2c.writeto(self.addr, b'\xE1\x08\x00')
            time.sleep(0.1)
        except Exception as e:
            print("Error initialising AHT10:", e)

    def read_data(self):
        try:
            self.i2c.writeto(self.addr, b'\xAC\x33\x00')
            time.sleep(0.1)
            data = self.i2c.readfrom(self.addr, 6)

            for _ in range(5):
                if not data[0] & 0x80:
                    break
                time.sleep(0.05)

            if data[0] & 0x80:
                return None, None

            raw_humidity = ((data[1] << 16) | (data[2] << 8) | data[3]) >> 4
            raw_temp = (((data[3] & 0x0F) << 16) | (data[4] << 8) | data[5])

            humidity = (raw_humidity / 1048576) * 100
            temp = (raw_temp / 1048576) * 200 - 50

            return round(temp, 2), round(humidity, 2)
        except Exception as e:
            print("Error leyendo AHT10:", e)
            return None, None


class Board:
    def __init__(self):
        self.device_id = ubinascii.hexlify(unique_id()).decode()
        self.button = Pin(4, Pin.IN, Pin.PULL_DOWN)

    def reset(self, seg=3):
        for _ in range(seg):
            print(f'{seg}')
            seg -= 1
            time.sleep(1)
        reset()

    def get_id(self):
        return self.device_id


class ButtonManager:
    def __init__(self, buttons_config):
        """
        For the list safe Output read
        GPIO
        buttons_config={"name": GPIO}
        ej:
        buttons_config={
        "button_1: 4",
        "button_2: 5
        }
        """
        self.buttons = {name: Pin(pin, Pin.IN, Pin.PULL_DOWN) for name, pin in buttons_config.items()}

    def get_state(self, name):
        if name in self.buttons:
            return self.buttons[name].value()
        return None

    def wait_for_press(self, name, debounce=0.1):
        if name in self.buttons:
            while not self.buttons[name].value():
                time.sleep(debounce)
            return True
        return False


class LedManager:
    def __init__(self, leds_config, period=250):
        """
        For the list safe Input read
        GPIO
        leds_config={"name": GPIO}
        ej:
        leds_config={
        "button":     25,
        "temp":       26,
        "humidity":   27,
        "esp_onboard": 2
        }
        """
        self.leds = {name: Pin(pin, Pin.OUT) for name, pin in leds_config.items()}
        self.period = period
        self.timer = Timer(0)

    def turn_on(self, name):
        if name in self.leds:
            self.leds[name].value(1)

    def turn_off(self, name):
        if name in self.leds:
            self.leds[name].value(0)

    def blink(self, timer):
        self.leds["esp_onboard"].value(not self.leds["esp_onboard"].value())

    def start_blink(self):
        self.timer.init(period=self.period, mode=Timer.PERIODIC, callback=self.blink)

    def stop_blink(self):
        self.timer.deinit()
        self.leds["esp_onboard"].value(0)
