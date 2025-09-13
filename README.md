# Cloud Telegram Bot (Python, aiogram)

## Variáveis (Render/Railway)
- BOT_TOKEN
- DATABASE_URL  (Neon, com sslmode=require)
- MP_ACCESS_TOKEN (Mercado Pago; opcional para testes)
- ADMINS  (IDs Telegram, vírgula separados)

## Deploy (Render)
1. Conecte ao GitHub e importe este repositório.
2. Tipo: Worker (ou Blueprint usando render.yaml)
3. Build: `pip install -r requirements.txt`
4. Start: `python -m src.main`
5. Defina as Environment Variables.

## Admin no Telegram
- `/whitelist` — ativa você
- `/newproduct SKU|Nome|PrecoEmCentavos|Estoque`
- Envie **foto** com legenda `SKU: ABC` (anexa imagem)
- `/toggle SKU`, `/setprice SKU|centavos`, `/setstock SKU|qtd`
- `/menu` — reenvia cardápio

## Cliente
- `/start` → botão **Ver cardápio**
- Botões: **➕**, **🧺 Carrinho**, **✅ Finalizar**
- Seleciona janela de entrega
- PIX (copia e cola) se MP_ACCESS_TOKEN definido
