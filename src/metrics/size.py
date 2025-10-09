from typing import Dict
from huggingface_service import ModelMetadata

def score_model_size(metadata: ModelMetadata) -> Dict[str, float]:
    """Return size compatibility scores per hardware type (0–1)."""
    size_mb = metadata.modelSize / (1024 * 1024)  # MB
    size_gb = size_mb / 1024

    def normalize(value: float, min_val: float, max_val: float) -> float:
        """Linearly scale size into [0,1], clamped."""
        if value <= min_val:
            return 1.0
        elif value >= max_val:
            return 0.0
        return 1 - ((value - min_val) / (max_val - min_val))

    return {
        "raspberry_pi": normalize(size_gb, 0.0, 1.0),   # best <1GB
        "jetson_nano": normalize(size_gb, 0.0, 2.0),   # best <2GB
        "desktop_pc": normalize(size_gb, 0.0, 6.0),    # best <6GB
        "aws_server": normalize(size_gb, 0.0, 10.0),   # best <10GB
    }
