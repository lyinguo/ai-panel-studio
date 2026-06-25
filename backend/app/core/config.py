from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── LLM API ──
    deepseek_api_key: str = ""
    deepseek_api_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    # ── 备用供应商（兼容 OpenAI 接口） ──
    llm_provider: str = "deepseek"
    openai_api_key: str = ""
    openai_api_base_url: str = ""
    openai_model: str = ""

    # ── 数据库 ──
    database_url: str = "sqlite:///./ai_panel.db"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()