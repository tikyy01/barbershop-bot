from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime

SERVICES = [
    ("✂️ Стрижка", "900 ₽"),
    ("👦 Детская стрижка", "900 ₽"),
    ("✂️🧔 Стрижка + борода", "1500 ₽"),
    ("🧔 Окантовка бороды", "800 ₽"),
    ("⚡ Стрижка под одну насадку", "500 ₽"),
    ("🪩 Стрижка налысо", "400 ₽"),
    ("💈 Окантовка головы", "300 ₽"),
    ("🎨 Камуфляж седины", "700 ₽"),
]

SERVICE_LABELS = {str(i): f"{name} — {price}" for i, (name, price) in enumerate(SERVICES)}

def client_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✂️ Записаться")],
            [KeyboardButton(text="📋 Мои записи")],
        ],
        resize_keyboard=True
    )

def admin_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📅 Записи на сегодня")],
            [KeyboardButton(text="📆 Все записи")],
            [KeyboardButton(text="🗂 Записи по дате")],
            [KeyboardButton(text="🕐 Управление расписанием")],
            [KeyboardButton(text="👤 Режим клиента")],
        ],
        resize_keyboard=True
    )

def services_keyboard():
    builder = InlineKeyboardBuilder()
    for i, (name, price) in enumerate(SERVICES):
        builder.button(text=f"{name} — {price}", callback_data=f"s:{i}")
    builder.adjust(1)
    return builder.as_markup()

def available_dates_keyboard(dates: list):
    builder = InlineKeyboardBuilder()
    days_ru = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    months_ru = ["янв", "фев", "мар", "апр", "май", "июн",
                 "июл", "авг", "сен", "окт", "ноя", "дек"]
    today = datetime.now().date()
    for d in dates:
        day = datetime.strptime(d, "%Y-%m-%d").date()
        diff = (day - today).days
        if diff == 0:
            prefix = "Сегодня"
        elif diff == 1:
            prefix = "Завтра"
        else:
            prefix = days_ru[day.weekday()]
        label = f"{prefix}, {day.day} {months_ru[day.month - 1]}"
        builder.button(text=label, callback_data=f"date:{d}")
    builder.adjust(2)
    return builder.as_markup()

def free_times_keyboard(free_slots: list):
    builder = InlineKeyboardBuilder()
    for slot in free_slots:
        builder.button(text=slot, callback_data=f"time:{slot}")
    builder.adjust(3)
    return builder.as_markup()

def contact_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Отправить номер", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def confirm_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data="confirm_booking")
    builder.button(text="❌ Отмена", callback_data="cancel_booking")
    builder.adjust(2)
    return builder.as_markup()

def appointment_manage_keyboard(appt_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data=f"admin_confirm:{appt_id}")
    builder.button(text="❌ Отменить", callback_data=f"admin_cancel:{appt_id}")
    builder.button(text="🗑 Удалить", callback_data=f"admin_delete:{appt_id}")
    builder.adjust(2)
    return builder.as_markup()

def cancel_appointment_keyboard(appt_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отменить запись", callback_data=f"client_cancel:{appt_id}")
    builder.adjust(1)
    return builder.as_markup()

def schedule_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить слоты на дату")],
            [KeyboardButton(text="📋 Посмотреть расписание")],
            [KeyboardButton(text="🔒 Закрыть один слот")],
            [KeyboardButton(text="🗑 Удалить все слоты на дату")],
            [KeyboardButton(text="🔙 Назад")],
        ],
        resize_keyboard=True
    )
