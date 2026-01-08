from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    model: str = Field(default="gpt-3.5-turbo-preview", alias="MODEL")
    max_tokens: int = Field(default=2000, alias="MAX_TOKENS")
    temperature: float = Field(default=0.7, alias="TEMPERATURE")
    
    #A App Configuration
    data_dir: Path = Field(default=Path.home() / ".rocket" / "DATA_DIR")
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8",case_sensitive=False,extra="ignore")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
settings = Settings()