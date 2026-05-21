import hashlib
import json
from datetime import datetime

import pandas as pd


def clean_value(value):
    if pd.isna(value) if not isinstance(value, (list, dict, tuple)) else False:
        return None
    if hasattr(value, "isoformat") and not isinstance(value, str):
        try:
            return value.isoformat()
        except Exception:
            pass
    if isinstance(value, (int, float, str, bool, list, dict)) or value is None:
        return value
    return str(value)


def record_id(table, record, index=0, key=""):
    if key and str(record.get(key, "")).strip():
        return str(record.get(key)).strip()
    base = json.dumps(record, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(f"{table}|{index}|{base}".encode("utf-8")).hexdigest()


def fetch_dataframe(client, table, columns):
    response = client.table(table).select("*").execute()
    data = getattr(response, "data", None) or []
    df = pd.DataFrame(data)
    if df.empty:
        return pd.DataFrame(columns=columns)
    df = df.drop(columns=["id", "created_at", "updated_at"], errors="ignore")
    for column in columns:
        if column not in df.columns:
            df[column] = ""
    return df[columns]


def save_dataframe(client, table, columns, df, key=""):
    rows = []
    data = df.copy()
    for column in columns:
        if column not in data.columns:
            data[column] = ""
    for index, row in data[columns].iterrows():
        record = {column: clean_value(row.get(column, "")) for column in columns}
        record["id"] = record_id(table, record, index, key)
        rows.append(record)
    if rows:
        client.table(table).upsert(rows, on_conflict="id").execute()
    return len(rows)


def save_log(client, action, module="", detail="", record="", user="sistema", level=""):
    item = {
        "id": hashlib.sha256(f"{datetime.utcnow().isoformat()}|{action}|{record}".encode("utf-8")).hexdigest(),
        "data_hora": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "usuario": user,
        "nivel": level,
        "acao": action,
        "modulo": module,
        "registro": record,
        "detalhe": detail,
    }
    client.table("logs_sistema").insert(item).execute()
    return item["id"]


def logical_delete(client, table, record_id_value, user=""):
    payload = {"ativo": False, "usuario_alteracao": user}
    client.table(table).update(payload).eq("id", record_id_value).execute()
    return True
