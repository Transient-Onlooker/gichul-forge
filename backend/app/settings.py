from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    storage_dir: str = "./storage"
    retention_days: int = 7
    max_upload_mb: int = 300
    review_policy: str = "auto_when_confident"
    confidence_threshold: float = 0.72

    nvidia_nim_api_key: str = ""
    nvidia_nim_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_nim_text_model: str = "nvidia/nemotron-3-ultra-550b-a55b"
    nvidia_nim_vision_model: str = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
    nvidia_nim_ocr_model: str = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
    nvidia_nim_metadata_model: str = "nvidia/nemotron-3-ultra-550b-a55b"
    nvidia_nim_tagger_model: str = "nvidia/nemotron-3-ultra-550b-a55b"
    nvidia_nim_qa_model: str = "nvidia/nemotron-3-ultra-550b-a55b"
    nvidia_nim_timeout_seconds: int = 120
    nvidia_nim_max_retries: int = 2

    mermiad_korean_font_path: str = ""

    model_config = SettingsConfigDict(
        env_file=("../.env.local", ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def storage_path(self) -> Path:
        return Path(self.storage_dir).resolve()

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def public_config(self) -> dict:
        return {
            "appEnv": self.app_env,
            "reviewPolicy": self.review_policy,
            "confidenceThreshold": self.confidence_threshold,
            "retentionDays": self.retention_days,
            "maxUploadMb": self.max_upload_mb,
            "nim": {
                "baseUrl": self.nvidia_nim_base_url,
                "hasApiKey": bool(self.nvidia_nim_api_key),
                "models": {
                    "text": self.nvidia_nim_text_model,
                    "vision": self.nvidia_nim_vision_model,
                    "ocr": self.nvidia_nim_ocr_model,
                    "metadata": self.nvidia_nim_metadata_model,
                    "tagger": self.nvidia_nim_tagger_model,
                    "qa": self.nvidia_nim_qa_model,
                },
            },
        }


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.storage_path.mkdir(parents=True, exist_ok=True)
    return settings
