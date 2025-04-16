#!/usr/bin/python3
# -*- coding: utf-8 -*-
import urllib3
import json
import time
import gc
import os
import sys
import hashlib#!/usr/bin/python3
# -*- coding: utf-8 -*-
import urllib3
import json
import time
import gc
import os
import sys
import hashlib
import math
import datetime
import requests
from paho.mqtt import client as mqtt
from datetime import datetime
from datetime import date
from threading import Timer
import uuid  # Für eindeutige IDs

urllib3.disable_warnings()

# Konfiguration
base_url = "https://192.168.178.XXX:8124"
username = "XXXX"
password = "XXXXX"
serial = "1234567"

# MQTT-Konfiguration
mqtt_broker = "192.168.178.50"  # Ersetze dies mit deiner MQTT-Broker-Adresse
mqtt_port = 1883  # Standard-MQTT-Port
mqtt_user = "XXXXX"  # Ersetze dies mit deinem MQTT-Benutzernamen
mqtt_password = "XXXXX"  # Ersetze dies mit deinem MQTT-Passwort
mqtt_client_id = "judo_i_soft_plus"  # Eindeutige Client-ID
base_topic = "homeassistant/sensor/judo_i_soft_plus"  # Basis-Topic für Home Assistant Auto-Discovery
command_topic = "judo_i_soft_plus/command"  # Topic für Befehle (z.B. Ventilsteuerung, Wasserhärte)

# --- Funktionen ---

def send_http_get_request(url):
    """Sendet eine HTTP GET Anfrage und gibt die Antwort als JSON zurück."""
    try:
        response = requests.get(url, verify=False, timeout=30)  # verify=False, da SSL-Zertifikat vermutlich selbstsigniert ist
        response.raise_for_status()  # Wirft einen Fehler, wenn die Anfrage nicht erfolgreich war
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Fehler beim Senden der Anfrage: {e}")
        return None

def login():
    """Führt den Login durch und gibt das Token zurück."""
    login_url = f"{base_url}?group=register&command=login&msgnumber=2&name=login&user={username}&password={password}&role=customer"
    response = send_http_get_request(login_url)
    if response:
        return response.get("token")
    else:
        return None

def get_data(token, group, command, **kwargs):
    """Ruft Daten vom Judo i-soft plus ab."""
    url = f"{base_url}?group={group}&command={command}&msgnumber=1&token={token}"
    for key, value in kwargs.items():
        url += f"&{key}={value}"
    response = send_http_get_request(url)
    #print(response)
    if response:
        return response.get("data")
    else:
        return None

def set_residual_hardness(token, value):
    """Setzt den Sollwert für die Resthärte."""
    url = f"{base_url}?group=settings&command=residual%20hardness&msgnumber=1&token={token}&parameter={value}"
    response = send_http_get_request(url)
    if response and response.get("status") == "ok":
        print("Resthärte erfolgreich gesetzt.")
        return True
    else:
        print("Fehler beim Setzen der Resthärte.")
        return False

def control_valve(token, action):
    """Steuert das Wassersperrventil."""
    url = f"{base_url}?group=waterstop&command=valve&msgnumber=1&token={token}&parameter={action}"
    response = send_http_get_request(url)
    if response and response.get("status") == "ok":
        print(f"Wassersperrventil {action}.")
        return True
    else:
        print("Fehler beim Steuern des Wassersperrventils.")
        return False


class notification_entity():
        jetzt = datetime.now()
        print(jetzt.time())

# --- MQTT-Funktionen ---


def on_connect(client, userdata, flags, rc):
    global auto_discovery_done  # Zugriff auf die globale Variable
    if rc == 0:
        #print("MQTT verbunden!")
        publish_auto_discovery(client)
    else:
        print(f"MQTT-Verbindung fehlgeschlagen: {rc}")

