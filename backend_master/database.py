from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

DATABASE_URL = "sqlite:///./smartcity_pro.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- MODÈLES DE DONNÉES (SCHEMA) ---

class Lampadaire(Base):
    __tablename__ = "lampadaires"
    id = Column(String, primary_key=True, index=True)
    zone = Column(String) # Association zone géographique [cite: 27]
    is_on = Column(Boolean, default=False) # État en temps réel [cite: 28]
    intensity = Column(Integer, default=0) # Intensité variable [cite: 19]
    consumption = Column(Float, default=0.0) # Consommation électrique [cite: 21]
    
    # --- VISIBILITÉ ÉTAT DE SANTÉ & TRAFIC ---
    traffic_level = Column(Integer, default=0) # Niveau de trafic [cite: 20]
    
    # Remplacer le simple Boolean par un String pour détailler la panne
    # Permet d'afficher : "OK", "AMPOULE_GRILLEE", "SURTENSION" [cite: 22, 40]
    health_status = Column(String, default="OK") 
    
    last_update = Column(DateTime, default=datetime.utcnow)

class MesureEnv(Base):
    __tablename__ = "mesures_environnement"
    id = Column(Integer, primary_key=True, index=True)
    zone = Column(String)
    luminosity = Column(Float) # Capteur de luminosité [cite: 19]
    
    # --- AJOUT POUR LE BADGE JOUR/NUIT ---
    # Permet au Dashboard d'afficher ☀️ ou 🌙 
    is_night = Column(Boolean, default=False) 
    
    traffic_level = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow)

class Alerte(Base):
    __tablename__ = "alertes"
    id = Column(Integer, primary_key=True, index=True)
    type = Column(String) # Ex: ANOMALIE_IA, PANNE_CRITIQUE [cite: 32, 40]
    device_id = Column(String)
    
    # Message détaillé pour l'intervention de l'IA
    # Ex: "L'IA a détecté une surconsommation de +20%" 
    message = Column(String) 
    
    timestamp = Column(DateTime, default=datetime.utcnow)
    resolved = Column(Boolean, default=False)

def init_db():
    Base.metadata.create_all(bind=engine)