import network
import time
import ujson
import select
import gc
from machine import Pin
from umqtt.simple import MQTTClient

import config  # config.py hasil copy dari config_template.py

# ===== State =====
relay = Pin(config.RELAY_PIN, Pin.OUT)
relay.value(0)
device_state = False

led = Pin(2, Pin.OUT)   # LED indikator WiFi
led.value(0)
led_last_toggle = time.time()

TOPIC_SET = "home/{}/{}/set".format(config.HOME_ID, config.DEVICE_ID)
TOPIC_STATUS = "home/{}/{}/status".format(config.HOME_ID, config.DEVICE_ID)

wlan = network.WLAN(network.STA_IF)
last_ping = time.time()  # inisialisasi di module-level, hindari error scope


def connect_wifi():
    """Blocking: coba connect tiap 15 detik sampai berhasil.
    Program lain (MQTT dst) baru jalan setelah ini return.
    LED (pin 2) nyala TERUS selama proses connect/reconnect,
    setelah berhasil connect LED kembali ke mode kedip (ditangani di main loop)."""
    led.value(1)  # nyala solid selama usaha connect/reconnect
    wlan.active(True)
    print("\n=== SMART AI IoT - ESP32 Device (MicroPython) ===")
    print("Device ID:", config.DEVICE_ID)
    print("Home ID:", config.HOME_ID)
    print("Relay Pin:", config.RELAY_PIN)

    attempt = 0
    while not wlan.isconnected():
        attempt += 1
        print("\n[WiFi] Percobaan koneksi ke-{} ...".format(attempt))
        wlan.disconnect()
        wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)

        # tunggu maksimal 15 detik untuk hasil dari percobaan ini
        t0 = time.time()
        while not wlan.isconnected() and (time.time() - t0) < 15:
            time.sleep(0.5)
            print(".", end="")

        if wlan.isconnected():
            print("\n[WiFi] Terhubung!")
            print("IP Address:", wlan.ifconfig()[0])
            print("Signal Strength (RSSI):", wlan.status('rssi'))
            global led_last_toggle
            led_last_toggle = time.time()
            return
        else:
            print("\n[WiFi] Gagal, ulangi lagi dalam siklus berikutnya...")
            # loop otomatis mengulang -> total jeda antar percobaan ~15 detik

    return


def mqtt_callback(topic, msg):
    topic = topic.decode()
    msg = msg.decode()
    print("\n[MQTT] Pesan diterima di topic:", topic)
    print("Payload:", msg)

    if topic == TOPIC_SET:
        handle_set_command(msg)


def handle_set_command(message):
    global device_state
    try:
        doc = ujson.loads(message)
    except Exception as e:
        print("JSON parse error:", e)
        return

    if "state" in doc:
        state = str(doc["state"]).lower()
        if state == "on":
            device_state = True
            relay.value(1)
            print("[DEVICE] Light turned ON")
        elif state == "off":
            device_state = False
            relay.value(0)
            print("[DEVICE] Light turned OFF")

        publish_status()


def publish_status():
    payload = ujson.dumps({
        "state": "on" if device_state else "off",
        "timestamp": time.time()
    })
    try:
        client.publish(TOPIC_STATUS, payload, retain=True)
        print("[MQTT] Status published:", payload)
    except Exception as e:
        print("[MQTT] Gagal publish status:", e)


def connect_mqtt():
    global client
    print("Connecting to MQTT broker...")

    # bersihkan memori & pastikan tidak ada socket lama yang masih nyangkut
    gc.collect()
    print("[MEM] free:", gc.mem_free())

    ssl_params = {"server_hostname": config.MQTT_BROKER}
    # Catatan: verifikasi sertifikat TLS di sini masih longgar (setara setInsecure()).
    # Lihat bagian keamanan di penjelasan chat untuk cara mengetatkannya.

    client = MQTTClient(
        client_id=config.MQTT_CLIENT_ID,
        server=config.MQTT_BROKER,
        port=config.MQTT_PORT,
        user=config.MQTT_USERNAME,
        password=config.MQTT_PASSWORD,
        keepalive=60,
        ssl=True,
        ssl_params=ssl_params,
    )
    client.set_callback(mqtt_callback)
    client.connect()
    client.subscribe(TOPIC_SET)
    print("Subscribed to:", TOPIC_SET)
    publish_status()
    global last_ping
    last_ping = time.time()


def reconnect_mqtt_loop():
    global client
    while True:
        try:
            connect_mqtt()
            return
        except Exception as e:
            # penting: tutup socket yang gagal supaya tidak bocor memori
            try:
                client.sock.close()
            except Exception:
                pass
            gc.collect()
            print("[MQTT] Gagal konek, rc/err:", e)
            time.sleep(5)


def main():
    global last_ping, led_last_toggle
    # 1) WAJIB: WiFi harus connect dulu sebelum lanjut
    connect_wifi()

    # 2) Baru setup MQTT setelah WiFi pasti connect
    reconnect_mqtt_loop()

    # 3) Loop utama
    while True:
        try:
            # cek dulu apakah memang ada data masuk di socket,
            # supaya check_msg() tidak dipanggil "buta" (sumber error -1 palsu)
            r, _, _ = select.select([client.sock], [], [], 0.3)
            if r:
                client.check_msg()

            # kirim PINGREQ berkala supaya broker tidak menganggap client mati
            if time.time() - last_ping > 30:
                client.ping()
                last_ping = time.time()

        except OSError as e:
            # errno 11 (EAGAIN) / 110 (ETIMEDOUT) itu normal untuk socket
            # non-blocking, BUKAN berarti koneksi putus -> abaikan saja
            if len(e.args) and e.args[0] in (11, 110):
                pass
            else:
                print("[MQTT] Koneksi putus (OSError):", e)
                reconnect_mqtt_loop()
        except Exception as e:
            print("[MQTT] Koneksi putus:", e)
            reconnect_mqtt_loop()

        # cek WiFi tiap loop; kalau putus, blocking reconnect lagi (retry 15s)
        if not wlan.isconnected():
            print("[WiFi] Koneksi putus, mencoba reconnect...")
            connect_wifi()
            reconnect_mqtt_loop()
        else:
            # LED kedip tiap 5 detik selama WiFi tersambung (heartbeat)
            if time.time() - led_last_toggle >= 5:
                led.value(not led.value())
                led_last_toggle = time.time()


if __name__ == "__main__":
    main()