def publish_auto_discovery(client):
    # Sensor-Auto-Discovery
    sensors = {
        "Rohwasser": {"unit_of_measurement": "m³", "device_class": "water", "state_class": "total_increasing"},
        "Entkalktes_Wasser": {"unit_of_measurement": "m³", "device_class": "water", "state_class": "total_increasing"},
        "Wasserverbrauch_Durchschnitt": {"unit": "L/Tag"},
        "Aktuelle_Menge": {"unit": "L/min"},
        "Salzmenge": {"unit": "kg"},
        "Salzbereich": {"unit": "Tage"},
        "Resthärte": {"unit": "°dH"},
        "Ventilstatus": {},
        "Standby_Status": {},
        "Wasserstop_Entnahmezeit": {"unit": "s"},
        "Wasserstop_Durchflussrate": {"unit": "L/min"},
        "Wasserstop_Menge": {"unit": "L"},
        "Urlaubsmodus": {},
    }

    for sensor_name, config in sensors.items():
        unique_id = f"{mqtt_client_id}_{sensor_name.replace(' ', '_').lower()}"
        discovery_topic = f"{base_topic}/{unique_id}/config"
        discovery_payload = {
            "unique_id": unique_id,
            "name": f"Judo i-soft plus {sensor_name}",
            "state_topic": f"judo_i_soft_plus/state/{sensor_name.replace(' ', '_').lower()}",
            "device": {
                "identifiers": [mqtt_client_id],
                "name": "Judo i-soft plus",
                "manufacturer": "Judo",
                "model": "i-soft plus",
            },
        }
        discovery_payload.update(config)  # Füge zusätzliche Konfigurationen hinzu
        client.publish(discovery_topic, json.dumps(discovery_payload), retain=True)

    # Switch-Auto-Discovery für das Wassersperrventil
    valve_discovery_topic = f"homeassistant/switch/judo_i_soft_plus/valve/config"
    valve_discovery_payload = {
        "unique_id": f"{mqtt_client_id}_valve",
        "name": "Judo i-soft plus Ventil",
        "command_topic": command_topic,
        "state_topic": "judo_i_soft_plus/state/ventilstatus",
        "payload_on": "open",
        "payload_off": "close",
        "device": {
            "identifiers": [mqtt_client_id],
            "name": "Judo i-soft plus",
            "manufacturer": "Judo",
            "model": "i-soft plus",
        },
    }
    client.publish(valve_discovery_topic, json.dumps(valve_discovery_payload), retain=True)

    # Number-Auto-Discovery für die Wasserhärte
    hardness_discovery_topic = f"homeassistant/number/judo_i_soft_plus/hardness/config"
    hardness_discovery_payload = {
        "unique_id": f"{mqtt_client_id}_hardness",
        "name": "Judo i-soft plus Wasserhärte",
        "command_topic": command_topic,
        "state_topic": "judo_i_soft_plus/state/resthaerte",
        "min": 1,
        "max": 14,
        "step": 1,
        "device": {
            "identifiers": [mqtt_client_id],
            "name": "Judo i-soft plus",
            "manufacturer": "Judo",
            "model": "i-soft plus",
        },
    }
    client.publish(hardness_discovery_topic, json.dumps(hardness_discovery_payload), retain=True)
    
def on_message(client, userdata, msg):
    try:
        if msg.topic == command_topic:
            command = msg.payload.decode("utf-8")
        if command == "open" or command == "close":
            control_valve(token, command)
        else:
            try:
                hardness = int(command)
                if 1 <= hardness <= 14:
                    set_residual_hardness(token, hardness)
            except ValueError:
                print(f"Ungültiger Befehl: {command}")
    except Exception as e:
        print(f"Fehler bei der Nachrichtenverarbeitung: {e}")

# MQTT-Client erstellen und verbinden
client = mqtt.Client(mqtt_client_id)
client.username_pw_set(mqtt_user, mqtt_password)
client.on_connect = on_connect
client.on_message = on_message
client.connect(mqtt_broker, mqtt_port, 60)
client.loop_start()

class Function_Caller(Timer):
        def run(self):
            while not self.finished.wait(self.interval):  
                self.function()




# --- Hauptprogramm ---

