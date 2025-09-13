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
# -------- Catálogo e Carrinho (em memória) --------
from decimal import Decimal

# Exemplo de produtos (edite livremente)
PRODUCTS = [
    {
        "sku": "A12",
        "name": "Produto A12",
        "price_cents": 9000,  # R$ 90,00
        "photo_url": "https://picsum.photos/seed/a12/600/400",
        "description": "Descrição do Produto A12. Qualidade premium."
    },
    {
        "sku": "B21",
        "name": "Produto B21",
        "price_cents": 12000,  # R$ 120,00
        "photo_url": "https://picsum.photos/seed/b21/600/400",
        "description": "Produto B21 com ótimo custo-benefício."
    },
    {
        "sku": "C33",
        "name": "Produto C33",
        "price_cents": 4500,  # R$ 45,00
        "photo_url": "https://picsum.photos/seed/c33/600/400",
        "description": "C33 é compacto e eficiente."
    },
]

# taxa de entrega fixa (centavos)
DELIVERY_FEE_CENTS = 1000  # R$ 10,00

# Carrinhos por usuário: { user_id: {sku: qty, ...} }
CARTS: dict[int, dict[str, int]] = {}

def price_fmt(cents: int) -> str:
    reais = Decimal(cents) / Decimal(100)
    return f"R$ {reais:.2f}".replace(".", ",")

def get_product(sku: str):
    for p in PRODUCTS:
        if p["sku"] == sku:
            return p
    return None

def get_cart(user_id: int) -> dict[str, int]:
    return CARTS.setdefault(user_id, {})

def cart_total_cents(cart: dict[str, int]) -> int:
    total = 0
    for sku, qty in cart.items():
        p = get_product(sku)
        if p:
            total += p["price_cents"] * qty
    return total

def render_cart_text(user_id: int) -> str:
    cart = get_cart(user_id)
    if not cart:
        return "🧺 Seu carrinho está vazio."
    lines = ["🧺 *Seu carrinho:*"]
    for sku, qty in cart.items():
        p = get_product(sku)
        if p:
            lines.append(f"- {qty}x {p['name']} — {price_fmt(p['price_cents']*qty)}")
    subtotal = cart_total_cents(cart)
    lines.append(f"\nSubtotal: *{price_fmt(subtotal)}*")
    lines.append(f"Entrega: *{price_fmt(DELIVERY_FEE_CENTS)}* (fixa)")
    lines.append(f"Total: *{price_fmt(subtotal + DELIVERY_FEE_CENTS)}*")
    return "\n".join(lines)

# -------- Handlers --------
@dp.message(Command("start"))
async def cmd_start(message: Message):
    # Simples: só admins podem usar (troque depois para checar na tabela de customers)
    if message.from_user.id not in ADMINS:
        await message.answer("👋 Olá! Serviço temporariamente fora do ar para não cadastrados.")
        return
    await message.answer(
        "Bem-vindo(a)! 👋\nUse /menu para ver o cardápio.\n"
        "Comandos: /menu, /cart, /clear, /checkout"
    )

@dp.message(Command("menu"))
async def cmd_menu(message: Message):
    if message.from_user.id not in ADMINS:
        await message.answer("Serviço temporariamente fora do ar.")
        return

    kb = InlineKeyboardBuilder()
    for p in PRODUCTS:
        kb.button(text=f"📦 {p['name']} — {price_fmt(p['price_cents'])}", callback_data=f"prod:{p['sku']}")
    kb.button(text="🧺 Ver carrinho", callback_data="cart")
    await message.answer("📋 *Cardápio disponível:*\nSelecione um produto:", reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("prod:"))
async def cb_show_product(call: CallbackQuery):
    sku = call.data.split(":", 1)[1]
    p = get_product(sku)
    if not p:
        await call.answer("Produto não encontrado.", show_alert=True)
        return

    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Adicionar ao carrinho", callback_data=f"add:{sku}")
    kb.button(text="🧺 Ver carrinho", callback_data="cart")
    caption = (
        f"*{p['name']}*\n"
        f"{p['description']}\n\n"
        f"Preço: *{price_fmt(p['price_cents'])}*"
    )
    # Envia foto + legenda
    await call.message.answer_photo(photo=p["photo_url"], caption=caption, reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("add:"))
async def cb_add(call: CallbackQuery):
    sku = call.data.split(":", 1)[1]
    p = get_product(sku)
    if not p:
        await call.answer("Produto inválido.", show_alert=True)
        return

    cart = get_cart(call.from_user.id)
    cart[sku] = cart.get(sku, 0) + 1
    await call.answer("Adicionado ✅", show_alert=False)

    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Adicionar mais", callback_data=f"add:{sku}")
    kb.button(text="🧺 Ver carrinho", callback_data="cart")
    kb.button(text="🧹 Limpar carrinho", callback_data="clear")
    kb.button(text="✅ Finalizar pedido", callback_data="checkout")
    await call.message.answer(
        f"✅ *{p['name']}* adicionado.\n\n{render_cart_text(call.from_user.id)}",
        reply_markup=kb.as_markup(), parse_mode="Markdown"
    )

@dp.message(Command("cart"))
@dp.callback_query(F.data == "cart")
async def show_cart(evt):
    if isinstance(evt, Message):
        user_id = evt.from_user.id
        send = evt.answer
    else:  # CallbackQuery
        user_id = evt.from_user.id
        send = evt.message.answer

    kb = InlineKeyboardBuilder()
    kb.button(text="🧹 Limpar carrinho", callback_data="clear")
    kb.button(text="✅ Finalizar pedido", callback_data="checkout")
    kb.button(text="📋 Voltar ao cardápio", callback_data="back_menu")
    await send(render_cart_text(user_id), reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data == "back_menu")
async def cb_back_menu(call: CallbackQuery):
    await cmd_menu(call.message)

@dp.message(Command("clear"))
@dp.callback_query(F.data == "clear")
async def clear_cart(evt):
    if isinstance(evt, Message):
        user_id = evt.from_user.id
        send = evt.answer
    else:
        user_id = evt.from_user.id
        send = evt.message.answer

    CARTS[user_id] = {}
    await send("🧹 Carrinho limpo.")

@dp.message(Command("checkout"))
@dp.callback_query(F.data == "checkout")
async def checkout(evt):
    if isinstance(evt, Message):
        user_id = evt.from_user.id
        send = evt.answer
    else:
        user_id = evt.from_user.id
        send = evt.message.answer

    cart = get_cart(user_id)
    if not cart:
        await send("Seu carrinho está vazio.")
        return

    subtotal = cart_total_cents(cart)
    total = subtotal + DELIVERY_FEE_CENTS

    # Aqui futuramente integramos PIX (Mercado Pago) e salvamos no banco
    txt = (
        "🧾 *Resumo do pedido:*\n\n"
        f"{render_cart_text(user_id)}\n\n"
        "_Pagamento:_ *PIX aleatório (a configurar)*\n"
        "_Entrega:_ janelas definidas por você\n"
    )
    await send(txt, parse_mode="Markdown")


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
