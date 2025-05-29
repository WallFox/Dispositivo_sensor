from umqtt.simple import MQTTClient
from Led_board import LedManager, Board, ButtonManager, AHT10
import time
import ujson
import config
from Crypto import Crypto


class MQTTManager:
    def __init__(self, host, topic_pub, topic_sub, debug=False):
        self.board = Board()
        self.aht10 = AHT10()  # SDA 21 Green, SCL 21 Yellow
        self.crypto = Crypto(config.passphrase)
        self.leds = LedManager({
            "button_led": 19  # Orange
        })
        self.buttons = ButtonManager({
            "button_push": 23  # White
        })
        self.client_id = self.board.get_id()
        self.host = host
        self.port = 1883  # WebSocket port 8081
        self.topic_pub = topic_pub.encode()
        self.topic_sub = topic_sub.encode()
        self.debug = debug
        self.client = None
        self.connected = False

    def connect(self):
        self.client = MQTTClient(self.client_id, self.host, self.port, keepalive=30)
        self.client.set_callback(self.on_message)
        for attempt in range(3):
            try:
                self.client.connect()
                self.client.subscribe(self.topic_sub)
                self.connected = True
                if self.debug:
                    print(f'Connect to broker MQTT: {self.host}')
                    print(f'Subscribed to: {self.topic_sub.decode()}')
                return True
            except Exception as e:
                print(f'Attempt {attempt + 1} failed: {e}')
                time.sleep(2)
        print('Critical Error, Rebooting...')
        self.board.reset()
        return False

    def on_message(self, topic, msg):
        try:

            if config.Crypto:
                texto = self.crypto.decrypt(msg)
                if self.debug:
                    print(f'Decrypted raw message: {texto}')
            else:
                texto = msg.decode()

            data = ujson.loads(texto)
            print(f'Received message from {topic.decode()}: {data}')

            msg_id = data.get('id')
            if msg_id in ['Status_ESP', 'Telegram', 'Node']:
                btn = data.get('dato_button')
                if btn in [0, 1]:
                    if btn == 1:
                        self.leds.turn_on('button_led')
                        print("LED encendido")
                    else:
                        self.leds.turn_off('button_led')
                        print("LED apagado")
                else:
                    print("Error: 'dato_button' must be 0 or 1")
            else:
                print(f'Ignored message: Invalid ID - {msg_id}')

        except Exception as e:
            print(f'Error processing MQTT message: {e}')

    def publish(self, msg):
        if self.client and self.connected:
            try:
                if config.Crypto:
                    self.client.publish(self.topic_pub, msg)
                else:
                    self.client.publish(self.topic_pub, msg.encode())
                if self.debug:
                    print(f'Published: {msg} in {self.topic_pub.decode()}')
                return True
            except Exception as e:
                print(f'Error publishing: {e}')
                self.connected = False
                return False
        return False

    def is_mqtt_connected(self):
        if not self.connected:
            return False
        try:
            self.client.ping()
            return True
        except Exception as e:
            print(f'Ping failed: {e}')
            self.connected = False
            return False

    def reconnect_mqtt(self):
        print("Attempting MQTT reconnection...")
        try:
            if self.client:
                self.client.disconnect()
        except:
            pass

        self.connected = False
        time.sleep(2)

        try:
            self.client.connect()
            self.client.subscribe(self.topic_sub)  # Re-suscribirse es crítico
            self.connected = True
            print("Reconnected to the MQTT broker")
            print(f"Re-subscribed to: {self.topic_sub.decode()}")
            return True
        except Exception as e:
            print("Error reconnecting MQTT:", e)
            return False

    def publish_data(self):
        before_stage = self.buttons.get_state('button_push')
        last_temp_hum_publish = time.time()
        interval = config.interval_normal
        warning_temp = config.warning_temp
        warning_hum = config.warning_hum

        while True:
            try:
                temp, hum = self.aht10.read_data()
                actual_state = self.buttons.get_state('button_push')

                msg = ujson.dumps({
                    'id': 'Sensor_ESP',
                    'dato_temp': temp,
                    'dato_hum': hum,
                    'dato_button': actual_state
                })

                msg_cifrado = self.crypto.encrypt(msg)

                # Verificar conexión antes de publicar
                if not self.is_mqtt_connected():
                    print('Broker disconnected. Trying to reconnect...')
                    if not self.reconnect_mqtt():
                        time.sleep(5)
                        continue

                # Publicar cambio de botón inmediatamente
                if actual_state != before_stage:
                    if config.Crypto:
                        if self.publish(msg_cifrado):
                            print(f'Button change sent: {actual_state}')
                            before_stage = actual_state
                        else:
                            print('Failed to send button change')
                    else:
                        if self.publish(msg):
                            print(f'Button change sent: {actual_state}')
                            before_stage = actual_state
                        else:
                            print('Failed to send button change')

                # Ajustar intervalo según alertas
                if temp and hum and (temp >= warning_temp or hum >= warning_hum):
                    interval = config.interval_warning
                else:
                    interval = config.interval_normal

                # Publicar datos periódicos
                if time.time() - last_temp_hum_publish >= interval:
                    if config.Crypto:
                        if self.publish(msg_cifrado):
                            print(f'Periodic data sent: T={temp}°C, H={hum}%')
                            last_temp_hum_publish = time.time()
                        else:
                            print('Failed to send periodic data')
                    else:
                        if self.publish(msg):
                            print(f'Periodic data sent: T={temp}°C, H={hum}%')
                            last_temp_hum_publish = time.time()
                        else:
                            print('Failed to send periodic data')

            except Exception as e:
                print(f'Error in publish_data: {e}')

            time.sleep(0.1)

    def listen(self):
        while True:
            try:
                if self.connected and self.client:
                    self.client.check_msg()
                else:
                    print("MQTT not connected, attempting reconnection...")
                    if not self.reconnect_mqtt():
                        time.sleep(5)
                        continue

                time.sleep(0.1)

            except OSError as e:
                print(f'Network error in listen: {e}')
                self.connected = False
                time.sleep(2)
            except Exception as e:
                print(f'Error in listen: {e}')
                time.sleep(1)

    def disconnect(self):
        if self.client:
            try:
                self.client.disconnect()
                self.connected = False
                if self.debug:
                    print('Disconnected from MQTT')
            except:
                pass
