# core/config.py
import os
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # caminhos base
    base_dir: str = Field(default_factory=lambda: os.path.dirname(os.path.abspath(__file__)))
    project_root: str = Field(default_factory=lambda: os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
    data_dir: str = Field(default_factory=lambda: os.path.join(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")), "data"))
    styles_dir: str = Field(default_factory=lambda: os.path.join(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")), "styles"))

    # arquivos (podem ser sobrescritos via .env)
    csv_path: str = Field(default_factory=lambda: os.path.join(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")), "data", "visitas_acs.csv"))
    territorio_df: str = Field(default_factory=lambda: os.path.join(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")), "data", "territorio_df.geojson"))
    regioes_saude: str = Field(default_factory=lambda: os.path.join(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")), "data", "regioes_saude.geojson"))
    regioes_adm: str   = Field(default_factory=lambda: os.path.join(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")), "data", "regioes_adm.geojson"))

    class Config:
        env_file = os.path.join(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")), ".env")
        env_file_encoding = "utf-8"

@lru_cache()
def load_settings() -> Settings:
    return Settings()

