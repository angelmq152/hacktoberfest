from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    telegram_token: str = ""
    allowed_user_ids: str = ""
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""
    elevenlabs_tts_model: str = "eleven_flash_v2_5"
    gemma_api_key: str = ""
    gemma_base_url: str = ""                 # empty -> Google AI Studio (Gemini API)
    gemma_model: str = "gemma-3-27b-it"
    docker_host: str = "tcp://socket-proxy:2375"
    managed_label: str = "hackbot.manage=true"
    out_dir: Path = Path("/data/out")

    @property
    def allowed_ids(self) -> set[int]:
        return {int(x) for x in self.allowed_user_ids.split(",") if x.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
