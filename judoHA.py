#!/usr/bin/python3
# -*- coding: utf-8 -*-
import urllib3
import json
import time
import requests
from paho.mqtt import client as mqtt
from datetime import datetime
from requests.adapters import HTTPAdapter
import ssl

urllib3.disable_warnings()

# --- Globale Konfiguration ---
BASE_URL = "https://192.168.178.XX:8124"
USERNAME = "USER"
PASSWORD = "PW"
SERIAL = "SERIAL"

# MQTT-Konfiguration
MQTT_BROKER = "192.168.178.XX"
MQTT_PORT = 1883
MQTT_USER = "MQTTUSER"
MQTT_PASSWORD = "MQTTPWD"
MQTT_CLIENT_ID = "judo_i_soft_plus"
BASE_TOPIC = f"homeassistant/sensor/{MQTT_CLIENT_ID}"
COMMAND_TOPIC = f"{MQTT_CLIENT_ID}/command"
STATE_TOPIC_BASE = f"{MQTT_CLIENT_ID}/state"

class LegacySSLAdapter(HTTPAdapter):
    def __init__(self, *args, **kwargs):
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        self.ssl_context.set_ciphers('DEFAULT@SECLEVEL=1')
        super().__init__(*args, **kwargs)

    def init_poolmanager(self, *args, **kwargs):
        kwargs['ssl_context'] = self.ssl_context
        return super().init_poolmanager(*args, **kwargs)

