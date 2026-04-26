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
    # Lighter model used for tasks that don't need extended reasoning and
    # would otherwise be truncated by Gemini Flash's thinking budget
    # (e.g. structured extraction over long inputs). Empty → fall back to
    # `llm_model`.
    llm_lite_model: str = ""

    # Google Calendar OAuth
    google_calendar_client_id: str = ""
    google_calendar_client_secret: str = ""

    # Public URLs — used to build redirect_uri for the OAuth callback and to
    # bounce the user back to the frontend after the consent dance.
    backend_base_url: str = "http://localhost:8000"
    frontend_base_url: str = "http://localhost:8080"

    # Server
    port: int = 8000
    env: str = "development"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