def main():
    now = datetime.now()
    if now.hour != 5:
        token = login()
        response2 = send_http_get_request(f"{base_url}?group=register&command=connect&msgnumber=5&token={token}&parameter=i-soft%20plus&serial%20number={serial}")
        #print(response2)
        time.sleep(3)
        if token:
            jetzt = datetime.now()
            print(jetzt.time())
            print("Login erfolgreich.")

            # Wasserverbrauch
            water_total = get_data(token, "consumption", "water total")
            total_water = water_total
            rawwater, decarbonatedwater = map(float, water_total.split(" ")[1:])

            rawwater_m3 = rawwater / 1000.0
            decarbonatedwater_m3 = decarbonatedwater / 1000.0

            water_average = get_data(token, "consumption", "water average")
            actual_quantity = get_data(token, "consumption", "actual quantity")
            salt_quantity = get_data(token, "consumption", "salt quantity")
            salt_range = get_data(token, "consumption", "salt range")
            residual_hardness = get_data(token, "settings", "residual hardness")
            valve_status = get_data(token, "waterstop", "valve")
            standby = get_data(token, "waterstop", "standby")
            abstraction_time = get_data(token, "waterstop", "abstraction time")
            flow_rate = get_data(token, "waterstop", "flow rate")
            quantity = get_data(token, "waterstop", "quantity")
            vacation = get_data(token, "waterstop", "vacation")
                    
            print("Daten abgeholt")
                
            # Daten über MQTT veröffentlichen
            client.publish(f"judo_i_soft_plus/state/rohwasser", str(rawwater_m3))
            client.publish(f"judo_i_soft_plus/state/entkalktes_wasser", str(decarbonatedwater_m3))
            client.publish(f"judo_i_soft_plus/state/wasserverbrauch_durchschnitt", str(water_average))
            client.publish(f"judo_i_soft_plus/state/aktuelle_menge", str(actual_quantity))
            client.publish(f"judo_i_soft_plus/state/salzmenge", str(salt_quantity))
            client.publish(f"judo_i_soft_plus/state/salzbereich", str(salt_range))
            client.publish(f"judo_i_soft_plus/state/resthaerte", str(residual_hardness))
            client.publish(f"judo_i_soft_plus/state/ventilstatus", str(valve_status))
            client.publish(f"judo_i_soft_plus/state/standby_status", str(standby))
            client.publish(f"judo_i_soft_plus/state/wasserstop_entnahmezeit", str(abstraction_time))
            client.publish(f"judo_i_soft_plus/state/wasserstop_durchflussrate", str(flow_rate))
            client.publish(f"judo_i_soft_plus/state/wasserstop_menge", str(quantity))
            client.publish(f"judo_i_soft_plus/state/urlaubsmodus", str(vacation))

            
            if now.hour == 22:  # Überprüfen, ob es 22:00 Uhr ist        
                # --- Wöchentlicher Wasserverbrauch ---
                today = datetime.now()
                year, month, day = today.year, today.month, today.day
                water_weekly = get_data(token, "consumption", "water weekly", year=year, month=month, day=day)

                # --- Jährlicher Wasserverbrauch ---
                water_yearly = get_data(token, "consumption", "water yearly", year=year)

                        # Wöchentlicher Wasserverbrauch per MQTT veröffentlichen
                print("Wöchentlicher Wasserverbrauch per MQTT veröffentlichen")
                if water_weekly:
                    days = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
                    values = list(map(float, water_weekly.split(" ")[1:]))
                    for i, day_value in enumerate(zip(days, values)):
                        client.publish(f"judo_i_soft_plus/state/wasser_woche/{day_value[0].lower()}",str(day_value[1]))

                # Jährlicher Wasserverbrauch per MQTT veröffentlichen
                print("Jährlicher Wasserverbrauch per MQTT veröffentlichen")
                if water_yearly:
                    months = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
                    values = list(map(float, water_yearly.split(" ")[1:]))
                    for i, month_value in enumerate(zip(months, values)):
                        client.publish(f"judo_i_soft_plus/state/wasser_jahr/{month_value[0].lower()}",str(month_value[1]))
            else:
                print("Wöchentlicher Wasserverbrauch wird nicht ausgeführt, da es nicht 22:00 Uhr ist.")

            jetzt = datetime.now()
            print(jetzt.time())
            print("Skript abgeschlossen.")
    else:
        print("Pause bis 6 Uhr - Script abgeschlossen um",)
