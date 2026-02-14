from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal, init_db, Lampadaire, MesureEnv, Alerte
from pydantic import BaseModel
from typing import List
from fastapi.middleware.cors import CORSMiddleware
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import json
import threading
from datetime import datetime, timedelta # <--- AJOUT IMPORTANT POUR L'HISTORIQUE
from ai_engine import SmartCityAI

app = FastAPI(title="SmartCity IoT API - Master Grade", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ai_brain = SmartCityAI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- MQTT LISTENER (ÉCOUTE) ---
def mqtt_listener():
    def on_connect(client, userdata, flags, reason_code, properties=None):
        if reason_code == 0:
            print("🌐 [MQTT BRIDGE] Connexion réussie au Broker HiveMQ !")
            client.subscribe("ville_master/#")
        else:
            print(f"❌ [MQTT BRIDGE] Échec de connexion: {reason_code}")

    def on_message(client, userdata, msg):
        db = SessionLocal()
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            parts = topic.split("/")
            # Structure: ville_master / Zone / ID / status
            detected_zone = parts[1] if len(parts) > 1 else "Zone_A"

            # === MISE A JOUR STATUS & PANNES ===
            if "status" in topic:
                lamp_id = payload['id']
                lamp = db.query(Lampadaire).filter(Lampadaire.id == lamp_id).first()
                
                # Création si n'existe pas
                if not lamp:
                    lamp = Lampadaire(id=lamp_id, zone=detected_zone)
                    db.add(lamp)
                
                # Mise à jour des valeurs
                lamp.is_on = payload.get('is_on', False)
                lamp.intensity = payload.get('intensity', 0)
                lamp.consumption = payload.get('consumption', 0.0)
                lamp.zone = detected_zone
                if 'traffic_level' in payload: 
                    lamp.traffic_level = payload['traffic_level']
                
                # --- 1. GESTION DES PANNES (ET ENREGISTREMENT HISTORIQUE) ---
                if payload.get('failure', False):
                    lamp.health_status = "PANNE_SIGNALÉE"
                    
                    # ANTI-SPAM : Vérifie si la dernière alerte date de moins de 60s
                    last_alert = db.query(Alerte).filter(
                        Alerte.device_id == lamp_id,
                        Alerte.type == "PANNE_MATERIELLE"
                    ).order_by(Alerte.timestamp.desc()).first()
                    
                    now = datetime.now()
                    
                    # On enregistre SEULEMENT si c'est une nouvelle panne (> 60s)
                    if not last_alert or (now - last_alert.timestamp > timedelta(seconds=60)):
                        new_alert = Alerte(
                            device_id=lamp_id,
                            type="PANNE_MATERIELLE",
                            message="Ampoule grillée détectée (Conso ~0W)",
                            timestamp=now
                        )
                        db.add(new_alert)
                        print(f"🚨 [HISTORIQUE] Panne enregistrée pour {lamp_id}")

                elif lamp.is_on and lamp.consumption < 5:
                     lamp.health_status = "AMPOULE_GRILLÉE" # Cas rare
                elif lamp.consumption > 120:
                     lamp.health_status = "SURTENSION"
                else:
                     # Si pas de panne matérielle, on vérifie l'IA juste après
                     if lamp.health_status != "ANOMALIE_IA":
                        lamp.health_status = "OK"

                # --- 2. GESTION INTELLIGENCE ARTIFICIELLE (IA) ---
                if ai_brain.detect_anomaly(lamp.intensity, lamp.consumption):
                    lamp.health_status = "ANOMALIE_IA"
                    expected = (lamp.intensity / 100) * 100
                    
                    # Anti-spam pour l'IA aussi (Optionnel mais conseillé)
                    last_ia = db.query(Alerte).filter(
                        Alerte.device_id == lamp_id, Alerte.type == "ANOMALIE_IA"
                    ).order_by(Alerte.timestamp.desc()).first()
                    
                    now = datetime.now()
                    if not last_ia or (now - last_ia.timestamp > timedelta(seconds=60)):
                        msg_ia = f"Conso anormale: {lamp.consumption}W (Attendu: ~{expected:.1f}W)"
                        alerte = Alerte(type="ANOMALIE_IA", device_id=lamp.id, message=msg_ia, timestamp=now)
                        db.add(alerte)
                        print(f"⚠️ [IA] Anomalie enregistrée pour {lamp_id}")
                
                db.commit()

            # === MISE A JOUR ENVIRONNEMENT ===
            elif "luminosity" in topic:
                valeur = payload.get('value', 0)
                is_night_mode = valeur < 300 
                mesure = MesureEnv(zone=detected_zone, luminosity=valeur, is_night=is_night_mode, traffic_level=0)
                db.add(mesure)
                db.commit()
                
            elif "traffic" in topic:
                valeur = payload.get('value', 0)
                mesure = MesureEnv(zone=detected_zone, luminosity=0, traffic_level=valeur)
                db.add(mesure)
                db.commit()

        except Exception as e:
            print(f"⚠️ [MQTT ERROR] : {e}")
        finally:
            db.close()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect("broker.hivemq.com", 1883, 60)
    client.loop_forever()

@app.on_event("startup")
def startup_event():
    init_db()
    t = threading.Thread(target=mqtt_listener)
    t.daemon = True
    t.start()

# --- ROUTES API ---
@app.get("/api/lampadaires")
def get_lampadaires(db: Session = Depends(get_db)):
    return db.query(Lampadaire).all()

@app.get("/api/alertes")
def get_alertes(db: Session = Depends(get_db)):
    return db.query(Alerte).order_by(Alerte.timestamp.desc()).limit(20).all()

@app.get("/api/environnement")
def get_env_status(db: Session = Depends(get_db)):
    last_mesure = db.query(MesureEnv).filter(MesureEnv.luminosity > 0).order_by(MesureEnv.timestamp.desc()).first()
    if last_mesure:
        return {"is_night": last_mesure.is_night, "lux": last_mesure.luminosity}
    return {"is_night": False, "lux": 1000}

@app.post("/api/lampadaires/{lamp_id}/switch")
def switch_lamp(lamp_id: str, intensity: int, db: Session = Depends(get_db)):
    lamp = db.query(Lampadaire).filter(Lampadaire.id == lamp_id).first()
    if not lamp: raise HTTPException(status_code=404, detail="Lampe introuvable")
    
    target_zone = lamp.zone
    payload = {
        "action": "SET_INTENSITY", 
        "value": intensity, 
        "reason": "COMMANDE_VOCALE_IA",
        "traffic": lamp.traffic_level
    }
    
    topic = f"ville_master/{target_zone}/{lamp_id}/cmd"
    
    try:
        publish.single(topic, payload=json.dumps(payload), hostname="broker.hivemq.com", port=1883)
        print(f"✅ [BACKEND] Ordre IA envoyé à {lamp_id} ({intensity}%)")
    except Exception as e:
        print(f"❌ [ERREUR] {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    return {"message": "Ordre envoyé"}

@app.get("/api/lampadaires/{lamp_id}/historique")
def get_lamp_history(lamp_id: str, db: Session = Depends(get_db)):
    return db.query(Alerte).filter(Alerte.device_id == lamp_id).order_by(Alerte.timestamp.desc()).all()