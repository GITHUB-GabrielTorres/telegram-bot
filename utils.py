from db import get_connection


def format_brl(value: float) -> str:
    sign = "-" if value < 0 else ""
    value = abs(value)
    formatted = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{sign}R$ {formatted}"


def format_balances_block(
    balances: list[tuple[str, float]],
    changed_person: str | None = None,
    title: str = "Saldos atuais",
) -> str:
    lines = [f"<b>{title}</b>"]
    for name, balance in balances:
        marker = " <b>(novo)</b>" if name == changed_person else ""
        lines.append(f"{name}{marker}: {format_brl(balance)}")
    return "\n".join(lines)


def get_reference_value(key: str) -> float:
    conn = get_connection()
    row = conn.execute("SELECT value FROM reference_values WHERE key = ?", (key,)).fetchone()
    conn.close()
    if row is None:
        raise ValueError(f"Valor de referência '{key}' não encontrado.")
    return row[0]

