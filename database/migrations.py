from datetime import datetime


def migration_done(client, name):
    response = (
        client.table("migracoes_sistema")
        .select("id,status")
        .eq("nome_migracao", name)
        .eq("status", "concluida")
        .limit(1)
        .execute()
    )
    return bool(getattr(response, "data", None))


def register_migration(client, name, status, imported=0, ignored=0, errors=""):
    payload = {
        "id": name,
        "nome_migracao": name,
        "status": status,
        "data_execucao": datetime.now().isoformat(),
        "registros_importados": int(imported or 0),
        "registros_ignorados": int(ignored or 0),
        "erros": str(errors or "")[:2000],
    }
    client.table("migracoes_sistema").upsert(payload, on_conflict="id").execute()
    return payload
