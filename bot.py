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

# ---------------- HELPERS ----------------

SPACES_FILE = "spaces.txt"

def load_spaces():
    mapping = {}
    if os.path.exists(SPACES_FILE):
        with open(SPACES_FILE, "r") as f:
            for line in f:
                chat_id, space = line.strip().split(":")
                mapping[space] = int(chat_id)
    return mapping

def save_space(chat_id: int, space: str):
    lines = []
    if os.path.exists(SPACES_FILE):
        with open(SPACES_FILE, "r") as f:
            lines = f.readlines()

    with open(SPACES_FILE, "w") as f:
        for line in lines:
            if not line.strip().endswith(f":{space}"):
                f.write(line)
        f.write(f"{chat_id}:{space}\n")


# ---------------- FSM ----------------

class ReportForm(StatesGroup):
    oc = State()
    date = State()
    kids = State()
    teacher = State()
    lesson = State()
    media = State()
    confirm = State()


# ---------------- SETSPACE ----------------

@dp.message(F.text.startswith("/setspace"))
async def set_space(message: types.Message):
    parts = message.text.split(maxsplit=1)

    if len(parts) < 2:
        await message.answer("Вкажіть простір: /setspace Ромни або /setspace Одеса")
        return

    space = parts[1].strip()

    if space not in ["Ромни", "Одеса"]:
        await message.answer("Простір має бути: Ромни або Одеса")
        return

    save_space(message.chat.id, space)

    await message.answer(f"✔ Простір '{space}' прив’язано до цього чату.")


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
    text = message.text.strip()

    if text not in ["Ромни", "Одеса"]:
        await message.answer("Будь ласка, оберіть один із варіантів: Ромни або Одеса.")
        return

    await state.update_data(oc=text)

    await message.answer(
        "Введіть дату проведення (наприклад 31.08.2026):",
        reply_markup=types.ReplyKeyboardRemove()
    )

    await state.set_state(ReportForm.date)


# ---------------- STEP 2: ДАТА ----------------

@dp.message(ReportForm.date, F.text)
async def report_date(message: types.Message, state: FSMContext):
    await state.update_data(date=message.text.strip())

    await state.set_state(ReportForm.kids)
    await message.answer("Введіть кількість дітей:")


@dp.message(ReportForm.date)
async def report_date_invalid(message: types.Message):
    await message.answer("Будь ласка, введіть дату у форматі 31.08.2026")


# ---------------- STEP 3: КІЛЬКІСТЬ ДІТЕЙ ----------------

@dp.message(ReportForm.kids, F.text)
async def report_kids(message: types.Message, state: FSMContext):
    await state.update_data(kids=message.text.strip())

    await state.set_state(ReportForm.teacher)
    await message.answer("Введіть ПІП викладача (приклад: Шостак Наталія):")


# ---------------- STEP 4: ВИКЛАДАЧ ----------------

@dp.message(ReportForm.teacher, F.text)
async def report_teacher(message: types.Message, state: FSMContext):
    await state.update_data(teacher=message.text.strip())

    await state.set_state(ReportForm.lesson)
    await message.answer("Вкажіть назву заняття:")


# ---------------- STEP 5: НАЗВА ЗАНЯТТЯ ----------------

@dp.message(ReportForm.lesson, F.text)
async def report_lesson(message: types.Message, state: FSMContext):
    await state.update_data(lesson=message.text.strip())

    await state.set_state(ReportForm.media)

    kb = ReplyKeyboardBuilder()
    kb.button(text="Надіслати звіт")
    kb.adjust(1)

    await message.answer(
        "Надішліть фото або відео (до 10).\n"
        "Коли завершите — натисніть кнопку нижче.",
        reply_markup=kb.as_markup(resize_keyboard=True)
    )


# ---------------- STEP 6: МЕДІА ----------------

@dp.message(ReportForm.media, F.text == "Надіслати звіт")
async def report_media_done(message: types.Message, state: FSMContext):
    await state.set_state(ReportForm.confirm)

    data = await state.get_data()

    text = (
        f"Простір: {data['oc']}\n"
        f"Дата: {data['date']}\n"
        f"Кількість дітей: {data['kids']}\n"
        f"Викладач: {data['teacher']}\n"
        f"Назва заняття: {data['lesson']}"
    )

    kb = InlineKeyboardBuilder()
    kb.button(text="Підтвердити", callback_data="confirm_yes")
    kb.button(text="Скасувати", callback_data="confirm_no")
    kb.adjust(1)

    await message.answer(text + "\n\nПідтвердити відправку?", reply_markup=kb.as_markup())


@dp.message(ReportForm.media)
async def report_media_collect(message: types.Message, state: FSMContext):
    data = await state.get_data()
    media_list = data.get("media", [])

    if message.photo:
        media_list.append(("photo", message.photo[-1].file_id))
    elif message.video:
        media_list.append(("video", message.video.file_id))

    await state.update_data(media=media_list)


# ---------------- STEP 7: CALLBACK ----------------

@dp.callback_query(F.data == "confirm_yes")
async def report_confirm(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()

    spaces = load_spaces()
    chat_id = spaces.get(data["oc"])

    if not chat_id:
        await call.message.answer(
            "❗ Простір не прив’язано до жодного чату.\n"
            "Зайдіть у потрібний чат і виконайте:\n"
            "/setspace Ромни або /setspace Одеса"
        )
        return

    caption = (
        f"Простір: {data['oc']}\n"
        f"Дата: {data['date']}\n"
        f"Кількість дітей: {data['kids']}\n"
        f"Викладач: {data['teacher']}\n"
        f"Назва заняття: {data['lesson']}"
    )

    media_group = []

    for mtype, file_id in data.get("media", []):
        if mtype == "photo":
            media_group.append(types.InputMediaPhoto(media=file_id, caption=caption if len(media_group) == 0 else ""))
        else:
            media_group.append(types.InputMediaVideo(media=file_id, caption=caption if len(media_group) == 0 else ""))

    await bot.send_media_group(chat_id, media_group)

    await call.message.answer("✔ Звіт успішно надіслано!")
    await state.clear()

    kb = ReplyKeyboardBuilder()
    kb.button(text="Подати звіт")
    kb.adjust(1)

    await call.message.answer(
        "Готово! Можете подати новий звіт:",
        reply_markup=kb.as_markup(resize_keyboard=True)
    )


@dp.callback_query(F.data == "confirm_no")
async def report_cancel(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("❌ Відправку скасовано.")
    await state.clear()

    kb = ReplyKeyboardBuilder()
    kb.button(text="Подати звіт")
    kb.adjust(1)

    await call.message.answer(
        "Повертаємось до початку:",
        reply_markup=kb.as_markup(resize_keyboard=True)
    )


# ---------------- RUN ----------------

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
