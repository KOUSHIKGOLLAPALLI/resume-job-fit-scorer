import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    api_key: str | None = os.getenv("GEMINI_API_KEY")

    weights: dict[str, float] = None

    def __post_init__(self):
        object.__setattr__(self, "weights", {
            "skills": 0.40,
            "experience": 0.20,
            "education": 0.15,
            "responsibilities": 0.15,
            "tools": 0.10,
        })


settings = Settings()