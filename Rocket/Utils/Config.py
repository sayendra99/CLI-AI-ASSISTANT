from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    
    # API Keys
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    
    # Model Configuration
    model: str = Field(default="gpt-3.5-turbo-preview", alias="MODEL")
    gemini_model: str = Field(default="gemini-1.5-flash", alias="GEMINI_MODEL")
    max_tokens: int = Field(default=2000, alias="MAX_TOKENS")
    temperature: float = Field(default=0.7, alias="TEMPERATURE")
    max_retries: int = Field(default=3, alias="MAX_RETRIES")
    retry_delay: float = Field(default=1.0, alias="RETRY_DELAY")

    # OpenAI Compat Configuration
    openai_compat_url: str = Field(default="", alias="OPENAI_COMPAT_URL")
    openai_compat_model: str = Field(default="", alias="OPENAI_COMPAT_MODEL")
    openai_compat_api_key: str = Field(default="", alias="OPENAI_COMPAT_API_KEY")
    
    # App Configuration
    data_dir: Path = Field(default=Path.home() / ".rocket" / "DATA_DIR")

    # Provider Selection
    preferred_provider: str = Field(default="", alias="PREFERRED_PROVIDER")
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
settings = Settings()