import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
import asyncpg
import httpx

# -------- Config --------
BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")
PUBLIC_URL = os.getenv("PUBLIC_URL")
ADMINS = [int(x.strip()) for x in (os.getenv("ADMINS") or "").split(",") if x.strip().isdigit()]
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "defaultsecret")

if not BOT_TOKEN:
    raise RuntimeError("Faltou BOT_TOKEN (configure no Render)")
if not DATABASE_URL:
    raise RuntimeError("Faltou DATABASE_URL (configure no Render)")
if not PUBLIC_URL:
    raise RuntimeError("Faltou PUBLIC_URL (configure no Render)")

try:
    import uvloop
    uvloop.install()
except Exception:
    pass

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# -------- Banco --------
_db_pool = None
async def db_pool():
    global _db_pool
    if _db_pool is None:
        _db_pool = await asyncpg.create_pool(DATABASE_URL, ssl="require")
    return _db_pool

# -------- Handlers --------
@dp.message(Command("start"))
async def cmd_start(message: Message):
    if message.from_user.id not in ADMINS:
        await message.answer("👋 Olá! Serviço temporariamente fora do ar para não cadastrados.")
        return
    await message.answer("Bem-vindo(a)! Use /menu para ver o cardápio.")

@dp.message(Command("whitelist"))
async def cmd_whitelist(message: Message):
    if message.from_user.id in ADMINS:
        await message.answer("✅ Usuário ativado para usar o bot")
    else:
        await message.answer("⛔ Você não é admin.")

@dp.message(Command("menu"))
async def cmd_menu(message: Message):
    kb = InlineKeyboardBuilder()
    kb.button(text="🍕 Produto Exemplo - R$90", callback_data="add:A12")
    kb.button(text="🧺 Ver carrinho", callback_data="cart")
    await message.answer("📋 Cardápio disponível:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("add:"))
async def cb_add(call: CallbackQuery):
    await call.message.answer("Produto adicionado ao carrinho ✅")

@dp.callback_query(F.data == "cart")
async def cb_cart(call: CallbackQuery):
    await call.message.answer("🧺 Seu carrinho:\n1x Produto Exemplo - R$90\n\nTotal: R$90")

# -------- Webhook --------
async def health(request):
    return web.Response(text="ok")

async def on_startup(app):
    webhook_url = f"{PUBLIC_URL}/webhook/{WEBHOOK_SECRET}"
    await bot.set_webhook(webhook_url, drop_pending_updates=True)
    print(f"Webhook set: {webhook_url}")

async def on_shutdown(app):
    try:
        await bot.delete_webhook(drop_pending_updates=False)
    except Exception:
        pass

def create_app():
    app = web.Application()
    app.router.add_get("/", health)
    SimpleRequestHandler(dp, bot).register(app, path=f"/webhook/{WEBHOOK_SECRET}")
    setup_application(app, dp, on_startup=on_startup, on_shutdown=on_shutdown)
    return app

async def main():
    app = create_app()
    port = int(os.getenv("PORT", "10000"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"HTTP webhook server on :{port}")
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
