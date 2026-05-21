import os


def safe_filename(name):
    base = os.path.basename(str(name or "arquivo"))
    return "".join(char for char in base if char.isalnum() or char in "._- ").strip() or "arquivo"
