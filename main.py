from telegram.ext import Application, CommandHandler, CallbackQueryHandler

from config import TELEGRAM_TOKEN
from db import init_db
from handlers.commands import start, register, help_command, setbal_callback, definirsaldo, ganhei, undo_ganhei, definirrecompensa, saldo, li, cursohoras, podcasthoras, versiculos, treinodourado, desfazer, gasto, historico, verid, editar


def main() -> None:
    init_db()

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("register", register))
    app.add_handler(CommandHandler("ajuda", help_command))
    app.add_handler(CommandHandler(["definirsaldo", "ds"], definirsaldo))
    app.add_handler(CommandHandler(["ganhei", "g"], ganhei))
    app.add_handler(CommandHandler(["xganhei", "xg"], undo_ganhei))
    app.add_handler(CommandHandler(["definirrecompensa", "dr"], definirrecompensa))
    app.add_handler(CommandHandler(["saldo", "s"], saldo))
    app.add_handler(CommandHandler("li", li))
    app.add_handler(CommandHandler(["cursohoras", "ch"], cursohoras))
    app.add_handler(CommandHandler(["podcasthoras", "ph"], podcasthoras))
    app.add_handler(CommandHandler(["versiculos", "v"], versiculos))
    app.add_handler(CommandHandler(["treinodourado", "td"], treinodourado))
    app.add_handler(CommandHandler(["desfazer", "dz", "desfaz"], desfazer))
    app.add_handler(CommandHandler("gasto", gasto))
    app.add_handler(CommandHandler(["historico", "h"], historico))
    app.add_handler(CommandHandler(["verid", "vid"], verid))
    app.add_handler(CommandHandler(["editar", "ed"], editar))
    app.add_handler(CallbackQueryHandler(setbal_callback, pattern="^setbal:"))
    app.run_polling()


if __name__ == "__main__":
    main()