import os
import sys


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

    if os.environ.get("ALPES_ADMIN_PASSWORD") == "123":
        print("ALPES_ADMIN_PASSWORD nao pode ser 123 em production.")
        return 1

    print("Variaveis de production validadas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
