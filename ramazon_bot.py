import logging
import os
import requests
from datetime import datetime, date, timedelta
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

# ================== SOZLAMALAR ==================
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")

# Ramazon boshlanishi (2026)
RAMAZAN_START = date(2026, 2, 18)

# Viloyatlar va markazlari
CITIES = {
    "Toshkent": "Tashkent",
    "Andijon": "Andijan",
    "Farg‘ona": "Fergana",
    "Namangan": "Namangan",
    "Samarqand": "Samarkand",
    "Buxoro": "Bukhara",
    "Navoiy": "Navoi",
    "Jizzax": "Jizzakh",
    "Sirdaryo": "Gulistan",
    "Qashqadaryo": "Karshi",
    "Surxondaryo": "Termez",
    "Xorazm": "Urgench",
    "Toshkent v.": "Nurafshon",
    "Qoraqalpog‘iston": "Nukus",
}

# ================== BOT ==================
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot)

# ================== YORDAMCHI FUNKSIYALAR ==================

async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except:
        return False

def get_prayer_times(city_en: str):
    today = datetime.now().strftime("%d-%m-%Y")
    url = f"https://api.aladhan.com/v1/timingsByCity/{today}"
    params = {"city": city_en, "country": "Uzbekistan", "method": 2}
    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()["data"]["timings"]
        return data["Fajr"], data["Maghrib"]
    except:
        return None, None

def get_ramazan_day() -> int:
    today = date.today()
    return (today - RAMAZAN_START).days + 1

def time_to_ramazan_start() -> str:
    now = datetime.now()
    ramazan_datetime = datetime.combine(RAMAZAN_START, datetime.min.time())
    if now >= ramazan_datetime:
        return "Ramazon allaqachon boshlandi 🌙"
    delta = ramazan_datetime - now
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return f"⏳ Ramazon boshlanishigacha: {days} kun, {hours} soat, {minutes} daqiqa"

def regions_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for region in CITIES.keys():
        kb.add(region)
    return kb

def subscribe_keyboard():
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("🔔 Kanalga obuna bo‘lish", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}")
    )
    kb.add(
        InlineKeyboardButton("✅ Tekshirish", callback_data="check_sub")
    )
    return kb

# ================== HANDLERLAR ==================

@dp.message_handler(commands="start")
async def start_handler(message: types.Message):
    user_name = message.from_user.first_name
    if not await check_subscription(message.from_user.id):
        await message.answer(
            f"⚠️ Assalomu alaykum, {user_name}!\n\n"
            "Botdan foydalanish uchun avval kanalga obuna bo‘ling:",
            reply_markup=subscribe_keyboard()
        )
        return

    await message.answer(
        f"Assalomu alaykum, {user_name}!\n"
        f"{time_to_ramazan_start()}\n\n📍 Viloyatingizni tanlang:",
        reply_markup=regions_keyboard()
    )

@dp.callback_query_handler(lambda c: c.data == "check_sub")
async def recheck_subscription(call: types.CallbackQuery):
    if await check_subscription(call.from_user.id):
        await call.message.delete()
        await start_handler(call.message)
    else:
        await call.answer("❌ Siz hali kanalga obuna bo‘lmadingiz", show_alert=True)

@dp.message_handler(lambda m: m.text in CITIES)
async def region_handler(message: types.Message):
    if not await check_subscription(message.from_user.id):
        await message.answer(
            "❌ Avval kanalga obuna bo‘ling",
            reply_markup=subscribe_keyboard()
        )
        return

    city_en = CITIES[message.text]
    saharlik, iftor = get_prayer_times(city_en)
    ramazan_day = get_ramazan_day()
    user_name = message.from_user.first_name

    if saharlik is None:
        await message.answer("⚠️ Maʼlumotni olishda xatolik yuz berdi. Keyinroq qayta urinib ko‘ring.")
        return

    # Saharlik duosi
    saharlik_duo_arab = "Navaytu an asuma sovma shahri ramazona minal fajri ilal mag‘ribi, xolisan lillahi ta’ala. Allohu akbar."
    saharlik_duo_uz = "Ma’nosi: Ramazon oyining ro‘zasini subhdan to kun botguncha tutmoqni niyat qildim. Xolis Alloh uchun Alloh buyukdir."

    # Iftor duosi
    iftor_duo_arab = "Allohumma laka sumtu va bika amantu va a’layka tavakkaltu va a’la rizqika aftartu, fag‘firli ya g‘offaru ma qoddamtu va ma axxortu."
    iftor_duo_uz = "Ma’nosi: Ey Alloh, ushbu Ro‘zamni Sen uchun tutdim va Senga iymon keltirdim va Senga tavakkal qildim va bergan rizqing bilan iftor qildim. Ey mehribonlarning eng mehriboni, mening avvalgi va keyingi gunohlarimni mag‘firat qilgil."

    # HTML bilan chiroyli format
    msg = (
        f"📍 <b>{message.text}</b>\n"
        f"📅 {datetime.now().strftime('%d.%m.%Y')}\n"
        f"🌙 {ramazan_day}-Ramazon\n"
        f"⏰ Saharlik: {saharlik}\n"
        f"🌇 Iftor: {iftor}\n\n"
        f"{time_to_ramazan_start()}\n\n"
        f"🕋 <b>Saharlik duosi:</b>\n"
        f"{saharlik_duo_arab}\n"
        f"{saharlik_duo_uz}\n\n"
        f"🌅 <b>Iftor duosi:</b>\n"
        f"{iftor_duo_arab}\n"
        f"{iftor_duo_uz}"
    )

    await message.answer(msg)

# ================== ISHGA TUSHIRISH ==================
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
