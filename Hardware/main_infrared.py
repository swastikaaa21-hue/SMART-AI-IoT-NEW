import network
import time
import ujson
from machine import Pin
from umqtt.simple import MQTTClient

import config

# ===== Pin Hardware ESP32 =====
# IR Pin (Digital OUT dari sensor IR Proximity/Obstacle/PIR)
# Default GPIO 4 (Bisa disesuaikan dengan sambungan pin Anda)
IR_PIN = getattr(config, 'IR_PIN', 4)
ir_sensor = Pin(IR_PIN, Pin.IN, Pin.PULL_UP)

# Indikator LED Onboard (GPIO 2)
led = Pin(2, Pin.OUT)
led.value(0)

# Optional Output Relay/Buzzer jika ingin otomatis menyalakan lampu saat deteksi IR
RELAY_PIN = getattr(config, 'RELAY_PIN', 18)
relay = Pin(RELAY_PIN, Pin.OUT)
relay.value(0)

# ===== Topik MQTT =====
TOPIC_SET = "home/{}/{}/set".format(config.HOME_ID, config.DEVICE_ID)
TOPIC_STATUS = "home/{}/{}/status".format(config.HOME_ID, config.DEVICE_ID)
TOPIC_TELEMETRY = "home/{}/{}/telemetry".format(config.HOME_ID, config.DEVICE_ID)

wlan = network.WLAN(network.STA_IF)
last_ping = time.time()
last_state = None


def connect_wifi():
    """Koneksi ke WiFi access point."""
    wlan.active(True)
    if not wlan.isconnected():
        print("[WiFi] Menghubungkan ke:", config.WIFI_SSID)
        wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
        attempt = 0
        while not wlan.isconnected() and attempt < 30:
            time.sleep(0.5)
            attempt += 1
            print(".", end="")
    if wlan.isconnected():
        print("\n[WiFi] Terhubung! IP:", wlan.ifconfig()[0])
    else:
        print("\n[WiFi] Gagal terhubung!")


def mqtt_callback(topic, msg):
    """Menerima perintah kontrol dari backend/website."""
    global relay
    topic_str = topic.decode()
    payload_str = msg.decode()
    print("\n[MQTT RX]", topic_str, "->", payload_str)
    try:
        data = ujson.loads(payload_str)
        action = data.get("action") or data.get("state")
        if action == "turn_on" or action == "on":
            relay.value(1)
            print("[ACTUATOR] ON")
        elif action == "turn_off" or action == "off":
            relay.value(0)
            print("[ACTUATOR] OFF")
    except Exception as e:
        print("[MQTT ERROR]", e)


def main():
    global last_state, last_ping

    print("\n==========================================")
    print("  SMART AI IoT - ESP32 Infrared Module")
    print("  Device ID:", config.DEVICE_ID)
    print("  Home ID  :", config.HOME_ID)
    print("  IR Pin   : GPIO", IR_PIN)
    print("==========================================")

    connect_wifi()

    # Inisialisasi MQTT dengan SSL/TLS HiveMQ
    client = MQTTClient(
        client_id=config.MQTT_CLIENT_ID + "-ir",
        server=config.MQTT_BROKER,
        port=config.MQTT_PORT,
        user=config.MQTT_USERNAME,
        password=config.MQTT_PASSWORD,
        ssl=True,
        ssl_params={'server_hostname': config.MQTT_BROKER}
    )
    client.set_callback(mqtt_callback)

    try:
        client.connect()
        client.subscribe(TOPIC_SET)
        print("[MQTT] Terhubung ke HiveMQ Cloud TLS!")
    except Exception as e:
        print("[MQTT] Gagal koneksi:", e)

    print("\n[SENSOR] Memulai pemantauan sensor infrared...")

    while True:
        try:
            # Non-blocking cek pesan masuk dari MQTT broker
            client.check_msg()

            # Baca sensor IR
            # Pada modul sensor IR obstacle standar: 0 = Terhalang/Ada Objek, 1 = Tidak ada objek
            # Pada modul PIR motion sensor: 1 = Ada gerakan, 0 = Tidak ada gerakan
            ir_val = ir_sensor.value()

            # Deteksi objek (default mode IR Obstacle active LOW)
            object_detected = (ir_val == 0)

            # Jika status berubah, kirim update status ke MQTT dan website
            if object_detected != last_state:
                last_state = object_detected
                state_str = "on" if object_detected else "off"
                led.value(1 if object_detected else 0)

                payload = ujson.dumps({
                    "state": state_str,
                    "motion_detected": object_detected,
                    "sensor_type": "infrared",
                    "timestamp": int(time.time())
                })

                client.publish(TOPIC_STATUS, payload)
                client.publish(TOPIC_TELEMETRY, payload)
                print("[EVENT] IR Deteksi:", state_str.upper(), "-> Kirim ke Cloud MQTT")

            # Keepalive ping setiap 30 detik
            if time.time() - last_ping > 30:
                client.ping()
                last_ping = time.time()

            time.sleep(0.1)

        except Exception as err:
            print("[LOOP ERROR]", err)
            time.sleep(2)
            try:
                connect_wifi()
                client.connect()
                client.subscribe(TOPIC_SET)
            except:
                pass


if __name__ == "__main__":
    main()
