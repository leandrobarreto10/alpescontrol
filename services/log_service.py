from database.repositories import save_log


def registrar_log(client, action, module="", detail="", record="", user="sistema", level=""):
    return save_log(client, action, module, detail, record, user, level)
