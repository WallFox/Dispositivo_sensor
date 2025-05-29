from WiFi_connection_manager import WiFiManager
from Web_server import WebServer
from MQTT_manager import MQTTManager
from _thread import start_new_thread
import time
import config

Host = config.Host
Topic_Pub = config.Topic_Pub
Topic_Sub = config.Topic_Sub

wifi = WiFiManager()
server = WebServer()

if wifi.connect():
    print('Successful connection')

    if server.has_internet():
        print('Internet connected')

        mqtt = MQTTManager(Host, Topic_Pub, Topic_Sub)
        mqtt.connect()

        if not mqtt.client:
            print('Could not connect to MQTT')
        else:
            start_new_thread(server.check_internet, ())
            start_new_thread(mqtt.listen, ())
            start_new_thread(mqtt.publish_data, ())

            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print('Ending MQTT...')
                mqtt.disconnect()

    else:
        print('Connected to WiFi, but without internet access')
else:
    print('Unable to connect, launching web server')
    server.launch_server()
