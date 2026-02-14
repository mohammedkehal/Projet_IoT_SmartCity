# devices.py
import paho.mqtt.client as mqtt
import json
import time
import threading
import random
from config import *

class SmartDevice(threading.Thread):
    def __init__(self, device_id, zone_id, device_type):
        super().__init__()
        self.id = device_id
        self.zone = zone_id
        self.type = device_type
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=device_id)
        self.running = True

    def connect_mqtt(self):
        try:
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.client.loop_start()
            # Service 1: Enregistrement dynamique [cite: 26, 27]
            self.announce()
        except Exception as e:
            print(f"❌ Erreur connexion {self.id}: {e}")

    def announce(self):
        """Envoie un message de naissance pour l'enregistrement automatique [cite: 27]"""
        payload = {
            "id": self.id,
            "zone": self.zone,
            "type": self.type,
            "status": "ONLINE",
            "timestamp": time.time()
        }
        self.client.publish(TOPIC_ANNOUNCE, json.dumps(payload), retain=True)
        print(f"📡 [ANNOUNCE] {self.id} enregistré dans la {self.zone}.")

    def stop(self):
        self.running = False
        self.client.loop_stop()
        self.client.disconnect()

class SmartLamp(SmartDevice):
    def __init__(self, device_id, zone_id):
        super().__init__(device_id, zone_id, "LAMPADAIRE")
        self.intensity = 0       
        self.is_on = False
        self.consumption = 0.0   
        self.has_failure = False # [cite: 22]
        self.current_traffic = 0 # Pour affichage dynamique du trafic

        self.topic_cmd = f"{TOPIC_BASE}/{self.zone}/{self.id}/cmd"
        self.topic_status = f"{TOPIC_BASE}/{self.zone}/{self.id}/status"

    def run(self):
        self.connect_mqtt()
        self.client.subscribe(self.topic_cmd)
        self.client.on_message = self.on_message

        while self.running:
            if not self.has_failure:
                # Simulation de consommation réaliste avec légère variation pour l'IA
                base_conso = (self.intensity / 100) * 100 if self.is_on else 0.5
                self.consumption = base_conso + random.uniform(0.1, 0.5)
            else:
                # Consommation résiduelle infime pour simuler une panne (Service 4) [cite: 33, 40]
                self.consumption = 0.1 

            # Payload complet pour le Dashboard (Service 2) [cite: 28]
            state_payload = {
                "id": self.id,
                "zone": self.zone,
                "intensity": self.intensity,
                "is_on": self.is_on,
                "consumption": round(self.consumption, 2),
                "traffic_level": self.current_traffic, # Pour le badge Trafic
                "failure": self.has_failure           # Pour le badge Santé
            }
            self.client.publish(self.topic_status, json.dumps(state_payload))
            time.sleep(2) # Fréquence d'envoi pour démo fluide

    def on_message(self, client, userdata, msg):
        """Réception des ordres (Service 3) [cite: 29, 31]"""
        try:
            cmd = json.loads(msg.payload.decode())
            action = cmd.get("action")
            
            if action == "SET_INTENSITY":
                val = cmd.get("value", 0)
                # On met à jour le trafic local reçu pour affichage
                self.current_traffic = cmd.get("traffic", self.current_traffic)
                self.intensity = val
                self.is_on = val > 0
                print(f"💡 {self.id}: {val}% (Trafic détecté: {self.current_traffic})")
            
            elif action == "TRIGGER_FAILURE": # [cite: 40]
                self.has_failure = True
                self.intensity = 0
                self.is_on = False
                alert = {"id": self.id, "type": "PANNE_MATERIELLE", "zone": self.zone}
                self.client.publish(TOPIC_ALERTS, json.dumps(alert))
                print(f"🔥 {self.id}: ALERTE PANNE !")

            elif action == "REBOOT": # 
                self.has_failure = False
                print(f"✅ {self.id}: Système réinitialisé.")

        except Exception as e:
            print(f"Erreur commande: {e}")

class TrafficSensor(SmartDevice):
    def __init__(self, device_id, zone_id):
        super().__init__(device_id, zone_id, "TRAFFIC_SENSOR")
        self.topic_data = f"{TOPIC_BASE}/{self.zone}/traffic"

    def run(self):
        self.connect_mqtt()
        while self.running:
            # Simulation : Fluide par défaut avec pics possibles [cite: 20]
            traffic_level = random.randint(10, 40) # Trafic fluide par défaut
            
            payload = {
                "sensor_id": self.id,
                "zone": self.zone,
                "value": traffic_level,
                "alert": traffic_level > TRAFFIC_PEAK # [cite: 42]
            }
            self.client.publish(self.topic_data, json.dumps(payload))
            time.sleep(10)

class LuminositySensor(SmartDevice):
    def __init__(self, device_id, zone_id):
        super().__init__(device_id, zone_id, "LUM_SENSOR")
        self.topic_data = f"{TOPIC_BASE}/{self.zone}/luminosity"
        self.lux = 1000

    def run(self):
        self.connect_mqtt()
        day_cycle = True
        
        while self.running:
            # Cycle accéléré pour la démonstration [cite: 22]
            if day_cycle:
                self.lux -= 100
                if self.lux <= 100: day_cycle = False
            else:
                self.lux += 100
                if self.lux >= 1000: day_cycle = True

            payload = {
                "sensor_id": self.id,
                "value": self.lux,
                "is_night": self.lux < LUMINOSITY_THRESHOLD # [cite: 39]
            }
            self.client.publish(self.topic_data, json.dumps(payload))
            print(f"☀️ {self.id}: Luminosité {self.lux} lux")
            time.sleep(5)