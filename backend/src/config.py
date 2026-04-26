"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Supabase
    supabase_url: str = ""
    supabase_service_key: str = ""
    supabase_jwt_secret: str = ""

    # Google Cloud
    google_cloud_project: str = ""
    google_cloud_location: str = "europe-west1"
    google_api_key: str = ""

    # Tavily
    tavily_api_key: str = ""

    # Gradium / Gradbot
    gradium_api_key: str = ""
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = "gemini-2.5-flash"

    # Google Calendar OAuth
    google_calendar_client_id: str = ""
    google_calendar_client_secret: str = ""

    # Server
    port: int = 8000
    env: str = "development"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
