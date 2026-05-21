import os
import sys
from urllib.parse import urlparse


REQUIRED_PRODUCTION_VARS = [
    "ENVIRONMENT",
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
    "SUPABASE_BUCKET",
    "ALPES_ADMIN_USER",
    "ALPES_ADMIN_PASSWORD",
]


def main():
    environment = os.environ.get("ENVIRONMENT", "").strip().lower()
    if environment not in {"production", "prod", "producao"}:
        print("Ambiente nao esta como production; validacao critica ignorada.")
        return 0

    missing = [name for name in REQUIRED_PRODUCTION_VARS if not os.environ.get(name)]
    if missing:
        print("Variaveis obrigatorias ausentes em production:")
        for name in missing:
            print(f"- {name}")
        return 1

    supabase_url = os.environ.get("SUPABASE_URL", "").strip()
    parsed_url = urlparse(supabase_url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        print("SUPABASE_URL invalida. Use o formato https://SEU-PROJETO.supabase.co")
        return 1

    if not os.environ.get("SUPABASE_BUCKET", "").strip():
        print("SUPABASE_BUCKET nao pode ficar vazio.")
        return 1

    admin_password = os.environ.get("ALPES_ADMIN_PASSWORD", "")
    if admin_password == "123" or len(admin_password) < 8:
        print("ALPES_ADMIN_PASSWORD deve ser forte e nao pode ser 123.")
        return 1

    print("Variaveis de production validadas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
