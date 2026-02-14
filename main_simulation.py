import paho.mqtt.client as mqtt
import json
import time
import random

# --- CONFIGURATION ---
BROKER = "broker.hivemq.com"
PORT = 1883
BASE_TOPIC = "ville_master"
ZONES = ["Zone_A", "Zone_B"]

class SimulatedDevice:
    def __init__(self, device_id, zone):
        self.id = device_id
        self.zone = zone
        self.is_on = False
        self.intensity = 0
        self.consumption = 0.0
        self.panne_materielle = False 
        self.anomalie_ia = False      
        self.local_traffic = 0 

    def update(self):
        # Calcul Consommation
        if self.is_on:
            self.consumption = self.intensity + random.uniform(-0.5, 0.5)
        else:
            self.consumption = 0.0

        # Pannes
        if self.panne_materielle and self.is_on: self.consumption = 0.1 
        if self.anomalie_ia: self.consumption = 150.0 

    def to_json(self):
        return json.dumps({
            "id": self.id, "zone": self.zone, "is_on": self.is_on,
            "intensity": self.intensity, "consumption": round(self.consumption, 2),
            "failure": self.panne_materielle, 
            "traffic_level": self.local_traffic # Envoi du trafic réaliste
        })

devices = [
    SimulatedDevice("Lamp_A1", "Zone_A"),
    SimulatedDevice("Lamp_A2", "Zone_A"),
    SimulatedDevice("Lamp_B1", "Zone_B") 
]

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        parts = msg.topic.split("/")
        target_id = parts[2]
        for dev in devices:
            if dev.zone == parts[1] and (dev.id == target_id or target_id == "all"):
                if payload["action"] == "SET_INTENSITY":
                    dev.intensity = payload["value"]
                    dev.is_on = dev.intensity > 0
    except: pass

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="Simu_Traffic_Realiste")
client.on_connect = lambda c, u, f, r, p: c.subscribe(f"{BASE_TOPIC}/+/+/cmd")
client.on_message = on_message
client.connect(BROKER, PORT, 60)
client.loop_start()

# --- BOUCLE DE DÉMONSTRATION RÉALISTE ---
print("📢 Scénario Vivant : Trafic variable (12..45..89..) + Voiture A1/A2 + Pannes")
compteur_absolu = 0

try:
    while True:
        compteur_absolu += 1
        cycle = compteur_absolu % 60 # Cycle de 60 secondes
        
        # --- GÉNÉRATION D'UN BRUIT DE FOND (Trafic léger partout par défaut) ---
        # Chaque lampe voit entre 0 et 15 voitures (C'est calme)
        for d in devices:
            d.local_traffic = random.randint(0, 15)

        # Reset des pannes avant la fin
        if cycle < 40:
            for d in devices:
                d.panne_materielle = False
                d.anomalie_ia = False

        # --- PHASE 1 : JOUR (0-10s) ---
        if cycle < 10:
            lux = 900
            phase = "☀️ JOUR (Trafic présent mais inutile)"
            # Même le jour, il y a des voitures (ex: 20-40), mais ça n'allume rien
            for d in devices: d.local_traffic = random.randint(20, 45)

        # --- PHASE 2 : NUIT CALME (10-20s) ---
        elif 10 <= cycle < 20:
            lux = 100
            phase = "🌙 NUIT FLUIDE (Varie entre 5 et 25)"
            # Trafic faible variable (jamais au dessus de 50)
            for d in devices: d.local_traffic = random.randint(5, 25)

        # --- PHASE 3 : LA VOITURE ROULE SOUS A1 (20-30s) ---
        elif 20 <= cycle < 30:
            lux = 100
            phase = "🚗 Voiture sous A1 (A1 fort, A2 faible)"
            # A1 voit beaucoup de trafic (entre 75 et 95) -> Déclenche 100%
            devices[0].local_traffic = random.randint(75, 95)
            # A2 reste calme (entre 0 et 10)
            devices[1].local_traffic = random.randint(0, 10)

        # --- PHASE 4 : LA VOITURE ROULE SOUS A2 (30-40s) ---
        elif 30 <= cycle < 40:
            lux = 100
            phase = "🚗 Voiture sous A2 (A1 faible, A2 fort)"
            # A1 redevient calme
            devices[0].local_traffic = random.randint(0, 10)
            # A2 voit le trafic (entre 75 et 95) -> Déclenche 100%
            devices[1].local_traffic = random.randint(75, 95)

        # --- PHASE 5 : PANNES (40-60s) ---
        else:
            lux = 100
            phase = "⚠️ PANNES (Trafic faible)"
            devices[2].panne_materielle = True # B1
            devices[0].anomalie_ia = True      # A1

        # ENVOI DES DONNÉES
        # 1. Luminosité Globale
        for zone in ZONES:
            client.publish(f"{BASE_TOPIC}/{zone}/luminosity", json.dumps({"value": lux}))
        
        # 2. Trafic & Status
        for dev in devices:
            # Envoi du trafic VARIABLE au contrôleur
            client.publish(f"{BASE_TOPIC}/{dev.zone}/{dev.id}/traffic", json.dumps({"value": dev.local_traffic}))
            
            dev.update()
            client.publish(f"{BASE_TOPIC}/{dev.zone}/{dev.id}/status", dev.to_json())

        print(f"⏱️ {cycle}s | {phase} | A1:{devices[0].local_traffic} A2:{devices[1].local_traffic}")
        time.sleep(1)

except KeyboardInterrupt:
    client.loop_stop()