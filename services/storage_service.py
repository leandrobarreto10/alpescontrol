import mimetypes
import os


def upload_file(client, bucket_name, path, content, content_type=None):
    bucket = client.storage.from_(bucket_name)
    options = {
        "content-type": content_type or mimetypes.guess_type(str(path))[0] or "application/octet-stream",
        "x-upsert": "true",
    }
    try:
        bucket.upload(path, content, file_options=options)
    except Exception:
        bucket.update(path, content, file_options=options)
    return path


def upload_local_file(client, bucket_name, local_path, remote_path):
    with open(local_path, "rb") as file:
        return upload_file(client, bucket_name, remote_path, file.read())


def signed_url(client, bucket_name, path, expires_in=3600):
    response = client.storage.from_(bucket_name).create_signed_url(path, expires_in)
    if isinstance(response, dict):
        return response.get("signedURL") or response.get("signedUrl") or response.get("signed_url") or ""
    return str(response or "")


def delete_file(client, bucket_name, path):
    client.storage.from_(bucket_name).remove([path])
    return True


def list_files(client, bucket_name, folder=""):
    return client.storage.from_(bucket_name).list(folder, {"limit": 1000, "offset": 0}) or []


def safe_name(name):
    base = os.path.basename(str(name or "arquivo"))
    return "".join(char for char in base if char.isalnum() or char in "._- ").strip() or "arquivo"
