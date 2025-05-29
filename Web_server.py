from WiFi_connection_manager import *
from Led_board import Board
import network
import socket
import ure
import time
import ujson
import config

class WebServer:
    max_networks = 5

    def __init__(self,debug=False):
        self.debug = debug
        self.ap = network.WLAN(network.AP_IF)
        self.sta = network.WLAN(network.STA_IF)
        self.wifi_manager = WiFiManager(debug=debug)
        self.board = Board()
        self.ssid = config.ssid
        self.password = config.password

    def star_ap(self):
        if self.debug:
            print('Starting Access Point...')
        self.ap.active(True)
        self.ap.config(essid=self.ssid, password=self.password, authmode=network.AUTH_WPA2_PSK)
        time.sleep(1)
        print(f"WiFi AP '{self.ssid}' started. Connect and visit 192.168.4.1")

    def scan_networks(self):
        self.sta.active(True)
        networks = self.sta.scan()
        return [(ssid.decode(), rssi) for ssid, _, _, rssi, _, _ in networks if rssi > -80]

    def url_decode(self,text):
        text = text.replace('+',' ')
        text = ure.sub(r'%([0-9A-Fa-f]{2})', lambda match: chr(int(match.group(1), 16)), text)
        return text

    def has_internet(self, retries=3, delay=1):
        for attempt in range(retries):
            try:
                s = socket.socket()
                s.settimeout(3)
                s.connect(('8.8.8.8',53))
                s.close()
                return True
            except:
                if self.debug:
                    print(f'[Attempt {attempt+1}] No internet access, retrying...')
                time.sleep(delay)
        return False

    def check_internet(self):
        while True:
            print('Checking internet...')
            if not self.has_internet():
                time.sleep(2)
                print("Lose internet, trying reconnect...")
                self.wifi_manager.connect()
            time.sleep(10)

    def handle_request(self,request):
        request_str = str(request)
        match = ure.search(r'/\?ssid=([^&]+)&password=([^&\s\\]+)',request_str)

        if match:
            ssid = self.url_decode(match.group(1))
            password = self.url_decode(match.group(2))
            if self.debug:
                print(f'Received credentials: SSID={ssid}, PASSWORD={password}')

            updated = False
            for net in self.wifi_manager.credentials['networks']:
                if net['network'] == ssid:
                    net['password'] = password
                    updated = True
                    break

            if not updated:
                if len(self.wifi_manager.credentials['networks']) >= self.max_networks:
                    self.wifi_manager.credentials['networks'].pop(0)
                self.wifi_manager.credentials['networks'].append({'network': ssid, 'password': password})

            self.wifi_manager.save_credentials()
            print('Credentials saved. Rebooting...')
            self.board.reset()

        networks = self.scan_networks()
        options_html = "".join(f'<option value="{ssid}">{ssid} ({rssi} dBm)</option>' for ssid, rssi in networks)

        with open('index.html', 'r') as file:
            html = file.read().replace("<!-- NETWORKS_PLACEHOLDER -->", options_html)
        return html

    def launch_server(self):
        self.star_ap()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('',80))
        s.listen(5) #Number device

        while True:
            conn, addr = s.accept()
            print(f'Connection from {addr}')
            request = conn.recv(1024)
            response = self.handle_request(request)
            head_http = "HTTP/1.1 200 OK \n content-type: text/html\n\n"
            html_total = head_http + response
            conn.sendall(html_total.encode())
            conn.close()

















