import network
import time
import ujson
from machine import Pin, PWM
from umqtt.simple import MQTTClient

import config

# ============================================================
#  HARDWARE PIN CONFIGURATION
# ============================================================
# TSOP38238: Pin 1(OUT)->GPIO15, Pin 2(GND)->GND, Pin 3(Vs)->3.3V
IR_RX_PIN = getattr(config, "IR_RX_PIN", 15)
# IR Transmitter LED: Anoda (via R 100 ohm) -> GPIO 4, Katoda -> GND
IR_TX_PIN = getattr(config, "IR_TX_PIN", 4)
# Indikator LED Onboard
LED_PIN = getattr(config, "LED_PIN", 2)

# Pin Setup
rx_pin = Pin(IR_RX_PIN, Pin.IN, Pin.PULL_UP)
tx_pwm = PWM(Pin(IR_TX_PIN), freq=38000, duty=0)
led = Pin(LED_PIN, Pin.OUT)
led.value(0)

# ============================================================
#  DEFAULT TV CODES (NEC Protocol 32-bit HEX)
#  Bisa otomatis ditimpa lewat proses "Learn" remote fisik Anda
# ============================================================
TV_CODES = {
    "power": 0x20DF10EF,      # LG / General TV Power
    "vol_up": 0x20DF40BF,     # Volume Up
    "vol_down": 0x20DDC03F,   # Volume Down
    "mute": 0x20DF906F,       # Mute
    "ch_up": 0x20DF00FF,      # Channel Up
    "ch_down": 0x20DF807F,    # Channel Down
}

# Load saved custom codes from flash if available
try:
    with open("tv_codes.json", "r") as f:
        saved = ujson.loads(f.read())
        TV_CODES.update(saved)
        print("[STORAGE] Custom learned TV codes loaded from tv_codes.json")
except Exception:
    pass

# MQTT Topics
TOPIC_SET = "home/{}/{}/set".format(config.HOME_ID, config.DEVICE_ID)
TOPIC_STATUS = "home/{}/{}/status".format(config.HOME_ID, config.DEVICE_ID)
TOPIC_TELEMETRY = "home/{}/{}/telemetry".format(config.HOME_ID, config.DEVICE_ID)

wlan = network.WLAN(network.STA_IF)
mqtt_client = None
learning_mode = False
target_learn_button = "power"
last_ping = time.time()


# ============================================================
#  TRANSMITTER ENGINE (38 kHz IR PWM Modulator)
# ============================================================
def ir_carrier_on():
    """Nyalakan carrier 38kHz (duty cycle ~33% untuk IR LED)"""
    tx_pwm.duty(341)

def ir_carrier_off():
    """Matikan carrier"""
    tx_pwm.duty(0)

def send_nec_code(hex_code):
    """
    Kirim sinyal IR 38kHz dengan format protokol standar NEC 32-bit.
    Format NEC:
    - Leader Mark: 9000 us (Carrier ON)
    - Leader Space: 4500 us (Carrier OFF)
    - Bit 0: 560 us Mark + 560 us Space
    - Bit 1: 560 us Mark + 1690 us Space
    - Stop bit: 560 us Mark
    """
    led.value(1)
    # Leader
    ir_carrier_on()
    time.sleep_us(9000)
    ir_carrier_off()
    time.sleep_us(4500)

    # 32 data bits (MSB first)
    for i in range(31, -1, -1):
        bit = (hex_code >> i) & 1
        ir_carrier_on()
        time.sleep_us(560)
        ir_carrier_off()
        if bit:
            time.sleep_us(1690)
        else:
            time.sleep_us(560)

    # Stop bit
    ir_carrier_on()
    time.sleep_us(560)
    ir_carrier_off()
    led.value(0)
    print("[IR TX] Sinyal Terkirim ke TV: 0x{:08X}".format(hex_code))


