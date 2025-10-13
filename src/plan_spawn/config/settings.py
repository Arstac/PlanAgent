"""
Configuration and settings management.
Loads from environment variables with sensible defaults.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()


class Settings:
    """Global configuration settings."""

    # API Keys
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    BRAVE_API_KEY: str = os.getenv("BRAVE_API_KEY", "")

    # Model configuration
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    
    # Storage
    ARTIFACTS_PATH: Path = Path(os.getenv("ARTIFACTS_PATH", "./artifacts"))
    
    # Execution limits
    MAX_ITERATIONS_PER_STEP: int = int(os.getenv("MAX_ITERATIONS_PER_STEP", "15"))
    DEFAULT_TIMEOUT_S: int = int(os.getenv("DEFAULT_TIMEOUT_S", "180"))
    MAX_TOKENS_PER_CALL: int = int(os.getenv("MAX_TOKENS_PER_CALL", "4096"))
    
    # Tool limits
    MAX_WEB_FETCH_PER_STEP: int = int(os.getenv("MAX_WEB_FETCH_PER_STEP", "10"))
    MAX_SEARCH_RESULTS: int = int(os.getenv("MAX_SEARCH_RESULTS", "5"))
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    ENABLE_RICH_LOGGING: bool = os.getenv("ENABLE_RICH_LOGGING", "true").lower() == "true"
    
    @classmethod
    def validate(cls) -> bool:
        """Validate critical settings."""
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required. Set it in .env file.")

        # Create artifacts directory if it doesn't exist
        cls.ARTIFACTS_PATH.mkdir(parents=True, exist_ok=True)

        return True


# Singleton instance
settings = Settings()

# Validate on import
settings.validate()
