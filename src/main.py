import asyncio, os, re, json, datetime
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import asyncpg
from dotenv import load_dotenv
import httpx
from aiohttp import web

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")
ADMINS = [int(x.strip()) for x in (os.getenv("ADMINS") or "").split(",") if x.strip().isdigit()]

if not BOT_TOKEN:
    raise RuntimeError("Faltou BOT_TOKEN (configure no Render)")
if not DATABASE_URL:
    raise RuntimeError("Faltou DATABASE_URL (configure no Render)")

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# --- Mini servidor HTTP p/ Render (healthcheck) ---
async def health(request):
    return web.Response(text="ok")

async def run_web():
    app = web.Application()
    app.router.add_get("/", health)
    port = int(os.getenv("PORT", "10000"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"HTTP healthcheck on :{port}")

# aqui vai TODO o código de banco, produtos, carrinho, PIX, admin...
# (o mesmo que já passamos antes)
# por simplicidade, deixei resumido — se quiser te mando o arquivo inteiro pronto,
# já com todos os comandos (whitelist, newproduct, menu, checkout etc.)

async def main():
    try:
        import uvloop
        uvloop.install()
    except Exception:
        pass
    await asyncio.gather(
        run_web(),             # servidor HTTP para o Render
        dp.start_polling(bot)  # bot Telegram
    )

if __name__ == "__main__":
    asyncio.run(main())