Function_Caller(120, main).start()
import math
import datetime
import requests
from paho.mqtt import client as mqtt
from datetime import datetime
from datetime import date
from threading import Timer
import uuid  # Für eindeutige IDs

urllib3.disable_warnings()

# Konfiguration
base_url = "https://192.168.178.xxxx:8124"
username = "xxxx"
password = "xxxx"
serial = "xxxx"

# MQTT-Konfiguration
mqtt_broker = "192.168.178.yyyy"  # Ersetze dies mit deiner MQTT-Broker-Adresse
mqtt_port = 1883  # Standard-MQTT-Port
mqtt_user = "yyyyy"  # Ersetze dies mit deinem MQTT-Benutzernamen
mqtt_password = "yyyyy"  # Ersetze dies mit deinem MQTT-Passwort
mqtt_client_id = "judo_i_soft_plus"  # Eindeutige Client-ID
base_topic = "homeassistant/sensor/judo_i_soft_plus"  # Basis-Topic für Home Assistant Auto-Discovery
command_topic = "judo_i_soft_plus/command"  # Topic für Befehle (z.B. Ventilsteuerung, Wasserhärte)

# --- Funktionen ---

def send_http_get_request(url):
    """Sendet eine HTTP GET Anfrage und gibt die Antwort als JSON zurück."""
    try:
        response = requests.get(url, verify=False, timeout=30)  # verify=False, da SSL-Zertifikat vermutlich selbstsigniert ist
        response.raise_for_status()  # Wirft einen Fehler, wenn die Anfrage nicht erfolgreich war
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Fehler beim Senden der Anfrage: {e}")
        return None

def login():
    """Führt den Login durch und gibt das Token zurück."""
    login_url = f"{base_url}?group=register&command=login&msgnumber=2&name=login&user={username}&password={password}&role=customer"
    response = send_http_get_request(login_url)
    if response:
        return response.get("token")
    else:
        return None

def get_data(token, group, command, **kwargs):
    """Ruft Daten vom Judo i-soft plus ab."""
    url = f"{base_url}?group={group}&command={command}&msgnumber=1&token={token}"
    for key, value in kwargs.items():
        url += f"&{key}={value}"
    response = send_http_get_request(url)
    #print(response)
    if response:
        return response.get("data")
    else:
        return None

def set_residual_hardness(token, value):
    """Setzt den Sollwert für die Resthärte."""
    url = f"{base_url}?group=settings&command=residual%20hardness&msgnumber=1&token={token}&parameter={value}"
    response = send_http_get_request(url)
    if response and response.get("status") == "ok":
        print("Resthärte erfolgreich gesetzt.")
        return True
    else:
        print("Fehler beim Setzen der Resthärte.")
        return False

def control_valve(token, action):
    """Steuert das Wassersperrventil."""
    url = f"{base_url}?group=waterstop&command=valve&msgnumber=1&token={token}&parameter={action}"
    response = send_http_get_request(url)
    if response and response.get("status") == "ok":
        print(f"Wassersperrventil {action}.")
        return True
    else:
        print("Fehler beim Steuern des Wassersperrventils.")
        return False


class notification_entity():
        jetzt = datetime.now()
        print(jetzt.time())

# --- MQTT-Funktionen ---


def on_connect(client, userdata, flags, rc):
    global auto_discovery_done  # Zugriff auf die globale Variable
    if rc == 0:
        #print("MQTT verbunden!")
        publish_auto_discovery(client)
    else:
        print(f"MQTT-Verbindung fehlgeschlagen: {rc}")

