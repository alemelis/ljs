from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    prowlarr_url: str = "http://localhost:9696"
    prowlarr_api_key: str = ""

    torbox_api_key: str = ""
    torbox_base_url: str = "https://api.torbox.app"

    rclone_remote_name: str = "torbox"
    rclone_config_path: str = "./rclone.conf"
    local_storage_path: str = "./downloads"
    movies_path: str = "./downloads/movies"
    tv_path: str = "./downloads/tv"
    other_path: str = "./downloads"

    auto_sync: bool = False
    poll_interval_seconds: int = 10


settings = Settings()
