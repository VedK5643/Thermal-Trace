"""
Production ML Model Training Script.
Trains a tuned multi-class XGBoost Classifier on synthetic/engineered NASA FIRMS telemetry
and serializes the model weights to backend/app/ml/models/xgboost_v1.joblib.
"""
import os
import json
import random
import joblib
import numpy as np
import pandas as pd
import hashlib
import datetime
from sklearn.model_selection import StratifiedKFold
from xgboost import XGBClassifier

ML_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(ML_DIR, "models")
MODEL_FILE = os.path.join(MODELS_DIR, "xgboost_v1.joblib")

CLASS_NAMES = ["industrial_fire", "gas_flare", "agricultural", "wildfire", "unknown"]
CLASS_MAP = {name: i for i, name in enumerate(CLASS_NAMES)}
REV_CLASS_MAP = {i: name for i, name in enumerate(CLASS_NAMES)}


def train_production_model(num_samples: int = 100000, export_dataset: bool = False):
    """Generates training data, fits XGBoost model, and optionally saves dataset artifact."""
    os.makedirs(MODELS_DIR, exist_ok=True)
    print(f"Generating {num_samples} training samples for Phase 6 production ML model...")

    np.random.seed(42)
    random.seed(42)

    ti4 = np.random.uniform(295.0, 368.0, num_samples)
    ti5 = np.random.uniform(280.0, 318.0, num_samples)
    frp = np.random.uniform(0.5, 45.0, num_samples)
    confidence = np.random.randint(40, 100, num_samples)
    is_day = np.random.choice([0.0, 1.0], size=num_samples)
    facility_dist_km = np.random.exponential(scale=22.0, size=num_samples)
    persistence_count = np.random.poisson(lam=2.8, size=num_samples)

    brightness_ratio = ti4 / (ti5 + 1e-5)
    temp_diff = ti4 - ti5
    frp_density = frp / (ti4 + 1e-5)
    confidence_norm = confidence / 100.0

    X = np.column_stack([
        ti4, ti5, brightness_ratio, temp_diff,
        frp, frp_density, confidence_norm, is_day,
        facility_dist_km, persistence_count
    ])

    y = []
    for i in range(num_samples):
        # Domain feature rules
        if ti4[i] > 342.0 and frp[i] > 16.0 and facility_dist_km[i] < 6.0:
            base = 1  # gas_flare
        elif ti4[i] > 326.0 and facility_dist_km[i] < 10.0:
            base = 0  # industrial_fire
        elif ti4[i] < 316.0 and frp[i] < 7.0 and facility_dist_km[i] > 12.0:
            base = 2  # agricultural
        else:
            base = 3  # wildfire

        # Environmental satellite noise (15%)
        if random.random() < 0.15:
            base = random.choice([0, 1, 2, 3, 4])
        y.append(base)

    y = np.array(y)

    feature_cols = [
        "bright_ti4", "bright_ti5", "brightness_ratio", "temp_diff",
        "frp", "frp_density", "confidence_norm", "is_day",
        "facility_dist_km", "persistence_count"
    ]

    if export_dataset:
        df = pd.DataFrame(X, columns=feature_cols)
        df["label"] = y
        
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "ml")
        os.makedirs(data_dir, exist_ok=True)
        parquet_path = os.path.join(data_dir, f"thermaleye_xgboost_v1_{num_samples}.parquet")
        meta_path = os.path.join(data_dir, f"thermaleye_xgboost_v1_{num_samples}.metadata.json")
        
        df.to_parquet(parquet_path, engine="pyarrow")
        
        with open(parquet_path, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
            
        metadata = {
            "dataset_name": f"thermaleye_xgboost_v1_{num_samples}",
            "dataset_version": "1.0",
            "source": "synthetic",
            "generation_basis": "existing FIRMS-derived feature space",
            "sample_count": num_samples,
            "feature_columns": feature_cols,
            "label_column": "label",
            "label_mapping": REV_CLASS_MAP,
            "model_version": "xgboost-v1",
            "generation_method": "numpy random synthesis based on domain rules",
            "generation_seed": 42,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "file_sha256": file_hash,
            "file_size_bytes": os.path.getsize(parquet_path)
        }
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2)
        print(f"Persisted training dataset to: {parquet_path}")

    print("Fitting XGBoost Classifier (n_estimators=150, max_depth=6)...")
    model = XGBClassifier(
        n_estimators=150,
        max_depth=6,
        learning_rate=0.08,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=42,
        eval_metric="mlogloss",
        n_jobs=-1
    )
    model.fit(X, y)

    artifact = {
        "model": model,
        "class_names": CLASS_NAMES,
        "feature_columns": feature_cols,
        "model_version": "xgboost-v1"
    }

    joblib.dump(artifact, MODEL_FILE)
    print(f"Successfully trained and saved model to: {MODEL_FILE}")


if __name__ == "__main__":
    train_production_model()
