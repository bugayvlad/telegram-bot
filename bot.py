from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
import asyncio
import os

API_TOKEN = os.getenv("API_TOKEN")

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# ---------------- FSM ----------------

class ReportForm(StatesGroup):
    oc = State()
    date = State()
    kids = State()
    teacher = State()
    media = State()
    confirm = State()

# ---------------- START ----------------

@dp.message(Command("start"))
async def start(message: types.Message):
    kb = ReplyKeyboardBuilder()
    kb.button(text="Подати звіт")
    kb.adjust(1)

    await message.answer(
        "Вітаю! Натисніть кнопку нижче:",
        reply_markup=kb.as_markup(resize_keyboard=True)
    )

# ---------------- STEP 1: ПРОСТІР ----------------

@dp.message(F.text == "Подати звіт")
async def report_start(message: types.Message, state: FSMContext):
    kb = ReplyKeyboardBuilder()
    kb.button(text="Ромни")
    kb.button(text="Одеса")
    kb.adjust(1)

    await state.set_state(ReportForm.oc)
    await message.answer(
        "Вітаю!\nОберіть простір:",
        reply_markup=kb.as_markup(resize_keyboard=True)
    )

@dp.message(ReportForm.oc)
async def report_oc(message: types.Message, state: FSMContext):
    oc_clean = message.text.strip()
    await state.update_data(oc=oc_clean)

    await message.answer(
        "Введіть дату проведення (наприклад 31.08.2026):",
        reply_markup=types.ReplyKeyboardRemove()
    )

    await state.set_state(ReportForm.date)

# ---------------- STEP 2: ДАТА ----------------

@dp.message(ReportForm.date)
async def report_date(message: types.Message, state: FSMContext):
    await state.update_data(date=message.text)

    await state.set_state(ReportForm.kids)
    await message.answer("Введіть кількість дітей:")

# ---------------- STEP 3: КІЛЬКІСТЬ ДІТЕЙ ----------------

@dp.message(ReportForm.kids)
async def report_kids(message: types.Message, state: FSMContext):
    await state.update_data(kids=message.text)

    await state.set_state(ReportForm.teacher)
    await message.answer("Введіть ПІП викладача (приклад: Шостак Наталія):")

# ---------------- STEP 4: ВИКЛАДАЧ ----------------

@dp.message(ReportForm.teacher)
async def report_teacher(message: types.Message, state: FSMContext):
    await state.update_data(teacher=message.text)

    await state.set_state(ReportForm.media)

    kb = ReplyKeyboardBuilder()
    kb.button(text="Надіслати звіт")
    kb.adjust(1)

    await message.answer(
        "Надішліть фото або відео (до 10).\n"
        "Коли завершите — натисніть кнопку нижче.",
        reply_markup=kb.as_markup(resize_keyboard=True)
    )

# ---------------- STEP 5: МЕДІА ----------------

@dp.message(ReportForm.media, F.text == "Надіслати звіт")
async def report_media_done(message: types.Message, state: FSMContext):
    await state.set_state(ReportForm.confirm)

    data = await state.get_data()

    text = (
        f"Перевірте дані:\n\n"
        f"Простір: {data['oc']}\n"
        f"Дата: {data['date']}\n"
        f"Кількість дітей: {data['kids']}\n"
        f"Викладач: {data['teacher']}\n"
        f"Фото/відео: додано\n\n"
        f"Підтвердити відправку?"
    )

    kb = InlineKeyboardBuilder()
    kb.button(text="Підтвердити", callback_data="confirm_yes")
    kb.button(text="Скасувати", callback_data="confirm_no")
    kb.adjust(1)

    await message.answer(text, reply_markup=kb.as_markup())

@dp.message(ReportForm.media)
async def report_media_collect(message: types.Message, state: FSMContext):
    data = await state.get_data()
    media_list = data.get("media", [])

    if message.photo:
        media_list.append(("photo", message.photo[-1].file_id))
    elif message.video:
        media_list.append(("video", message.video.file_id))

    await state.update_data(media=media_list)

# ---------------- STEP 6: ВІДПРАВКА ----------------

@dp.callback_query(ReportForm.confirm, F.data == "confirm_yes")
async def report_confirm(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()

    # Чати Golden Berry
    oc_chat_map = {
        "Ромни": -1001760038328,   # чат Ромни
        "Одеса": -1002100782948    # чат Одеса
    }

    chat_id = oc_chat_map.get(data["oc"])

    # Надсилання тексту
    await bot.send_message(
        chat_id,
        f"Звіт:\n\n"
        f"Простір: {data['oc']}\n"
        f"Дата: {data['date']}\n"
        f"Кількість дітей: {data['kids']}\n"
        f"Викладач: {data['teacher']}"
    )

    # Надсилання медіа
    for mtype, file_id in data.get("media", []):
        if mtype == "photo":
            await bot.send_photo(chat_id, file_id)
        else:
            await bot.send_video(chat_id, file_id)

    await call.message.answer("✔ Звіт успішно надіслано!")
    await state.clear()

@dp.callback_query(ReportForm.confirm, F.data == "confirm_no")
async def report_cancel(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("❌ Відправку скасовано.")
    await state.clear()

# ---------------- RUN ----------------

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