def publish_auto_discovery(client):
    # Sensor-Auto-Discovery
    sensors = {
        "Rohwasser": {"unit": "L", "device_class": "water", "state_class": "total_increasing"},
        "Entkalktes_Wasser": {"unit": "L", "device_class": "water", "state_class": "total_increasing"},
        "Wasserverbrauch_Durchschnitt": {"unit": "L/Tag"},
        "Aktuelle_Menge": {"unit": "L/min"},
        "Salzmenge": {"unit": "kg"},
        "Salzbereich": {"unit": "Tage"},
        "Resthärte": {"unit": "°dH"},
        "Ventilstatus": {},
        "Standby_Status": {},
        "Wasserstop_Entnahmezeit": {"unit": "s"},
        "Wasserstop_Durchflussrate": {"unit": "L/min"},
        "Wasserstop_Menge": {"unit": "L"},
        "Urlaubsmodus": {},
    }

    for sensor_name, config in sensors.items():
        unique_id = f"{mqtt_client_id}_{sensor_name.replace(' ', '_').lower()}"
        discovery_topic = f"{base_topic}/{unique_id}/config"
        discovery_payload = {
            "unique_id": unique_id,
            "name": f"Judo i-soft plus {sensor_name}",
            "state_topic": f"judo_i_soft_plus/state/{sensor_name.replace(' ', '_').lower()}",
            "device": {
                "identifiers": [mqtt_client_id],
                "name": "Judo i-soft plus",
                "manufacturer": "Judo",
                "model": "i-soft plus",
            },
        }
        discovery_payload.update(config)  # Füge zusätzliche Konfigurationen hinzu
        client.publish(discovery_topic, json.dumps(discovery_payload), retain=True)

    # Switch-Auto-Discovery für das Wassersperrventil
    valve_discovery_topic = f"homeassistant/switch/judo_i_soft_plus/valve/config"
    valve_discovery_payload = {
        "unique_id": f"{mqtt_client_id}_valve",
        "name": "Judo i-soft plus Ventil",
        "command_topic": command_topic,
        "state_topic": "judo_i_soft_plus/state/ventilstatus",
        "payload_on": "open",
        "payload_off": "close",
        "device": {
            "identifiers": [mqtt_client_id],
            "name": "Judo i-soft plus",
            "manufacturer": "Judo",
            "model": "i-soft plus",
        },
    }
    client.publish(valve_discovery_topic, json.dumps(valve_discovery_payload), retain=True)

    # Number-Auto-Discovery für die Wasserhärte
    hardness_discovery_topic = f"homeassistant/number/judo_i_soft_plus/hardness/config"
    hardness_discovery_payload = {
        "unique_id": f"{mqtt_client_id}_hardness",
        "name": "Judo i-soft plus Wasserhärte",
        "command_topic": command_topic,
        "state_topic": "judo_i_soft_plus/state/resthaerte",
        "min": 1,
        "max": 14,
        "step": 1,
        "device": {
            "identifiers": [mqtt_client_id],
            "name": "Judo i-soft plus",
            "manufacturer": "Judo",
            "model": "i-soft plus",
        },
    }
    client.publish(hardness_discovery_topic, json.dumps(hardness_discovery_payload), retain=True)
    
def on_message(client, userdata, msg):
    try:
        if msg.topic == command_topic:
            command = msg.payload.decode("utf-8")
        if command == "open" or command == "close":
            control_valve(token, command)
        else:
            try:
                hardness = int(command)
                if 1 <= hardness <= 14:
                    set_residual_hardness(token, hardness)
            except ValueError:
                print(f"Ungültiger Befehl: {command}")
    except Exception as e:
        print(f"Fehler bei der Nachrichtenverarbeitung: {e}")

# MQTT-Client erstellen und verbinden
client = mqtt.Client(mqtt_client_id)
client.username_pw_set(mqtt_user, mqtt_password)
client.on_connect = on_connect
client.on_message = on_message
client.connect(mqtt_broker, mqtt_port, 60)
client.loop_start()

class Function_Caller(Timer):
        def run(self):
            while not self.finished.wait(self.interval):  
                self.function()




