import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

from config import TELEGRAM_TOKEN, WEBHOOK_SECRET
from db import init_db
from handlers.commands import start, register, help_command, setbal_callback, definirsaldo, ganhei, undo_ganhei, definirrecompensa, saldo, li, cursohoras, podcasthoras, versiculos, treinodourado, desfazer, gasto, historico, verid, editar, recompensa_pontual

application = Application.builder().token(TELEGRAM_TOKEN).updater(None).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("register", register))
application.add_handler(CommandHandler("ajuda", help_command))
application.add_handler(CommandHandler(["definirsaldo", "ds"], definirsaldo))
application.add_handler(CommandHandler(["ganhei", "g"], ganhei))
application.add_handler(CommandHandler(["xganhei", "xg"], undo_ganhei))
application.add_handler(CommandHandler(["definirrecompensa", "dr"], definirrecompensa))
application.add_handler(CommandHandler(["saldo", "s"], saldo))
application.add_handler(CommandHandler("li", li))
application.add_handler(CommandHandler(["cursohoras", "ch"], cursohoras))
application.add_handler(CommandHandler(["podcasthoras", "ph"], podcasthoras))
application.add_handler(CommandHandler(["versiculos", "v"], versiculos))
application.add_handler(CommandHandler(["treinodourado", "td"], treinodourado))
application.add_handler(CommandHandler(["desfazer", "dz", "desfaz"], desfazer))
application.add_handler(CommandHandler("gasto", gasto))
application.add_handler(CommandHandler(["recompensa_pontual", "rp"], recompensa_pontual))
application.add_handler(CommandHandler(["historico", "h"], historico))
application.add_handler(CommandHandler(["verid", "vid"], verid))
application.add_handler(CommandHandler(["editar", "ed"], editar))
application.add_handler(CallbackQueryHandler(setbal_callback, pattern="^setbal:"))


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    async with application:
        yield


app = FastAPI(lifespan=lifespan)


@app.post("/webhook")
async def webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
):
    if not x_telegram_bot_api_secret_token or not secrets.compare_digest(
        x_telegram_bot_api_secret_token.encode(), WEBHOOK_SECRET.encode()
    ):
        raise HTTPException(status_code=403, detail="Forbidden")

    update = Update.de_json(await request.json(), application.bot)
    await application.process_update(update)
    return {"ok": True}