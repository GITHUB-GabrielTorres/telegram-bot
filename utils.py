from datetime import datetime, timedelta, timezone


LOCAL_TZ = timezone(timedelta(hours=-3))


def now_local() -> datetime:
    return datetime.now(LOCAL_TZ)


def format_dt(value: datetime) -> str:
    return value.astimezone(LOCAL_TZ).strftime("%Y-%m-%d %H:%M")

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