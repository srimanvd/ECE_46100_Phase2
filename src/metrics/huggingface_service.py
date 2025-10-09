from huggingface_hub import HfApi, hf_api
from datetime import datetime
from typing import List, Optional
from src.utils.logging import logger


class ModelMetadata:
    """Represents metadata for a Hugging Face model."""

    def __init__(
        self,
        name: str,
        category: str,
        size: int,
        license: str,
        downloads: int,
        likes: int,
        last_modified: datetime,
        files: List[str],
    ):
        self.modelName = name
        self.modelCategory = category
        self.modelSize = size
        self.license = license
        self.timesDownloaded = downloads
        self.modelLikes = likes
        self.lastModified = last_modified
        self.files = files

    def __repr__(self):
        return (
            f"<ModelMetadata name={self.modelName}, category={self.modelCategory}, "
            f"size={self.modelSize}, downloads={self.timesDownloaded}, likes={self.modelLikes}>"
        )

    def pretty_size(self) -> str:
        """Return human-readable file size (e.g. '420 MB')."""
        size = self.modelSize
        for unit in ["bytes", "KB", "MB", "GB", "TB"]:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} PB"


class HuggingFaceService:
    """Wrapper around the Hugging Face API to fetch model information."""

    def __init__(self, token: Optional[str] = None):
        try:
            self.api = HfApi(token=token)
            # You can optionally add a login check to validate the token immediately
            if token:
                self.api.whoami()
        except Exception as e:
            logger.error(f"Failed to initialize HuggingFaceService, possibly due to an invalid token: {e}")
            # Set api to None so the service fails gracefully later
            self.api = None

    def fetch_model_metadata(self, model_id: str) -> Optional[ModelMetadata]:
        """Fetch metadata for a given model ID from Hugging Face Hub.

        Returns:
            ModelMetadata if successful, None if model not found or API error.
        """
        try:
            info = self.api.model_info(model_id)
        except hf_api.HfHubHTTPError as e:
            # print(f"❌ Error: Could not fetch model '{model_id}' — {e}")
            return None
        except Exception as e:
            # print(f"❌ Unexpected error: {e}")
            return None

        model_name = info.modelId
        category = info.pipeline_tag if info.pipeline_tag else "unknown"

        # ✅ Use usedStorage instead of summing siblings
        size = getattr(info, "usedStorage", 0) or 0

        # License might be a property or in cardData
        license_str = getattr(info, "license", None) or (
            info.cardData.get("license") if hasattr(info, "cardData") and info.cardData else None
        ) or "unspecified"

        downloads = getattr(info, "downloads", 0) or 0
        likes = getattr(info, "likes", 0) or 0
        last_modified = getattr(info, "lastModified", datetime.min) or datetime.min
        files = [s.rfilename for s in info.siblings]

        return ModelMetadata(
            name=model_name,
            category=category,
            size=size,
            license=license_str,
            downloads=downloads,
            likes=likes,
            last_modified=last_modified,
            files=files,
        )
    def get_raw_model_info(self, model_id: str):
        """Return the raw ModelInfo object from huggingface_hub (or None on failure)."""
        try:
            return self.api.model_info(model_id)
        except Exception as e:
            # print(f"Could not fetch raw model info for '{model_id}': {e}")
            return None
        


# -------------------------
# Temporary test block
# -------------------------
if __name__ == "__main__":
    service = HuggingFaceService()
    model_id = "tencent/SRPO"  # test with a known model
    metadata = service.fetch_model_metadata(model_id)
