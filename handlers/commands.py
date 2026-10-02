from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from db import (
    create_movement,
    delete_movement,
    find_ganhei_id,
    get_balances,
    get_ganhei_days,
    get_movement,
    get_reference_value,
    get_user_balance,
    get_user_name,
    get_users,
    list_movements,
    list_reference_values,
    register_user,
    set_reference_value,
    update_movement_description,
)
from utils import format_balances_block, format_brl, format_dt, now_local


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
        "🏋️ <code>/treinodourado</code> (<code>/td</code>) <i>qtd [valor] [descrição]</i> — treino dourado\n"
        "🎁 <code>/recompensa_pontual</code> (<code>/rp</code>) <i>valor descrição</i> — recompensa avulsa\n\n"

        "🔍 <b>Consulta</b>\n"
        "<code>/historico</code> (<code>/h</code>) [n | m [n] | g [dias]] — lista movimentações ou dias ganhos/perdidos\n"
        "<code>/verid</code> (<code>/vid</code>) <i>id</i> — mostra todos os detalhes de uma movimentação\n\n"

        "⚙️ <b>Configuração</b>\n"
        "<code>/definirrecompensa</code> (<code>/dr</code>) [chave valor] — lista ou edita os valores\n"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Uso: /register <nome>")
        return

    name = context.args[0]
    user_id = update.effective_user.id

    register_user(user_id, name)

    await update.message.reply_text(f"Registrado como {name}!")


async def definirsaldo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    person = get_user_name(user_id)

    if person is None:
        await update.message.reply_text("Você ainda não está registrado. Use /register <nome> primeiro.")
        return

    if not context.args:
        await update.message.reply_text("Uso: /definirsaldo <valor>")
        return

    try:
        target = float(context.args[0])
    except ValueError:
        await update.message.reply_text("Valor inválido.")
        return

    current = get_user_balance(user_id)

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
    person = get_user_name(user_id)

    current = get_user_balance(user_id)
    diff = target - current

    create_movement(user_id, diff, "Ajuste de saldo", now_local())

    await query.edit_message_text(f"Saldo de {person} ajustado para {format_brl(target)}.")


