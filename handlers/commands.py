from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup

from telegram.ext import ContextTypes
from db import get_connection
from utils import format_brl, format_balances_block, get_reference_value
from db import get_balances


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Bot no ar!!!")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "🤖 <b>Comandos disponíveis</b>\n\n"

        "👤 <b>Conta</b>\n"
        "<code>/start</code> — verifica se o bot está no ar\n"
        "<code>/register</code> <i>nome</i> — vincula você a um nome\n"
        "<code>/ajuda</code> — mostra essa mensagem\n\n"

        "💰 <b>Saldo</b>\n"
        "<code>/saldo</code> (<code>/s</code>) — mostra o saldo de todos\n"
        "<code>/gasto</code> <i>valor descrição</i> — registra um gasto\n"
        "<code>/definirsaldo</code> (<code>/ds</code>) <i>valor</i> — ajusta seu saldo, com confirmação\n"
        "<code>/desfazer</code> (<code>/dz</code>) <i>id</i> — desfaz uma movimentação pelo id\n"
        "<code>/editar</code> (<code>/ed</code>) <i>id nova_descrição</i> — edita a descrição de uma movimentação (exceto /ganhei)\n\n"

        "⭐️ <b>Recompensa diária</b>\n"
        "<code>/ganhei</code> (<code>/g</code>) [ontem] — registra o ganho do dia\n"
        "<code>/xg</code> (<code>/xganhei</code>) [ontem] — desfaz o /ganhei\n\n"

        "🏆 <b>Recompensas</b>\n"
        "📖 <code>/li</code> <i>qtd [valor] [descrição]</i> — páginas lidas\n"
        "🎓 <code>/cursohoras</code> (<code>/ch</code>) <i>qtd [valor] [descrição]</i> — horas de curso\n"
        "🎧 <code>/podcasthoras</code> (<code>/ph</code>) <i>qtd [valor] [descrição]</i> — horas de podcast\n"
        "📜 <code>/versiculos</code> (<code>/v</code>) <i>qtd [valor] [descrição]</i> — versículos\n"
        "🏋️ <code>/treinodourado</code> (<code>/td</code>) <i>qtd [valor] [descrição]</i> — treino dourado\n\n"

        "🔍 <b>Consulta</b>\n"
        "<code>/historico</code> (<code>/h</code>) [n | m [n] | g [dias]] — lista movimentações ou dias ganhos/perdidos\n"
        "<code>/verid</code> (<code>/vid</code>) <i>id</i> — mostra todos os detalhes de uma movimentação\n\n"

        "⚙️ <b>Configuração</b>\n"
        "<code>/definirrecompensa</code> (<code>/dr</code>) [id valor] — lista ou edita os valores\n"
    )
    await update.message.reply_text(text, parse_mode="HTML")

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Uso: /register <nome>")
        return

    name = context.args[0]
    user_id = update.effective_user.id

    conn = get_connection()
    conn.execute(
        """
        INSERT INTO users (user_id, name) VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET name = excluded.name
        """,
        (user_id, name),
    )
    conn.commit()
    conn.close()

    await update.message.reply_text(f"Registrado como {name}!")


async def definirsaldo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    conn = get_connection()
    row = conn.execute("SELECT name FROM users WHERE user_id = ?", (user_id,)).fetchone()

    if row is None:
        await update.message.reply_text("Você ainda não está registrado. Use /register <nome> primeiro.")
        conn.close()
        return

    person = row[0]

    if not context.args:
        await update.message.reply_text("Uso: /definirsaldo <valor>")
        conn.close()
        return

    try:
        target = float(context.args[0])
    except ValueError:
        await update.message.reply_text("Valor inválido.")
        conn.close()
        return

    current = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM movements WHERE person = ?", (person,)
    ).fetchone()[0]
    conn.close()

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("Confirmar", callback_data=f"setbal:confirm:{target}"),
        InlineKeyboardButton("Cancelar", callback_data="setbal:cancel"),
    ]])

    await update.message.reply_text(
        f"Saldo atual: {format_brl(current)}\nNovo saldo: {format_brl(target)}\nConfirma?",
        reply_markup=keyboard,
    )


async def setbal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    parts = query.data.split(":")

    if parts[1] == "cancel":
        await query.edit_message_text("Cancelado.")
        return

    target = float(parts[2])
    user_id = update.effective_user.id

    conn = get_connection()
    person = conn.execute("SELECT name FROM users WHERE user_id = ?", (user_id,)).fetchone()[0]
    current = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM movements WHERE person = ?", (person,)
    ).fetchone()[0]

    diff = target - current

    conn.execute(
        "INSERT INTO movements (person, amount, description, movement_date) VALUES (?, ?, ?, ?)",
        (person, diff, "Ajuste de saldo", datetime.now()),
    )
    conn.commit()
    conn.close()

    await query.edit_message_text(f"Saldo de {person} ajustado para {format_brl(target)}.")


