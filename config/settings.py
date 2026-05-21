import os


def get_secret(name, default=""):
    return os.environ.get(name, default)


def environment():
    value = (
        os.environ.get("ENVIRONMENT")
        or os.environ.get("ALPES_ENVIRONMENT")
        or "development"
    )
    value = str(value).strip().lower()
    if value in {"production", "prod", "producao", "produção"}:
        return "production"
    return "development"


def is_production():
    return environment() == "production"


def required_production_settings():
    return [
        "SUPABASE_URL",
        "SUPABASE_SERVICE_ROLE_KEY",
        "SUPABASE_BUCKET",
    ]
