def money(value):
    try:
        return f"R$ {float(value):,.2f}"
    except Exception:
        return "R$ 0,00"
