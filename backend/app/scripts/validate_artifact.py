import warnings
import sys
import asyncio
import numpy as np
import xgboost
import sklearn
import joblib

from datetime import datetime, timezone
from sqlalchemy import text, NullPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.config import settings
from app.ml.source_features import build_source_features, FEATURE_COLUMNS

def get_versions():
    print("=== System Versions ===")
    print(f"Python: {sys.version.split(' ')[0]}")
    print(f"XGBoost: {xgboost.__version__}")
    print(f"Scikit-learn: {sklearn.__version__}")
    print(f"Joblib: {joblib.__version__}")
    print("========================\\n")

async def main():
    get_versions()
    
    artifact_path = "/home/yash-pandey/Documents/THERMAL SIH/backend/app/ml/models/thermalwatch_model.joblib"
    print(f"Loading artifact from: {artifact_path}")
    
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        artifact = joblib.load(artifact_path)
        if w:
            print("WARNINGS DURING LOAD:")
            for warn in w:
                print(f"  {warn.message}")
        else:
            print("No warnings during load.")
            
    print("\\n=== Artifact Structure ===")
    if isinstance(artifact, dict):
        print(f"Keys: {list(artifact.keys())}")
        xgb_model = artifact.get('model')
        label_encoder = artifact.get('label_encoder')
        feature_columns = artifact.get('feature_columns')
        
        print(f"Model: {type(xgb_model)}")
        print(f"LabelEncoder: {type(label_encoder)}")
        print(f"Classes: {label_encoder.classes_ if label_encoder else 'None'}")
        print(f"Feature Columns (Artifact): {feature_columns}")
        print(f"Feature Columns (Adapter) : {FEATURE_COLUMNS}")
        if feature_columns == FEATURE_COLUMNS:
            print("-> Feature lists MATCH EXACTLY.")
        else:
            print("-> Feature lists MISMATCH!")
    else:
        print("Artifact is not a dictionary. Something is wrong.")
        sys.exit(1)
        
    print("\\n=== Prediction Smoke Test ===")
    
    db_url = settings.get_database_url
    engine = create_async_engine(
        db_url, poolclass=NullPool,
        connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0}
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    
    cutoff = datetime.now(timezone.utc)
    async with session_factory() as session:
        res3 = await session.execute(text("SELECT round(latitude::numeric, 3), round(longitude::numeric, 3) FROM hotspots LIMIT 1 OFFSET 10"))
        row3 = res3.first()
        lat3, lon3 = float(row3[0]), float(row3[1]) if row3 else (25.942, 72.191)
        
        cases = [
            ("Multiple Observations", 25.942, 72.191),
            ("Single Observation", 29.458, 76.890),
            ("Arbitrary Hotspot", lat3, lon3),
        ]
        
        for name, lat, lon in cases:
            print(f"\\nTest Case: {name} ({lat}, {lon})")
            try:
                adapter_vec = await build_source_features(db=session, latitude=lat, longitude=lon, cutoff_ts=cutoff)
                vec_list = adapter_vec.to_list()
                print(f"  Vector: {vec_list}")
                
                # Reshape to 2D array for XGBoost
                X = np.array([vec_list], dtype=np.float32)
                
                preds = xgb_model.predict(X)
                pred_class_idx = preds[0]
                pred_class_name = label_encoder.inverse_transform([pred_class_idx])[0]
                
                probas = xgb_model.predict_proba(X)[0]
                sum_probas = float(np.sum(probas))
                
                print(f"  Predicted Class Index: {pred_class_idx}")
                print(f"  Predicted Class Name: {pred_class_name}")
                print(f"  Probabilities: {probas}")
                print(f"  Probas sum to: {sum_probas:.6f}")
                
                print("  Probability per class:")
                for i, c in enumerate(label_encoder.classes_):
                    print(f"    {c}: {probas[i]:.4f}")
            except Exception as e:
                print(f"  Error running prediction: {e}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