async def ganhei(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    person = get_user_name(user_id)

    if person is None:
        await update.message.reply_text("Você ainda não está registrado. Use /register <nome> primeiro.")
        return

    today = now_local().date()

    if context.args and context.args[0].lower() == "ontem":
        target_date = today - timedelta(days=1)
    else:
        target_date = today

    target_date_iso = target_date.isoformat()
    is_yesterday = target_date != today
    label = "ontem" if is_yesterday else "hoje"

    if find_ganhei_id(user_id, target_date_iso) is not None:
        await update.message.reply_text(f"{person}, você já usou o /ganhei {label}.")
        return

    amount = get_reference_value("day")
    movement_datetime = datetime.combine(target_date, now_local().timetz())

    create_movement(user_id, amount, "ganhei", movement_datetime)

    balances = get_balances()
    balances_text = format_balances_block(balances, person)

    await update.message.reply_text(
        f"{balances_text}\n\n{person} completou o dia de {label} e ganhou {format_brl(amount)}.",
        parse_mode="HTML",
    )


async def undo_ganhei(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    person = get_user_name(user_id)

    if person is None:
        await update.message.reply_text("Você ainda não está registrado. Use /register <nome> primeiro.")
        return

    today = now_local().date()

    if context.args and context.args[0].lower() == "ontem":
        target_date = today - timedelta(days=1)
    else:
        target_date = today

    target_date_iso = target_date.isoformat()
    is_yesterday = target_date != today
    label = "ontem" if is_yesterday else "hoje"

    movement_id = find_ganhei_id(user_id, target_date_iso)

    if movement_id is None:
        await update.message.reply_text(f"{person}, você não usou o /ganhei {label}, nada pra desfazer.")
        return

    delete_movement(movement_id)

    balances = get_balances()
    balances_text = format_balances_block(balances, person)

    await update.message.reply_text(
        f"{balances_text}\n\n{person} desfez o /ganhei de {label}.",
        parse_mode="HTML",
    )


async def definirrecompensa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    items = list_reference_values()

    if not context.args:
        lines = [f"{key} = {value}" for key, value in items]
        await update.message.reply_text(
            "Itens disponíveis:\n\n" + "\n".join(lines) + "\n\nUso: /dr <chave> <novo valor>"
        )
        return

    if len(context.args) != 2:
        await update.message.reply_text("Uso: /dr <chave> <novo valor>")
        return

    key = context.args[0]

    try:
        value = float(context.args[1])
    except ValueError:
        await update.message.reply_text("Valor inválido.")
        return

    if key not in dict(items):
        await update.message.reply_text(f"Nenhum item com a chave '{key}'.")
        return

    set_reference_value(key, value)

    await update.message.reply_text(f"{key} atualizado para {value}.")


async def saldo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    balances = get_balances()

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
    person = get_user_name(user_id)

    if person is None:
        await update.message.reply_text("Você ainda não está registrado. Use /register <nome> primeiro.")
        return

    if not context.args:
        await update.message.reply_text(f"Uso: /{usage_label} <quantidade> [valor_override] <descrição>")
        return

    try:
        quantity = int(context.args[0])
    except ValueError:
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
        await update.message.reply_text(
            f"Descrição é obrigatória. Uso: /{usage_label} <quantidade> [valor_override] <descrição>"
        )
        return

    amount = quantity * unit_value
    full_description = f"{description}: {description_extra}"

    balances_before = get_balances()
    movement_id = create_movement(user_id, amount, full_description, now_local())
    balances_after = get_balances()

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

    movement = get_movement(movement_id)

    if movement is None:
        await update.message.reply_text(f"Nenhuma movimentação com id {movement_id}.")
        return

    owner_name = get_user_name(movement["user_id"]) or str(movement["user_id"])

    balances_before = get_balances()
    delete_movement(movement_id)
    balances_after = get_balances()

    text = (
        f"<b>Movimentação #{movement_id} desfeita</b> "
        f"({movement['description']}, {format_brl(movement['amount'])})\n\n"
        f"{format_balances_block(balances_before, title='Saldo antes')}\n\n"
        f"{format_balances_block(balances_after, owner_name, title='Saldo depois')}"
    )

    await update.message.reply_text(text, parse_mode="HTML")


async def gasto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    person = get_user_name(user_id)

    if person is None:
        await update.message.reply_text("Você ainda não está registrado. Use /register <nome> primeiro.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Uso: /gasto <valor> <descrição>")
        return

    try:
        value = float(context.args[0])
    except ValueError:
        await update.message.reply_text("Valor inválido.")
        return

    description = " ".join(context.args[1:])
    amount = -abs(value)

    balances_before = get_balances()
    movement_id = create_movement(user_id, amount, description, now_local())
    balances_after = get_balances()

    text = (
        f"💸 <b>Movimentação #{movement_id}</b> ({description})\n\n"
        f"{format_balances_block(balances_before, title='Saldo antes')}\n\n"
        f"{format_balances_block(balances_after, person, title='Saldo depois')}"
    )

    await update.message.reply_text(text, parse_mode="HTML")


async def recompensa_pontual(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    person = get_user_name(user_id)

    if person is None:
        await update.message.reply_text("Você ainda não está registrado. Use /register <nome> primeiro.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Uso: /recompensa_pontual <valor> <descrição>")
        return

    try:
        value = float(context.args[0].replace(",", "."))
    except ValueError:
        await update.message.reply_text("Valor inválido.")
        return

    amount = round(abs(value), 2)
    description = f"recompensa pontual: {' '.join(context.args[1:])}"

    balances_before = get_balances()
    movement_id = create_movement(user_id, amount, description, now_local())
    balances_after = get_balances()

    text = (
        f"🎁 <b>Movimentação #{movement_id}</b> ({description})\n\n"
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

    users = get_users()
    ganhei_days = {user_id: get_ganhei_days(user_id) for user_id in users}

    today = now_local().date()
    lines = ["⭐️ <b>Dias ganhos/perdidos</b>"]

    for i in range(days - 1, -1, -1):
        day = today - timedelta(days=i)
        day_iso = day.isoformat()
        date_str = day.strftime("%d/%m")

        status_parts = [
            f"{name} {'✅' if day_iso in ganhei_days[user_id] else '❌'}"
            for user_id, name in users.items()
        ]

        lines.append(f"{date_str} — " + " | ".join(status_parts))

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

    movements = list_movements(limit, exclude_ganhei)

    if not movements:
        await update.message.reply_text("Nenhuma movimentação registrada ainda.")
        return

    movements.reverse()
    names = get_users()

    title = "📜 <b>Movimentações</b>" if exclude_ganhei else "📜 <b>Últimas movimentações</b>"
    lines = [title]
    for movement in movements:
        person = names.get(movement["user_id"], str(movement["user_id"]))
        amount = movement["amount"]
        signal = "+" if amount >= 0 else ""
        lines.append(
            f"\n#{movement['id']} — {person} — {signal}{format_brl(amount)}\n"
            f"{movement['description']}\n<i>{format_dt(movement['movement_date'])}</i>"
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

    movement = get_movement(movement_id)

    if movement is None:
        await update.message.reply_text(f"Nenhuma movimentação com id {movement_id}.")
        return

    person = get_user_name(movement["user_id"]) or str(movement["user_id"])
    amount = movement["amount"]
    signal = "+" if amount >= 0 else ""

    text = (
        f"🔍 <b>Movimentação #{movement_id}</b>\n\n"
        f"<b>Pessoa:</b> {person}\n"
        f"<b>Valor:</b> {signal}{format_brl(amount)}\n"
        f"<b>Descrição:</b> {movement['description']}\n"
        f"<b>Data do fato:</b> {format_dt(movement['movement_date'])}\n"
        f"<b>Registrado em:</b> {format_dt(movement['created_at'])}"
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

    movement = get_movement(movement_id)

    if movement is None:
        await update.message.reply_text(f"Nenhuma movimentação com id {movement_id}.")
        return

    old_description = movement["description"]

    if old_description == "ganhei":
        await update.message.reply_text("Movimentações de /ganhei não podem ter a descrição editada.")
        return

    update_movement_description(movement_id, new_description)

    await update.message.reply_text(
        f"<b>Movimentação #{movement_id}</b> atualizada.\n"
        f"<i>Antes:</i> {old_description}\n"
        f"<i>Agora:</i> {new_description}",
        parse_mode="HTML",
    )