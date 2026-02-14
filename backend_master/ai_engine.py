# backend_master/ai_engine.py
import pandas as pd
from sklearn.ensemble import IsolationForest
import numpy as np

class SmartCityAI:
    def __init__(self):
        # Modèle entraîné pour détecter les anomalies de consommation
        self.model = IsolationForest(contamination=0.05)
        # On simule un entraînement initial (en réalité, on chargerait des données historiques)
        X_train = np.array([[10, 10], [50, 50], [100, 100], [0, 0], [30, 30]])
        self.model.fit(X_train)

    def detect_anomaly(self, intensity, consumption):
        """
        Détecte si la consommation est anormale par rapport à l'intensité.
        Retourne True si c'est une anomalie.
        """
        # Si intensité 100% mais conso 0 -> Anomalie (Ampoule grillée)
        # Si intensité 0% mais conso > 0 -> Anomalie (Fuite courant)
        data = [[intensity, consumption]]
        prediction = self.model.predict(data)
        return prediction[0] == -1