def send_raw_pulses(pulses):
    """Kirim pulsa mentah (mark, space, mark, space...)"""
    led.value(1)
    for i, duration in enumerate(pulses):
        if i % 2 == 0:
            ir_carrier_on()
        else:
            ir_carrier_off()
        time.sleep_us(duration)
    ir_carrier_off()
    led.value(0)


# ============================================================
#  RECEIVER & LEARNING ENGINE (TSOP38238 Demodulator)
# ============================================================
def capture_ir_signal(timeout_ms=100):
    """
    Tangkap pulsa dari sensor TSOP38238.
    TSOP38238 output adalah Active-LOW (saat ada sinyal 38kHz, nilai = 0).
    """
    if rx_pin.value() == 1:
        return None  # Tidak ada sinyal masuk

    # Sinyal terdeteksi! Rekam transisi pulsa
    pulses = []
    t_start = time.ticks_us()
    current_state = 0
    t_last = t_start

    # Batas maksimal pembacaan satu frame ~70ms
    deadline = time.ticks_add(t_start, timeout_ms * 1000)

    while time.ticks_diff(deadline, time.ticks_us()) > 0:
        val = rx_pin.value()
        if val != current_state:
            now = time.ticks_us()
            duration = time.ticks_diff(now, t_last)
            pulses.append(duration)
            t_last = now
            current_state = val
        else:
            # Jika sinyal diam HIGH lebih dari 10ms, frame selesai
            if current_state == 1 and time.ticks_diff(time.ticks_us(), t_last) > 10000:
                break

    if len(pulses) < 10:
        return None  # Terlalu pendek / noise

    return pulses


def decode_nec(pulses):
    """Decode pulsa mentah ke format NEC 32-bit HEX"""
    if len(pulses) < 66:
        return None

    # Verifikasi leader mark (~9000us) & leader space (~4500us)
    if not (7000 < pulses[0] < 11000) or not (3000 < pulses[1] < 6000):
        return None

    code = 0
    # Bit data mulai dari indeks 2 (mark, space bergantian)
    for i in range(32):
        idx = 2 + (i * 2)
        if idx + 1 >= len(pulses):
            break
        space = pulses[idx + 1]
        code <<= 1
        if space > 1000:  # Space panjang (~1690us) = Bit 1
            code |= 1
        # Space pendek (~560us) = Bit 0

    return code


# ============================================================
#  WIFI & MQTT CONNECTION
# ============================================================
def connect_wifi():
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


def on_mqtt_message(topic, msg):
    """Menerima perintah dari Dashboard Web atau AI Gemini"""
    global learning_mode, target_learn_button
    topic_str = topic.decode()
    payload_str = msg.decode()
    print("\n[MQTT RX]", topic_str, "->", payload_str)

    try:
        data = ujson.loads(payload_str)
        action = data.get("action", "")
        button = data.get("button", data.get("value", ""))

        # Cek jika mode learn diminta
        if action == "learn_mode" or button == "learn":
            learning_mode = True
            target_learn_button = data.get("target_button", "power")
            print("[LEARN MODE] AKTIF! Arahkan remote TV ke TSOP38238 dan tekan tombol:", target_learn_button)
            return

        # Eksekusi tombol remote TV
        target_btn = str(button if button else action).lower()
        if target_btn == "turn_on" or target_btn == "turn_off" or target_btn == "toggle":
            target_btn = "power"

        if target_btn in TV_CODES:
            code = TV_CODES[target_btn]
            print("[COMMAND] Mengirim tombol TV:", target_btn.upper(), "-> 0x{:08X}".format(code))
            send_nec_code(code)

            # Lapor status kembali ke MQTT broker
            if mqtt_client:
                mqtt_client.publish(
                    TOPIC_STATUS,
                    ujson.dumps({
                        "state": "on" if target_btn == "power" else "active",
                        "last_button": target_btn,
                        "hex_code": "0x{:08X}".format(code),
                        "timestamp": int(time.time()),
                    })
                )
        elif data.get("hex_code"):
            # Perintah kirim kode HEX langsung
            hex_val = int(data["hex_code"], 16)
            send_nec_code(hex_val)
        else:
            print("[WARNING] Tombol tidak dikenal:", target_btn)

    except Exception as e:
        print("[ERROR JSON]", e)


