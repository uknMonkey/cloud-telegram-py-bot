# Cloud Telegram Bot — Webhook (Render)

## Variáveis necessárias
- BOT_TOKEN — do BotFather
- DATABASE_URL — Neon, com ?sslmode=require
- MP_ACCESS_TOKEN — (opcional, para PIX)
- ADMINS — IDs Telegram (números, separados por vírgula)
- PUBLIC_URL — URL pública do Render (ex.: https://cloud-telegram-py-bot.onrender.com)

## Deploy no Render
1. Crie Web Service a partir deste repo (plano Free).
2. Build Command: `pip install -r requirements.txt`
3. Start Command: `python -m src.main`
4. Configure as variáveis no painel Environment.
5. Deploy.

## Teste
- `/start` → mensagem para não cadastrados
- `/whitelist` (admin) → ativa o usuário
- `/menu` → cardápio de exemplo
