import os
from dataclasses import dataclass


def _parse_origins(value: str) -> tuple[str, ...]:
    origins = tuple(origin.strip().rstrip("/") for origin in value.split(",") if origin.strip())
    if "*" in origins:
        raise ValueError(
            "CORS_ORIGINS must list explicit origins; wildcard origins are not allowed."
        )
    return origins


@dataclass(frozen=True)
class Settings:
    app_env: str = "development"
    data_mode: str = "illustrative"
    cors_origins: tuple[str, ...] = ("http://localhost:5173",)
    api_prefix: str = "/api/v1"
    explanation_provider: str = "template"

    @classmethod
    def from_environment(cls) -> "Settings":
        app_env = os.getenv("APP_ENV", "development").strip() or "development"
        data_mode = os.getenv("DATA_MODE", "illustrative").strip().lower()
        api_prefix = os.getenv("API_PREFIX", "/api/v1").strip().rstrip("/")
        explanation_provider = os.getenv("EXPLANATION_PROVIDER", "template").strip().lower()
        if data_mode != "illustrative":
            raise ValueError(
                "Only DATA_MODE=illustrative is supported; no live provider is configured."
            )
        if not api_prefix.startswith("/") or api_prefix == "/":
            raise ValueError("API_PREFIX must be a non-root absolute path.")
        if explanation_provider != "template":
            raise ValueError("Only EXPLANATION_PROVIDER=template is supported in this build.")
        return cls(
            app_env=app_env,
            data_mode=data_mode,
            cors_origins=_parse_origins(os.getenv("CORS_ORIGINS", "http://localhost:5173")),
            api_prefix=api_prefix,
            explanation_provider=explanation_provider,
        )
