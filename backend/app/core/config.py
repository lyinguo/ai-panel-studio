from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    deepseek_api_key: str = ""
    database_url: str = "sqlite:///./ai_panel.db"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()