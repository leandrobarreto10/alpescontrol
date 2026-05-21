import os

try:
    from supabase import create_client
except Exception:
    create_client = None


_client = None


def supabase_url():
    return os.environ.get("SUPABASE_URL", "")


def supabase_key():
    return (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        or os.environ.get("SUPABASE_ANON_KEY", "")
        or os.environ.get("SUPABASE_KEY", "")
    )


def supabase_configured():
    return bool(create_client and supabase_url() and supabase_key())


def get_supabase_client():
    global _client
    if _client is not None:
        return _client
    if not supabase_configured():
        return None
    _client = create_client(supabase_url(), supabase_key())
    return _client
