# ============================================================
# SMART AI IoT - ESP32 Hardware Configuration Template
# Copy this file to 'config.py' and fill in your credentials.
# ============================================================

# --- WiFi Credentials ---
WIFI_SSID = "YOUR_WIFI_SSID"
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"

# --- Home & Device Identity ---
HOME_ID = "kamar"                     # Room slug matching backend (e.g. kamar, ruang-tamu)
DEVICE_ID = "esp32_light_01"          # Unique Device ID matching registered device
RELAY_PIN = 18                        # GPIO pin connected to relay module

# --- HiveMQ Cloud MQTT TLS Broker ---
MQTT_BROKER = "0899f05ecad5437d93d7fbd8b9b96f70.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_CLIENT_ID = "esp32_light_01"
MQTT_USERNAME = "SMART_AI_IoT"
MQTT_PASSWORD = "YOUR_MQTT_PASSWORD_HERE"