async def ganhei(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    conn = get_connection()
    row = conn.execute("SELECT name FROM users WHERE user_id = ?", (user_id,)).fetchone()

    if row is None:
        await update.message.reply_text("Você ainda não está registrado. Use /register <nome> primeiro.")
        conn.close()
        return

    person = row[0]

    if context.args and context.args[0].lower() == "ontem":
        target_date = (datetime.now() - timedelta(days=1)).date()
    else:
        target_date = datetime.now().date()

    target_date_iso = target_date.isoformat()
    is_yesterday = target_date_iso != datetime.now().date().isoformat()

    already_used = conn.execute(
        "SELECT COUNT(*) FROM movements WHERE person = ? AND description = ? AND date(movement_date) = ?",
        (person, "ganhei", target_date_iso),
    ).fetchone()[0]

    if already_used:
        label = "ontem" if is_yesterday else "hoje"
        await update.message.reply_text(f"{person}, você já usou o /ganhei {label}.")
        conn.close()
        return

    amount = get_reference_value("day")
    movement_datetime = datetime.combine(target_date, datetime.now().time())

    conn.execute(
        "INSERT INTO movements (person, amount, description, movement_date) VALUES (?, ?, ?, ?)",
        (person, amount, "ganhei", movement_datetime),
    )
    conn.commit()

    balances = get_balances(conn)
    conn.close()

    balances_text = format_balances_block(balances, person)
    label = "ontem" if is_yesterday else "hoje"

    await update.message.reply_text(
        f"{balances_text}\n\n{person} completou o dia de {label} e ganhou {format_brl(amount)}.",
        parse_mode="HTML",
    )


async def undo_ganhei(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    conn = get_connection()
    row = conn.execute("SELECT name FROM users WHERE user_id = ?", (user_id,)).fetchone()

    if row is None:
        await update.message.reply_text("Você ainda não está registrado. Use /register <nome> primeiro.")
        conn.close()
        return

    person = row[0]

    if context.args and context.args[0].lower() == "ontem":
        target_date = (datetime.now() - timedelta(days=1)).date()
    else:
        target_date = datetime.now().date()

    target_date_iso = target_date.isoformat()
    is_yesterday = target_date_iso != datetime.now().date().isoformat()
    label = "ontem" if is_yesterday else "hoje"

    movement = conn.execute(
        "SELECT id FROM movements WHERE person = ? AND description = ? AND date(movement_date) = ? ORDER BY id DESC LIMIT 1",
        (person, "ganhei", target_date_iso),
    ).fetchone()

    if movement is None:
        await update.message.reply_text(f"{person}, você não usou o /ganhei {label}, nada pra desfazer.")
        conn.close()
        return

    conn.execute("DELETE FROM movements WHERE id = ?", (movement[0],))
    conn.commit()

    balances = get_balances(conn)
    conn.close()

    balances_text = format_balances_block(balances, person)

    await update.message.reply_text(
        f"{balances_text}\n\n{person} desfez o /ganhei de {label}.",
        parse_mode="HTML",
    )


async def definirrecompensa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    conn = get_connection()

    if not context.args:
        rows = conn.execute(
            "SELECT rowid, key, value FROM reference_values ORDER BY rowid"
        ).fetchall()
        conn.close()

        lines = [f"{rowid}) {key} = {value}" for rowid, key, value in rows]
        await update.message.reply_text("Itens disponíveis:\n\n" + "\n".join(lines))
        return

    if len(context.args) != 2:
        conn.close()
        await update.message.reply_text("Uso: /dr <id> <novo valor>")
        return

    try:
        item_id = int(context.args[0])
        value = float(context.args[1])
    except ValueError:
        conn.close()
        await update.message.reply_text("Id ou valor inválido.")
        return

    row = conn.execute(
        "SELECT key FROM reference_values WHERE rowid = ?", (item_id,)
    ).fetchone()

    if row is None:
        conn.close()
        await update.message.reply_text(f"Nenhum item com id {item_id}.")
        return

    key = row[0]

    conn.execute("UPDATE reference_values SET value = ? WHERE rowid = ?", (value, item_id))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"{key} atualizado para {value}.")


async def saldo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    conn = get_connection()
    balances = get_balances(conn)
    conn.close()

    lines = ["<b>Saldos atuais</b>"]
    lines += [f"{name}: {format_brl(balance)}" for name, balance in balances]

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def register_reward_movement(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    reference_key: str,
    description: str,
    usage_label: str,
) -> None:
    user_id = update.effective_user.id
    conn = get_connection()
    row = conn.execute("SELECT name FROM users WHERE user_id = ?", (user_id,)).fetchone()

    if row is None:
        conn.close()
        await update.message.reply_text("Você ainda não está registrado. Use /register <nome> primeiro.")
        return

    person = row[0]

    if not context.args:
        conn.close()
        await update.message.reply_text(f"Uso: /{usage_label} <quantidade> [valor_override] <descrição>")
        return

    try:
        quantity = int(context.args[0])
    except ValueError:
        conn.close()
        await update.message.reply_text("Quantidade inválida.")
        return

    remaining = context.args[1:]

    if remaining:
        try:
            unit_value = float(remaining[0])
            description_extra = " ".join(remaining[1:])
        except ValueError:
            unit_value = get_reference_value(reference_key)
            description_extra = " ".join(remaining)
    else:
        unit_value = get_reference_value(reference_key)
        description_extra = ""

    if not description_extra:
        conn.close()
        await update.message.reply_text(
            f"Descrição é obrigatória. Uso: /{usage_label} <quantidade> [valor_override] <descrição>"
        )
        return

    amount = quantity * unit_value
    full_description = f"{description}: {description_extra}"

    balances_before = get_balances(conn)

    conn.execute(
        "INSERT INTO movements (person, amount, description, movement_date) VALUES (?, ?, ?, ?)",
        (person, amount, full_description, datetime.now()),
    )
    conn.commit()
    movement_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    balances_after = get_balances(conn)
    conn.close()

    text = (
        f"<b>Movimentação #{movement_id}</b> ({full_description})\n\n"
        f"{format_balances_block(balances_before, title='Saldo antes')}\n\n"
        f"{format_balances_block(balances_after, person, title='Saldo depois')}"
    )

    await update.message.reply_text(text, parse_mode="HTML")


async def li(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await register_reward_movement(update, context, "pages", "páginas lidas", "li")


async def cursohoras(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await register_reward_movement(update, context, "course_hours", "horas de curso", "cursohoras")


async def podcasthoras(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await register_reward_movement(update, context, "podcast_hours", "horas de podcast", "podcasthoras")


async def versiculos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await register_reward_movement(update, context, "bible_verses", "versículos", "versiculos")


async def treinodourado(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await register_reward_movement(update, context, "golden_training", "treino dourado", "treinodourado")


async def desfazer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Uso: /desfazer <id>")
        return

    try:
        movement_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Id inválido.")
        return

    conn = get_connection()
    movement = conn.execute(
        "SELECT person, amount, description FROM movements WHERE id = ?", (movement_id,)
    ).fetchone()

    if movement is None:
        conn.close()
        await update.message.reply_text(f"Nenhuma movimentação com id {movement_id}.")
        return

    person, amount, description = movement

    balances_before = get_balances(conn)
    conn.execute("DELETE FROM movements WHERE id = ?", (movement_id,))
    conn.commit()
    balances_after = get_balances(conn)
    conn.close()

    text = (
        f"<b>Movimentação #{movement_id} desfeita</b> ({description}, {format_brl(amount)})\n\n"
        f"{format_balances_block(balances_before, title='Saldo antes')}\n\n"
        f"{format_balances_block(balances_after, person, title='Saldo depois')}"
    )

    await update.message.reply_text(text, parse_mode="HTML")


async def gasto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    conn = get_connection()
    row = conn.execute("SELECT name FROM users WHERE user_id = ?", (user_id,)).fetchone()

    if row is None:
        conn.close()
        await update.message.reply_text("Você ainda não está registrado. Use /register <nome> primeiro.")
        return

    person = row[0]

    if len(context.args) < 2:
        conn.close()
        await update.message.reply_text("Uso: /gasto <valor> <descrição>")
        return

    try:
        value = float(context.args[0])
    except ValueError:
        conn.close()
        await update.message.reply_text("Valor inválido.")
        return

    description = " ".join(context.args[1:])
    amount = -abs(value)

    balances_before = get_balances(conn)

    conn.execute(
        "INSERT INTO movements (person, amount, description, movement_date) VALUES (?, ?, ?, ?)",
        (person, amount, description, datetime.now()),
    )
    conn.commit()
    movement_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    balances_after = get_balances(conn)
    conn.close()

    text = (
        f"💸 <b>Movimentação #{movement_id}</b> ({description})\n\n"
        f"{format_balances_block(balances_before, title='Saldo antes')}\n\n"
        f"{format_balances_block(balances_after, person, title='Saldo depois')}"
    )

    await update.message.reply_text(text, parse_mode="HTML")


async def historico_ganhei(update: Update, extra_args: list[str]) -> None:
    days = 10
    if extra_args:
        try:
            days = int(extra_args[0])
        except ValueError:
            await update.message.reply_text("Quantidade de dias inválida.")
            return

    conn = get_connection()
    people = [row[0] for row in conn.execute("SELECT name FROM users").fetchall()]

    today = datetime.now().date()
    lines = ["⭐️ <b>Dias ganhos/perdidos</b>"]

    for i in range(days - 1, -1, -1):
        day = today - timedelta(days=i)
        day_iso = day.isoformat()
        date_str = day.strftime("%d/%m")

        status_parts = []
        for person in people:
            won = conn.execute(
                "SELECT COUNT(*) FROM movements WHERE person = ? AND description = ? AND date(movement_date) = ?",
                (person, "ganhei", day_iso),
            ).fetchone()[0]
            status_parts.append(f"{person} {'✅' if won else '❌'}")

        lines.append(f"{date_str} — " + " | ".join(status_parts))

    conn.close()
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def historico(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args

    if args and args[0].lower() == "g":
        await historico_ganhei(update, args[1:])
        return

    exclude_ganhei = bool(args) and args[0].lower() == "m"
    limit_args = args[1:] if exclude_ganhei else args

    limit = 10
    if limit_args:
        try:
            limit = int(limit_args[0])
        except ValueError:
            await update.message.reply_text("Quantidade inválida.")
            return

    conn = get_connection()
    if exclude_ganhei:
        rows = conn.execute(
            """
            SELECT id, person, amount, description, movement_date
            FROM movements
            WHERE description != ?
            ORDER BY id DESC
            LIMIT ?
            """,
            ("ganhei", limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT id, person, amount, description, movement_date
            FROM movements
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("Nenhuma movimentação registrada ainda.")
        return

    rows.reverse()

    title = "📜 <b>Movimentações</b>" if exclude_ganhei else "📜 <b>Últimas movimentações</b>"
    lines = [title]
    for movement_id, person, amount, description, movement_date in rows:
        date_str = str(movement_date)[:16]
        signal = "+" if amount >= 0 else ""
        lines.append(
            f"\n#{movement_id} — {person} — {signal}{format_brl(amount)}\n"
            f"{description}\n<i>{date_str}</i>"
        )

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def verid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Uso: /verid <id>")
        return

    try:
        movement_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Id inválido.")
        return

    conn = get_connection()
    row = conn.execute(
        "SELECT id, person, amount, description, movement_date, created_at FROM movements WHERE id = ?",
        (movement_id,),
    ).fetchone()
    conn.close()

    if row is None:
        await update.message.reply_text(f"Nenhuma movimentação com id {movement_id}.")
        return

    movement_id, person, amount, description, movement_date, created_at = row
    signal = "+" if amount >= 0 else ""

    text = (
        f"🔍 <b>Movimentação #{movement_id}</b>\n\n"
        f"<b>Pessoa:</b> {person}\n"
        f"<b>Valor:</b> {signal}{format_brl(amount)}\n"
        f"<b>Descrição:</b> {description}\n"
        f"<b>Data do fato:</b> {str(movement_date)[:16]}\n"
        f"<b>Registrado em:</b> {str(created_at)[:16]}"
    )

    await update.message.reply_text(text, parse_mode="HTML")


async def editar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) < 2:
        await update.message.reply_text("Uso: /editar <id> <nova descrição>")
        return

    try:
        movement_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Id inválido.")
        return

    new_description = " ".join(context.args[1:])

    conn = get_connection()
    row = conn.execute(
        "SELECT description FROM movements WHERE id = ?", (movement_id,)
    ).fetchone()

    if row is None:
        conn.close()
        await update.message.reply_text(f"Nenhuma movimentação com id {movement_id}.")
        return

    old_description = row[0]

    if old_description == "ganhei":
        conn.close()
        await update.message.reply_text("Movimentações de /ganhei não podem ter a descrição editada.")
        return

    conn.execute(
        "UPDATE movements SET description = ? WHERE id = ?", (new_description, movement_id)
    )
    conn.commit()
    conn.close()

    await update.message.reply_text(
        f"<b>Movimentação #{movement_id}</b> atualizada.\n"
        f"<i>Antes:</i> {old_description}\n"
        f"<i>Agora:</i> {new_description}",
        parse_mode="HTML",
    )