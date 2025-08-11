# judo-isoft-plus-to-mqtt
Dieses Python-Skript ist dazu konzipiert, Daten von einem Judo i-soft plus Wasserenthärtungssystem abzurufen und diese in ein MQTT-Netzwerk zu veröffentlichen, wodurch eine Integration in Home Assistant ermöglicht wird. Es führt einen Login auf der webbasierten Schnittstelle des Systems durch, um ein Authentifizierungstoken zu erhalten, und nutzt dieses, um verschiedene Datenpunkte wie Wasserverbrauch, Salzfüllstand, Wasserhärte und Ventilstatus abzufragen. Anschließend werden diese Daten in Echtzeit über MQTT-Topics publiziert und mithilfe von Home Assistant Auto-Discovery automatisch in Home Assistant als Sensoren, Schalter und Schieberegler eingerichtet. Dadurch können Nutzer das Wassersystem überwachen, steuern und automatisieren.

This Python script is designed to retrieve data from a Judo i-soft plus water softening system and publish it to an MQTT network, enabling integration with Home Assistant. It performs a login to the system's web-based interface to obtain an authentication token and uses this to retrieve various data points such as water consumption, salt level, water hardness and valve status. This data is then published in real time via MQTT topics and automatically set up in Home Assistant as sensors, switches and sliders using Home Assistant Auto-Discovery. This allows users to monitor, control and automate the water system.

Angelehnt an https://github.com/www-ShapeLabs-de/Judo-i-soft-save-plus-to-mqtt-bridge kann es über den Appdeamon auf Homeassist ausgeführt werden.

Based on https://github.com/www-ShapeLabs-de/Judo-i-soft-save-plus-to-mqtt-bridge, it can be executed via the Appdeamon on Homeassist.

Einrichtung von AppDaemon direkt in Home Assistant

MQTT sollte bereits eingerichtet und laufen.

Installiere AppDaemon und Studio Code Server (optional) über den Home Assistant Add-Ons Store 
(https://community.home-assistant.io/t/home-assistant-community-add-on-appdaemon-4/163259).

Konfiguriere AppDaemon mit den folgenden Einstellungen:
init_commands: []
python_packages:
  paho-mqtt
system_packages:

Kopiere die apps.yaml aus dem Github Ordner in den Ordner /addon_configs/a0d7b954_appdaemon/apps/ -> über Studio Code Server. 

Kopiere die judo.py und main_entity.py aus dem Github Ordner in den Ordner /addon_configs/a0d7b954_appdaemon/apps/main -> über Studio Code Server. (Wenn der Ordner nicht existiert, erstelle ihn)

Passe die judo.py-Datei an dein System an über Studio Code Server.

Starte AppDaemon und überprüfe die Protokolle auf mögliche Fehler. ACHTUNG der erste Start dauert ca. 10 Minuten.

Du kannst problemlos weitere Skripte in die main_entity.py-Datei (Hauptdatei, in der alle Skripte aufgerufen werden) hinzufügen.

ODER bei mir läuft es inzwischen als Extra Script im Terminal

-----

# Judo i-soft plus MQTT Integration für Home Assistant

Dieses Projekt ermöglicht die Integration einer Judo i-soft plus Wasserenthärtungsanlage in Home Assistant. Ein Python-Skript fragt die Daten der Anlage über deren lokale API ab und veröffentlicht sie über MQTT. Home Assistant kann diese Daten dann mittels MQTT Auto-Discovery automatisch als Entitäten erkennen und darstellen.

\!

## Features

  * Auslesen von Verbrauchsdaten (Rohwasser, Weichwasser, Durchschnitt)
  * Überwachung des Salzvorrats (Menge und Reichweite)
  * Anzeige und Steuerung der Resthärte
  * Status und Steuerung des Leckageschutz-Ventils
  * Anzeige weiterer Statusinformationen (Standby, Urlaubsmodus etc.)
  * Automatische Erstellung aller Entitäten in Home Assistant durch MQTT Auto-Discovery
  * Stabiler Betrieb durch automatische Neuanmeldung bei Session-Timeout

-----

## Voraussetzungen

  * Eine laufende **Home Assistant Instanz**.
  * Ein **MQTT Broker**, der in Home Assistant integriert ist (z. B. das "Mosquitto broker" Add-on).
  * Die **Zugangsdaten** für Ihre Judo i-soft Anlage (Benutzername, Passwort, Seriennummer).
  * Die **IP-Adresse** Ihrer Judo i-soft Anlage im lokalen Netzwerk.

-----

## Installation

Die Installation erfolgt über das "Advanced SSH & Web Terminal" Add-on in Home Assistant.

### 1\. SSH Add-on installieren

Stellen Sie sicher, dass das **"Advanced SSH & Web Terminal"** Add-on aus dem Add-on Store installiert und funktionsbereit ist.

### 2\. Python-Skript erstellen

Erstellen Sie eine Datei im Konfigurationsverzeichnis von Home Assistant.

  * **Pfad:** `/config/judoHA.py`


## Konfiguration

Passen Sie die folgenden Variablen am Anfang der `judoHA.py`-Datei an Ihre Umgebung an:

  * **Judo-Anlage:**
      * `BASE_URL`: Die URL Ihrer Anlage, z.B. `"https://192.168.1.50:8124"`.
      * `USERNAME`: Ihr Judo-Benutzername.
      * `PASSWORD`: Ihr Judo-Passwort.
      * `SERIAL`: Die Seriennummer Ihrer Anlage.
  * **MQTT-Broker:**
      * `MQTT_BROKER`: Die IP-Adresse oder der Hostname Ihres MQTT-Brokers.
      * `MQTT_USER`: Der Benutzername für den MQTT-Broker.
      * `MQTT_PASSWORD`: Das Passwort für den MQTT-Benutzer.
      * `MQTT_CLIENT_ID`: Kann im Normalfall unverändert bleiben.

-----

## Dienst einrichten und starten

Damit das Skript automatisch mit Home Assistant startet, konfigurieren Sie das SSH Add-on.

1.  Gehen Sie zu **Einstellungen \> Add-ons \> Advanced SSH & Web Terminal**.

2.  Öffnen Sie den Tab **"Konfiguration"**.

3.  Fügen Sie unter `init_commands` die folgenden Befehle hinzu:

    ```yaml
    init_commands:
      - pip install requests paho-mqtt
      - python3 /config/judoHA.py
    ```

4.  Speichern Sie die Konfiguration.

5.  Starten (oder starten Sie neu) das Add-on.

6.  Überprüfen Sie den Erfolg im Tab **"Protokoll"** des Add-ons. Erfolgsmeldungen wie `Login erfolgreich` und `Daten erfolgreich aktualisiert` sollten erscheinen.

-----

## Verwendung in Home Assistant

Nach dem erfolgreichen Start des Skripts werden die Judo-Entitäten automatisch in Home Assistant angelegt.

  * Gehen Sie zu **Einstellungen \> Geräte & Dienste \> Entitäten**.
  * Suchen Sie nach `judo`.
  * Alle Sensoren (z. B. `sensor.judo_salzmenge`), der Schalter (`switch.judo_ventil`) und der Number-Input (`number.judo_resthaerte`) sollten nun verfügbar sein und können in Dashboards und Automationen verwendet werden.

-----

## Lizenz

Dieses Projekt steht unter der MIT-Lizenz.
