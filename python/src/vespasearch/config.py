from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def find_env_file() -> str:
    candidates = [
        Path.cwd() / ".env",
        Path.cwd().parent / ".env",
        Path(__file__).resolve().parents[3] / ".env",
    ]

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    return ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=find_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str

    # Airbyte / Neon schemas
    slack_schema: str = "slack"
    drive_schema: str = "google_drive"
    github_schema: str = "github"

    slack_tables: str = (
        "channel_messages,threads,channels,users,channel_members"
    )
    drive_table: str = "documents"
    github_tables: str = (
        "issues,issue_comments,pull_requests,"
        "pull_request_comments,commits,repositories"
    )

    # Vespa
    vespa_url: str = "http://localhost:8080"
    vespa_config_url: str = "http://localhost:19071"
    vespa_namespace: str = "vespasearch"
    vespa_schema: str = "enterprise"
    vespa_content_cluster: str = "content"

    # Chunking
    chunk_size: int = 1400
    chunk_overlap: int = 180

    # LLM
    llm_provider: str = "groq"
    llm_enabled: bool = True

    # Groq
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-20b"
    groq_url: str = "https://api.groq.com/openai/v1"

    # Search/API
    top_k: int = 5
    default_search_mode: str = "hybrid"

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000"

    @property
    def slack_table_list(self):
        return [
            x.strip()
            for x in self.slack_tables.split(",")
            if x.strip()
        ]

    @property
    def github_table_list(self):
        return [
            x.strip()
            for x in self.github_tables.split(",")
            if x.strip()
        ]

    @property
    def cors_origin_list(self):
        return [
            x.strip()
            for x in self.cors_origins.split(",")
            if x.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()