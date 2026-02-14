# config.py
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883

# Structure des Topics (Respect des standards hiérarchiques)
TOPIC_BASE = "ville_master"
TOPIC_ANNOUNCE = f"{TOPIC_BASE}/annonces"  # Pour l'enregistrement dynamique 
TOPIC_ALERTS = f"{TOPIC_BASE}/alertes"      # Pour les notifs critiques 

# Seuils pour l'intelligence
LUMINOSITY_THRESHOLD = 300  # En dessous, c'est la nuit
TRAFFIC_PEAK = 80           # Au dessus, c'est un embouteillage