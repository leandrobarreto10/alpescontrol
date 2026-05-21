def required(value):
    return bool(str(value or "").strip())


def normalize_status(value, default="Ativo"):
    text = str(value or "").strip()
    return text or default