# --- Hauptprogramm ---

def main():
    
    token = login()
    response2 = send_http_get_request(f"{base_url}?group=register&command=connect&msgnumber=5&token={token}&parameter=i-soft%20plus&serial%20number=129741")
    #print(response2)
    time.sleep(3)
    if token:
        jetzt = datetime.now()
        print(jetzt.time())
        print("Login erfolgreich.")

        # Wasserverbrauch
        water_total = get_data(token, "consumption", "water total")
        total_water = water_total
        rawwater, decarbonatedwater = map(float, water_total.split(" ")[1:])

        water_average = get_data(token, "consumption", "water average")
        actual_quantity = get_data(token, "consumption", "actual quantity")
        salt_quantity = get_data(token, "consumption", "salt quantity")
        salt_range = get_data(token, "consumption", "salt range")
        residual_hardness = get_data(token, "settings", "residual hardness")
        valve_status = get_data(token, "waterstop", "valve")
        standby = get_data(token, "waterstop", "standby")
        abstraction_time = get_data(token, "waterstop", "abstraction time")
        flow_rate = get_data(token, "waterstop", "flow rate")
        quantity = get_data(token, "waterstop", "quantity")
        vacation = get_data(token, "waterstop", "vacation")
                
        print("Daten abgeholt")
            
        # --- Wöchentlicher Wasserverbrauch ---
        today = datetime.now()
        year, month, day = today.year, today.month, today.day
        water_weekly = get_data(token, "consumption", "water weekly", year=year, month=month, day=day)

        # --- Jährlicher Wasserverbrauch ---
        water_yearly = get_data(token, "consumption", "water yearly", year=year)

        # Daten über MQTT veröffentlichen
        client.publish(f"judo_i_soft_plus/state/rohwasser", str(rawwater))
        client.publish(f"judo_i_soft_plus/state/entkalktes_wasser", str(decarbonatedwater))
        client.publish(f"judo_i_soft_plus/state/wasserverbrauch_durchschnitt", str(water_average))
        client.publish(f"judo_i_soft_plus/state/aktuelle_menge", str(actual_quantity))
        client.publish(f"judo_i_soft_plus/state/salzmenge", str(salt_quantity))
        client.publish(f"judo_i_soft_plus/state/salzbereich", str(salt_range))
        client.publish(f"judo_i_soft_plus/state/resthaerte", str(residual_hardness))
        client.publish(f"judo_i_soft_plus/state/ventilstatus", str(valve_status))
        client.publish(f"judo_i_soft_plus/state/standby_status", str(standby))
        client.publish(f"judo_i_soft_plus/state/wasserstop_entnahmezeit", str(abstraction_time))
        client.publish(f"judo_i_soft_plus/state/wasserstop_durchflussrate", str(flow_rate))
        client.publish(f"judo_i_soft_plus/state/wasserstop_menge", str(quantity))
        client.publish(f"judo_i_soft_plus/state/urlaubsmodus", str(vacation))
                
                # Wöchentlicher Wasserverbrauch per MQTT veröffentlichen
        print("Wöchentlicher Wasserverbrauch per MQTT veröffentlichen")
        if water_weekly:
            days = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
            values = list(map(float, water_weekly.split(" ")[1:]))
            for i, day_value in enumerate(zip(days, values)):
                client.publish(f"judo_i_soft_plus/state/wasser_woche/{day_value[0].lower()}",str(day_value[1]))

        # Jährlicher Wasserverbrauch per MQTT veröffentlichen
        print("Jährlicher Wasserverbrauch per MQTT veröffentlichen")
        if water_yearly:
            months = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
            values = list(map(float, water_yearly.split(" ")[1:]))
            for i, month_value in enumerate(zip(months, values)):
                client.publish(f"judo_i_soft_plus/state/wasser_jahr/{month_value[0].lower()}",str(month_value[1]))

        jetzt = datetime.now()
        print(jetzt.time())
        print("Skript abgeschlossen.")

Function_Caller(120, main).start()
