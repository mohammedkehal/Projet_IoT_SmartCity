import paho.mqtt.client as mqtt
import json

# --- CONFIGURATION ---
BROKER = "broker.hivemq.com"
PORT = 1883
BASE_TOPIC = "ville_master"

# --- MÉMOIRE ---
city_memory = {}

def on_connect(client, userdata, flags, reason_code, properties=None):
    print(f"🧠 [CONTROLEUR] Connecté. Mode Hybride (Global + Suiveur).")
    # CHANGEMENT IMPORTANT ICI : On met /# pour écouter aussi les lampadaires précis
    client.subscribe(f"{BASE_TOPIC}/#")

def on_message(client, userdata, msg):
    try:
        topic = msg.topic
        payload = json.loads(msg.payload.decode())
        parts = topic.split("/")
        
        # On récupère la zone (ex: Zone_A)
        if len(parts) < 3: return
        zone = parts[1]

        # On s'assure que la mémoire existe pour cette zone
        if zone not in city_memory:
            city_memory[zone] = {"lux": 1000, "traffic": 0}

        # ====================================================
        # CAS 1 : C'EST UN MESSAGE GLOBAL (Ton code d'avant)
        # Ex: ville_master/Zone_A/luminosity
        # ====================================================
        if len(parts) == 3:
            data_type = parts[2]

            # Mise à jour de la mémoire (Ton code)
            if data_type == "luminosity":
                city_memory[zone]["lux"] = payload.get('value', 1000)
            elif data_type == "traffic":
                city_memory[zone]["traffic"] = payload.get('value', 0)
            
            # --- TES RÈGLES MÉTIERS (INCHANGÉES) ---
            lux = city_memory[zone]["lux"]
            traffic = city_memory[zone]["traffic"]
            new_intensity = 0
            mode = "JOUR ☀️"

            if lux > 300:
                new_intensity = 0
                mode = "JOUR ☀️"
            else:
                if traffic > 50: 
                    new_intensity = 100
                    mode = "🚨 NUIT + TRAFIC INTENSE"
                else:
                    new_intensity = 30
                    mode = "🌙 NUIT + TRAFIC FLUIDE"

            # Envoi commande GLOBALE ("all")
            cmd_topic = f"{BASE_TOPIC}/{zone}/all/cmd"
            payload_cmd = {"action": "SET_INTENSITY", "value": new_intensity}
            client.publish(cmd_topic, json.dumps(payload_cmd))
            
            if data_type == "luminosity" or (data_type == "traffic" and abs(traffic - 50) < 5):
                 print(f"⚖️ [GLOBAL] {zone} : {mode} -> {new_intensity}%")

        # ====================================================
        # CAS 2 : C'EST UN MESSAGE PRÉCIS (Le nouveau scénario)
        # Ex: ville_master/Zone_A/Lamp_A1/traffic
        # ====================================================
        elif len(parts) == 4 and parts[3] == "traffic":
            lamp_id = parts[2]      # Ex: Lamp_A1
            local_traffic = payload.get('value', 0)
            
            # On regarde s'il fait nuit dans la zone (grâce à ta mémoire)
            current_lux = city_memory[zone]["lux"]

            # On agit SEULEMENT s'il fait nuit (Si jour, on laisse éteint)
            if current_lux < 300:
                target_val = 30 # Par défaut nuit calme
                
                if local_traffic > 50:
                    target_val = 100 # Voiture détectée !
                    print(f"🚗 [SUIVEUR] Trafic sous {lamp_id} -> 100%")
                
                # On commande UNIQUEMENT ce lampadaire
                client.publish(f"{BASE_TOPIC}/{zone}/{lamp_id}/cmd", json.dumps({"action": "SET_INTENSITY", "value": target_val}))

    except Exception as e:
        print(f"Erreur: {e}")

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT, 60)
client.loop_forever()