# ============================================================
#  MAIN LOOP
# ============================================================
def main():
    global mqtt_client, learning_mode, last_ping

    print("\n=======================================================")
    print("  SMART AI IoT - Universal TV Remote (TSOP38238 + IR TX)")
    print("  Device ID   :", config.DEVICE_ID)
    print("  Room ID     :", config.HOME_ID)
    print("  TSOP38238 RX: GPIO", IR_RX_PIN)
    print("  IR LED TX   : GPIO", IR_TX_PIN)
    print("=======================================================")

    connect_wifi()

    # Koneksi MQTT TLS HiveMQ Cloud
    mqtt_client = MQTTClient(
        client_id=config.MQTT_CLIENT_ID + "-tv",
        server=config.MQTT_BROKER,
        port=config.MQTT_PORT,
        user=config.MQTT_USERNAME,
        password=config.MQTT_PASSWORD,
        ssl=True,
        ssl_params={"server_hostname": config.MQTT_BROKER},
    )
    mqtt_client.set_callback(on_mqtt_message)

    try:
        mqtt_client.connect()
        mqtt_client.subscribe(TOPIC_SET)
        print("[MQTT] Terhubung ke HiveMQ Cloud TLS! Subscribed ke:", TOPIC_SET)
    except Exception as e:
        print("[MQTT ERROR]", e)

    print("\n[READY] Siap menerima perintah dari Web UI atau sinyal dari remote TV...")
    print("Tip: Arahkan remote TV fisik ke sensor TSOP38238 untuk menangkap frekuensi & kodenya.\n")

    while True:
        try:
            # 1. Cek pesan masuk dari Web Dashboard / Backend
            mqtt_client.check_msg()

            # 2. Tangkap sinyal infrared dari remote fisik via TSOP38238
            pulses = capture_ir_signal()
            if pulses:
                led.value(1)
                nec_code = decode_nec(pulses)

                if nec_code is not None:
                    hex_str = "0x{:08X}".format(nec_code)
                    print("\n[TSOP38238] Sinyal Berhasil Ditangkap! Protokol: NEC | Kode HEX:", hex_str)

                    # Jika dalam mode pembelajaran (Learn), simpan kodenya
                    if learning_mode:
                        TV_CODES[target_learn_button] = nec_code
                        with open("tv_codes.json", "w") as f:
                            f.write(ujson.dumps(TV_CODES))
                        print("[LEARN SUCCESS] Tombol '{}' disimpan dengan kode: {}".format(target_learn_button, hex_str))
                        learning_mode = False

                    # Broadcast ke Cloud MQTT & Dashboard Web
                    mqtt_client.publish(
                        TOPIC_TELEMETRY,
                        ujson.dumps({
                            "event": "ir_code_captured",
                            "protocol": "NEC",
                            "hex_code": hex_str,
                            "timestamp": int(time.time()),
                        }),
                    )
                else:
                    print("\n[TSOP38238] Sinyal Ditangkap (Raw):", len(pulses), "pulsa")

                time.sleep_ms(200)
                led.value(0)

            # 3. Ping keepalive MQTT setiap 30 detik
            if time.time() - last_ping > 30:
                mqtt_client.ping()
                last_ping = time.time()

            time.sleep_ms(10)

        except Exception as err:
            print("[LOOP EXCEPTION]", err)
            time.sleep(2)
            try:
                connect_wifi()
                mqtt_client.connect()
                mqtt_client.subscribe(TOPIC_SET)
            except:
                pass


if __name__ == "__main__":
    main()
