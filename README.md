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
