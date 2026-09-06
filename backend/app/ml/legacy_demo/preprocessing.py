"""
Preprocessing utilities for feature normalization.
"""
from typing import List, Dict, Any
import numpy as np


class FeaturePreprocessor:
    """Preprocesses feature vectors for XGBoost inference."""

    def __init__(self):
        pass

    def transform_single(self, feature_dict: Dict[str, float], feature_cols: List[str]) -> np.ndarray:
        """Convert single feature dict to 2D numpy array [1, num_features]."""
        vector = [feature_dict.get(col, 0.0) for col in feature_cols]
        return np.array([vector], dtype=np.float32)

    def transform_batch(self, feature_dicts: List[Dict[str, float]], feature_cols: List[str]) -> np.ndarray:
        """Convert batch of feature dicts to 2D numpy array [N, num_features]."""
        matrix = []
        for fdict in feature_dicts:
            matrix.append([fdict.get(col, 0.0) for col in feature_cols])
        return np.array(matrix, dtype=np.float32)
