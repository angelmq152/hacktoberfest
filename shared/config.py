from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    telegram_token: str
    allowed_user_ids: str
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""
    elevenlabs_tts_model: str = "eleven_flash_v2_5"
    gemma_api_key: str = ""
    gemma_base_url: str = ""
    gemma_model: str = "gemma-3-27b-it"
    docker_host: str = "tcp://socket-proxy:2375"
    managed_label: str = "hackbot.manage=true"
    out_dir: str = "/data/out"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def allowed_users_list(self) -> list[int]:
        if not self.allowed_user_ids:
            return []
        return [int(uid.strip()) for uid in self.allowed_user_ids.split(",") if uid.strip()]

settings = Settings()
