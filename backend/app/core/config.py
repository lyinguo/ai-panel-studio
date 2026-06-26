from pathlib import Path

from pydantic_settings import BaseSettings


def _find_env_file() -> str:
    """从多个可能的位置查找 .env 文件。

    搜索优先级：
    1. backend/.env（当前目录）
    2. 项目根目录 /.env（与 backend/ 同级的 .env）
    """
    here = Path(__file__).resolve().parent  # backend/app/core/
    candidates = [
        here / "../../../.env",  # 项目根目录
        here / "../../.env",     # backend/ 目录
        Path(".env"),            # CWD
    ]
    for path in candidates:
        resolved = path.resolve()
        if resolved.exists():
            return str(resolved)
    return ".env"


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

    model_config = {
        "env_file": _find_env_file(),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()