# --- Judo API Funktionen ---
def send_http_get_request(session, url):
    try:
        response = session.get(url, verify=False, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Fehler beim Senden der GET-Anfrage (erwarte JSON): {e}")
        return None

def login(session):
    login_url = f"{BASE_URL}?group=register&command=login&msgnumber=2&name=login&user={USERNAME}&password={PASSWORD}&role=customer"
    response = send_http_get_request(session, login_url)
    if response:
        return response.get("token")
    return None

def get_data(session, token, group, command, **kwargs):
    if not token:
        print("Fehler: Ungültiges Token für get_data.")
        return None
    url = f"{BASE_URL}?group={group}&command={command}&msgnumber=1&token={token}"
    for key, value in kwargs.items():
        url += f"&{key}={value}"
    response = send_http_get_request(session, url)
    if response:
        return response.get("data")
    return None

def sende_get_befehl(session, url):
    """Sendet einen GET-Befehl an die Anlage, ohne eine JSON-Antwort zu erwarten."""
    try:
        response = session.get(url, verify=False, timeout=15)
        response.raise_for_status()
        print(f"GET-Befehl erfolgreich gesendet. HTTP-Status: {response.status_code}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Fehler beim Senden des GET-Befehls: {e}")
        return False

# --- MQTT-Funktionen ---
def publish_auto_discovery(client):
    print("Veröffentliche Auto-Discovery Konfiguration...")
    sensors = {
        "Rohwasser": {"unit_of_measurement": "m³", "device_class": "water", "state_class": "total_increasing"},
        "Entkalktes_Wasser": {"unit_of_measurement": "m³", "device_class": "water", "state_class": "total_increasing"},
        "Wasserverbrauch_Durchschnitt": {"unit_of_measurement": "L/Tag"},
        "Aktuelle_Menge": {"unit_of_measurement": "L/min"}, "Salzmenge": {"unit_of_measurement": "kg"},
        "Salzreichweite": {"unit_of_measurement": "Tage"}, "Resthaerte": {"unit_of_measurement": "°dH"},
        "Ventilstatus": {}, "Standby_Status": {}, "Wasserstop_Entnahmezeit": {"unit_of_measurement": "s"},
        "Wasserstop_Durchflussrate": {"unit_of_measurement": "L/min"}, "Wasserstop_Menge": {"unit_of_measurement": "L"}, "Urlaubsmodus": {},
    }
    device_info = {"identifiers": [MQTT_CLIENT_ID], "name": "Judo i-soft plus", "manufacturer": "Judo", "model": "i-soft plus"}
    for sensor_name, config in sensors.items():
        object_id = sensor_name.replace(' ', '_').lower()
        discovery_topic = f"{BASE_TOPIC}/{object_id}/config"
        discovery_payload = {
            "unique_id": f"{MQTT_CLIENT_ID}_{object_id}", "name": f"Judo {sensor_name.replace('_', ' ')}",
            "state_topic": f"{STATE_TOPIC_BASE}/{object_id}", "device": device_info, **config
        }
        client.publish(discovery_topic, json.dumps(discovery_payload), retain=True)
    client.publish(f"homeassistant/switch/{MQTT_CLIENT_ID}/valve/config", json.dumps({
        "unique_id": f"{MQTT_CLIENT_ID}_valve", "name": "Judo Ventil", "command_topic": COMMAND_TOPIC,
        "state_topic": f"{STATE_TOPIC_BASE}/ventilstatus", "payload_on": "open", "payload_off": "close", "device": device_info
    }), retain=True)
    client.publish(f"homeassistant/number/{MQTT_CLIENT_ID}/hardness/config", json.dumps({
        "unique_id": f"{MQTT_CLIENT_ID}_hardness", "name": "Judo Resthärte", "command_topic": COMMAND_TOPIC,
        "state_topic": f"{STATE_TOPIC_BASE}/resthaerte", "min": 1, "max": 14, "step": 1, "unit_of_measurement": "°dH", "device": device_info
    }), retain=True)
    print("Auto-Discovery Konfiguration abgeschlossen.")

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("MQTT verbunden!")
        publish_auto_discovery(client)
        client.subscribe(COMMAND_TOPIC)
        print(f"Command-Topic abonniert: {COMMAND_TOPIC}")
    else:
        print(f"MQTT-Verbindung fehlgeschlagen: {rc}")

def on_message(client, userdata, msg):
    """Verarbeitet eingehende MQTT-Befehle."""
    command_payload = msg.payload.decode("utf-8")
    print(f"Befehl empfangen: {command_payload}")
    
    token = userdata.get('token')
    session = userdata.get('session')

    if not token or not session:
        print("Kann Befehl nicht ausführen, da kein gültiges Token oder Session vorhanden ist.")
        return

    # Ventilsteuerung via GET mit korrekten Parametern
    if command_payload.lower() in ("open", "close"):
        print(f"Setze Ventilstatus auf: {command_payload}")
        url = f"{BASE_URL}?group=waterstop&command=valve&msgnumber=1&token={token}&parameter={command_payload.lower()}"
        sende_get_befehl(session, url)

        time.sleep(2)
        new_valve_status = get_data(session, token, "waterstop", "valve")
        if new_valve_status is not None and new_valve_status not in ("invalid token", "not logged in"):
            client.publish(f"{STATE_TOPIC_BASE}/ventilstatus", new_valve_status)

    # Resthärte-Einstellung via GET mit korrekten Parametern
    elif command_payload.isdigit():
        hardness = int(command_payload)
        print(f"Setze Resthärte auf: {hardness}°dH")
        # Der Befehl `residual hardness` enthält ein Leerzeichen, das von `requests` automatisch URL-kodiert wird.
        url = f"{BASE_URL}?group=settings&command=residual hardness&msgnumber=1&token={token}&parameter={hardness}"
        sende_get_befehl(session, url)

        time.sleep(2)
        new_hardness = get_data(session, token, "settings", "residual hardness")
        if new_hardness is not None and new_hardness not in ("invalid token", "not logged in"):
            client.publish(f"{STATE_TOPIC_BASE}/resthaerte", new_hardness)
    else:
        print(f"Unbekannter Befehl empfangen: '{command_payload}'")

# --- Hauptprogramm ---
if __name__ == "__main__":
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=MQTT_CLIENT_ID)
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message
    
    session = requests.Session()
    session.mount('https://', LegacySSLAdapter())

    token = None
    client.user_data_set({'token': token, 'session': session})

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
    except Exception as e:
        print(f"Konnte keine Verbindung zum MQTT Broker herstellen: {e}")
        exit()

    while True:
        try:
            if not token:
                print("Kein Token vorhanden, versuche Login...")
                token = login(session)
                if token:
                    print("Login erfolgreich.")
                    client.user_data_set({'token': token, 'session': session})
                    send_http_get_request(session, f"{BASE_URL}?group=register&command=connect&msgnumber=5&token={token}&parameter=i-soft%20plus&serial%20number={SERIAL}")
                else:
                    print("Login fehlgeschlagen. Warte 60 Sekunden.")
                    time.sleep(60)
                    continue
            
            raw_water_total = get_data(session, token, "consumption", "water total")

            if raw_water_total in ("invalid token", "not logged in"):
                print(f"Token abgelaufen (Antwort: '{raw_water_total}'). Fordere neuen an.")
                token = None
                client.user_data_set({'token': token, 'session': session})
                continue
            
            if raw_water_total and isinstance(raw_water_total, str):
                try:
                    parts = raw_water_total.split()
                    if len(parts) >= 2:
                        rawwater = float(parts[-2])
                        decarbonatedwater = float(parts[-1])
                        client.publish(f"{STATE_TOPIC_BASE}/rohwasser", round(rawwater / 1000.0, 2))
                        client.publish(f"{STATE_TOPIC_BASE}/entkalktes_wasser", round(decarbonatedwater / 1000.0, 2))
                    else:
                        print(f"WARNUNG: Unerwartetes Format für Rohwasser-Daten: '{raw_water_total}'")
                except (ValueError, IndexError) as e:
                    print(f"FEHLER: Konnte Rohwasser-Daten ('{raw_water_total}') nicht verarbeiten: {e}")
            else:
                print(f"WARNUNG: Keine gültigen Rohwasser-Daten empfangen (Wert: {raw_water_total}).")

            data_points = {
                "wasserverbrauch_durchschnitt": ("consumption", "water average"), "aktuelle_menge": ("consumption", "actual quantity"),
                "salzmenge": ("consumption", "salt quantity"), "salzreichweite": ("consumption", "salt range"),
                "resthaerte": ("settings", "residual hardness"), "ventilstatus": ("waterstop", "valve"),
                "standby_status": ("waterstop", "standby"), "wasserstop_entnahmezeit": ("waterstop", "abstraction time"),
                "wasserstop_durchflussrate": ("waterstop", "flow rate"), "wasserstop_menge": ("waterstop", "quantity"),
                "urlaubsmodus": ("waterstop", "vacation"),
            }

            for name, (group, command) in data_points.items():
                value = get_data(session, token, group, command)
                if value is not None and value not in ("invalid token", "not logged in"):
                    client.publish(f"{STATE_TOPIC_BASE}/{name}", value)
            
            print("Daten erfolgreich aktualisiert.")
            time.sleep(300)

        except requests.exceptions.ConnectionError as e:
            print(f"Verbindungsfehler: {e}. Warte 60 Sekunden.")
            time.sleep(60)
        except Exception as e:
            print(f"Ein unerwarteter Fehler ist aufgetreten: {e}")
            token = None
            client.user_data_set({'token': token, 'session': session})
            time.sleep(60) token, 'session': session})
            time.sleep(60)
