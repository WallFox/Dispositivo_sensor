import network
import time
import ujson
from Led_board import LedManager

class WiFiManager:
    filename = 'connection'

    def __init__(self, debug=False):
        self.debug   = debug
        self.station = network.WLAN(network.STA_IF)
        self.station.active(True)
        self.credentials = self.load_credentials()
        self.leds = LedManager({"esp_onboard":2})
        if self.debug:
            print('WiFiManager initialized')

    def load_credentials(self):
        try:
            with open(self.filename, 'r') as file:
                data = ujson.load(file)
                if self.debug:
                    print(f'Loaded credentials: {data}')
                return data
        except Exception as e:
            print(f'Error loading credentials: {e}')
            return {'networks': [], 'last_successful': None}

    def save_credentials(self):
        try:
            with open(self.filename, 'w') as file:
                ujson.dump(self.credentials, file)
            print('Credentials saved successfully')
            if self.debug:
                print(f'Updated credentials: {self.credentials}')
        except Exception as e:
            print(f'Error saving credentials: {e}')

    def reset_wifi(self):
        if self.debug:
            print('Resetting WiFi module...')
        self.station.active(False) #Active or deactivate el WiFi
        time.sleep(0.5)
        self.station.active(True)
        time.sleep(0.5)

    def is_connected_to_wifi(self):
        station = network.WLAN(network.STA_IF)
        if not station.isconnected():
            self.leds.turn_off("esp_onboard")
        else:
            self.leds.turn_on("esp_onboard")
        return station.isconnected()

    def connect(self):
        try:
            self.leds.start_blink()
            self.reset_wifi()

            if 'networks' not in self.credentials or not self.credentials['networks']:
                print('No saved networks.')
                return False
            networks = self.credentials['networks']
            last_successful = self.credentials.get('last_successful', None)

            if last_successful:
                networks.sort(key=lambda net: net['network'] != last_successful)

            for network_data in networks:
                ssid, password = network_data['network'], network_data['password']
                print(f'Trying to connect to: {ssid}')
                if self.debug:
                    print(f'Password: {password}')

                self.station.active(False)
                time.sleep(0.5)
                self.station.active(True)
                time.sleep(0.5)

                if self.debug:
                    print(f'Status before connecting: {self.station.status()}')

                self.station.connect(ssid, password)

                if self.debug:
                    print(f'Status after connecting: {self.station.status()}')

                for attempt in range(5):
                    if self.debug:
                        print(f'Attempt {attempt + 1}, Status WiFi: {self.station.status()}')
                        print(f'Network configuration after attempt: {self.station.ifconfig()}')
                    if self.station.isconnected():
                        self.leds.stop_blink()
                        print(f'Connected to {ssid}')
                        print(f'IP: {self.station.ifconfig()[0]}')
                        self.leds.turn_on("esp_onboard")
                        if self.debug:
                            print(f'Mask:    {self.station.ifconfig()[1]}')
                            print(f'Gateway: {self.station.ifconfig()[2]}')
                            print(f'DNS:     {self.station.ifconfig()[3]}')
                        self.credentials['last_successful'] = ssid
                        self.save_credentials()
                        return True
                    time.sleep(1)
                    print(f'Attempt {attempt + 1} failed...')

                print(f'Could not connect to {ssid}, trying next...')
                self.reset_wifi()

            print('Failed to connect to any saved network.')
            self.leds.stop_blink()
            self.leds.turn_off("esp_onboard")
            return False

        except Exception as e:
            print(f'Error in connect(): {e}')
            self.leds.stop_blink()
            return False