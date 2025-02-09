import paho.mqtt.client as mqtt
import threading
import logging
import queue
import time
import base64
import csv
from tqdm import tqdm
try:
    from evdev import InputDevice, categorize, ecodes
except:
    pass

logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('MQTTRecorder')

class SslContext():

    def __init__(self, enable, ca_cert, certfile, keyfile, tls_insecure):
        self.enable = enable
        self.ca_cert = ca_cert
        self.certfile = certfile
        self.keyfile = keyfile
        self.tls_insecure = tls_insecure


class MqttRecorder:

    def __init__(self, host: str, port: int, client_id: str, file_name: str, username: str,
                 password: str, sslContext: SslContext, encode_b64: bool):
        self.__recording = False
        self.__messages = queue.Queue()
        self.__file_name = file_name
        self.__last_message_time = None
        self.__encode_b64 = encode_b64
        self.__client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=client_id)
        self.__client.on_connect = self.__on_connect
        self.__client.on_message = self.__on_message
        self.__csv_writer_t = None
        if username is not None:
            self.__client.username_pw_set(username, password)
        if sslContext.enable:
            self.__client.tls_set(sslContext.ca_cert, sslContext.certfile, sslContext.keyfile)
            if sslContext.tls_insecure is True:
                self.__client.tls_insecure_set(True)
        self.__client.connect(host=host, port=port)
        self.__client.loop_start()

    def __csv_writer(self):
        logger.info('Saving messages to output file')
        with open(self.__file_name, 'w', newline='', buffering=1) as csvfile:
            writer = csv.writer(csvfile)
            while True:
                row = self.__messages.get()
                if not row:
                    break
                writer.writerow(row)

    def start_recording(self, topics: list, qos: int=0):
        self.__csv_writer_t = threading.Thread(target=self.__csv_writer)
        self.__csv_writer_t.daemon = True
        self.__csv_writer_t.start()
        self.__last_message_time = time.time()
        if type(topics) is list and len(topics) > 0:
            for topic in topics:
                self.__client.subscribe(topic, qos=qos)
        else:
            self.__client.subscribe('#', qos=qos)
        self.__recording = True

    def start_replay(self, loop: bool, delay: float=None):
        kbd = None
        try:
            kbd = InputDevice('/dev/input/event0')
            print("S stops play, then arrows Right and Left navigate through records, ENTER resumes play")
        except PermissionError as e:
            print("ERROR: '%s' - keyboard navigation disabled" % e)
            print("Make sure you have read permissions on /dev/input/event0")
        except Exception as e:
            print("ERROR: '%s' - keyboard navigation disabled" % e)

        def decode_payload(payload, encode_b64):
            return base64.b64decode(payload) if encode_b64 else payload

        logger.info(f"{self.__file_name}: counting lines")
        with open(self.__file_name, newline='') as csvfile:
            csv_lines = sum(1 for line in csvfile)
            logger.info(f"{self.__file_name}: {csv_lines} lines")

        with open(self.__file_name, newline='') as csvfile:
            logger.info('Starting replay')
            first_message = True
            reader = csv.reader(csvfile)
            # Convert reader to list for random access
            rows = list(reader)
            current_row_index = 0

            while True:
                while current_row_index < len(rows):
                    row = rows[current_row_index]
                    tqdm.write(f'Processing row {current_row_index + 1}/{len(rows)}')

                    if not first_message:
                        time.sleep(delay or float(row[5]))
                        if kbd:
                            keys = kbd.active_keys()
                            if ecodes.KEY_S in keys:
                                print("Paused - Navigation Mode")
                                while True:
                                    keys = kbd.active_keys()
                                    if ecodes.KEY_RIGHT in keys: # Right arrow to move forward
                                        if current_row_index < len(rows) - 1:
                                            current_row_index += 1
                                            print(f"Moving to row {current_row_index + 1}")
                                            row = rows[current_row_index]
                                            mqtt_payload = decode_payload(row[1], self.__encode_b64)
                                            retain = False if row[3] == 'False' else True
                                            self.__client.publish(topic=row[0], payload=mqtt_payload,
                                                    qos=int(row[2]), retain=retain)
                                        time.sleep(0.2) # Prevent multiple keypresses
                                    elif ecodes.KEY_LEFT in keys: # Left arrow to move backward
                                        if current_row_index > 0:
                                            current_row_index -= 1
                                            row = rows[current_row_index]
                                            mqtt_payload = decode_payload(row[1], self.__encode_b64)
                                            retain = False if row[3] == 'False' else True
                                            self.__client.publish(topic=row[0], payload=mqtt_payload,
                                                    qos=int(row[2]), retain=retain)
                                            print(f"Moving to row {current_row_index + 1}")
                                        time.sleep(0.2) # Prevent multiple keypresses
                                    elif ecodes.KEY_ENTER in keys: # Enter to resume
                                        print("Resuming replay")
                                        break
                                    time.sleep(0.1) # Reduce CPU usage
                    else:
                        first_message = False
                    mqtt_payload = decode_payload(row[1], self.__encode_b64)
                    retain = False if row[3] == 'False' else True
                    self.__client.publish(topic=row[0], payload=mqtt_payload,
                            qos=int(row[2]), retain=retain)
                    current_row_index += 1
                logger.info('End of replay')
                if loop:
                    logger.info('Restarting replay')
                    current_row_index = 0 # Reset index for loop
                    time.sleep(1)
                else:
                    break

    def stop_recording(self):
        self.__client.loop_stop()
        logger.info('Recording stopped')
        self.__recording = False
        self.__messages.put([])
        self.__csv_writer_t.join()


    def __on_connect(self, client, userdata, flags, rc):
        logger.info("Connected to broker!")


    def __on_message(self, client, userdata, msg):
        def encode_payload(payload, encode_b64):
            return base64.b64encode(msg.payload).decode() if encode_b64 else payload.decode()

        if self.__recording:
            logger.info("[MQTT Message received] Topic: %s QoS: %s Retain: %s",
                        msg.topic, msg.qos, msg.retain)
            time_now = time.time()
            time_delta = time_now - self.__last_message_time
            payload = encode_payload(msg.payload, self.__encode_b64)
            row = [msg.topic, payload, msg.qos, msg.retain, time_now, time_delta]
            self.__messages.put(row)
            self.__last_message_time = time_now
