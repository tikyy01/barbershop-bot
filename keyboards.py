from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta

# ─── Услуги ──────────────────────────────────────────────────────────────────

SERVICES = [
    ("✂️ Стрижка", "900 ₽"),
    ("👦 Детская стрижка", "900 ₽"),
    ("✂️🧔 Стрижка + борода", "1500 ₽"),
    ("🧔 Окантовка бороды", "800 ₽"),
    ("⚡ Стрижка под одну насадку", "500 ₽"),
    ("👨‍🦲 Стрижка налысо", "400 ₽"),
    ("💈 Окантовка головы", "300 ₽"),
    ("🎨 Камуфляж седины", "700 ₽"),
]

SERVICE_LABELS = {str(i): f"{name} — {price}" for i, (name, price) in enumerate(SERVICES)}

# ─── Главное меню клиента ─────────────────────────────────────────────────────

def client_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✂️ Записаться")],
            [KeyboardButton(text="📋 Мои записи")],
        ],
        resize_keyboard=True
    )

# ─── Главное меню админа ──────────────────────────────────────────────────────

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

# ─── Выбор услуги (клиент) ───────────────────────────────────────────────────

def services_keyboard():
    builder = InlineKeyboardBuilder()
    for i, (name, price) in enumerate(SERVICES):
        builder.button(text=f"{name} — {price}", callback_data=f"s:{i}")
    builder.adjust(1)
    return builder.as_markup()

# ─── Выбор даты (клиент) — только даты со свободными слотами ─────────────────

def available_dates_keyboard(dates: list):
    builder = InlineKeyboardBuilder()
    days_ru = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    months_ru = ["янв", "фев", "мар", "апр", "май", "июн",
                 "июл", "авг", "сен", "окт", "ноя", "дек"]
    today = datetime.now().date()
    for d in dates:
        day = datetime.strptime(d, "%Y-%m-%d").date()
        if day < today:
            continue  # пропускаем прошедшие даты
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

# ─── Выбор времени (клиент) ───────────────────────────────────────────────────

def free_times_keyboard(free_slots: list):
    builder = InlineKeyboardBuilder()
    for slot in free_slots:
        builder.button(text=slot, callback_data=f"time:{slot}")
    builder.adjust(3)
    return builder.as_markup()

# ─── Запрос контакта ─────────────────────────────────────────────────────────

def contact_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Отправить номер", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

# ─── Подтверждение записи ─────────────────────────────────────────────────────

def confirm_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data="confirm_booking")
    builder.button(text="❌ Отмена", callback_data="cancel_booking")
    builder.adjust(2)
    return builder.as_markup()

# ─── Управление записью (админ) ───────────────────────────────────────────────

def appointment_manage_keyboard(appt_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data=f"admin_confirm:{appt_id}")
    builder.button(text="❌ Отменить", callback_data=f"admin_cancel:{appt_id}")
    builder.button(text="🗑 Удалить", callback_data=f"admin_delete:{appt_id}")
    builder.adjust(2)
    return builder.as_markup()

# ─── Отмена записи клиентом ───────────────────────────────────────────────────

def cancel_appointment_keyboard(appt_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отменить запись", callback_data=f"client_cancel:{appt_id}")
    return builder.as_markup()

# ─── Меню расписания (админ) ──────────────────────────────────────────────────

def schedule_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить слоты на дату")],
            [KeyboardButton(text="📋 Посмотреть расписание")],
            [KeyboardButton(text="🗑 Удалить все слоты на дату")],
            [KeyboardButton(text="🔒 Закрыть слот вручную")],
            [KeyboardButton(text="🔙 Назад")],
        ],
        resize_keyboard=True
    )

# ─── Выбор даты (админ) — ближайшие 14 дней ──────────────────────────────────

def admin_date_picker_keyboard():
    builder = InlineKeyboardBuilder()
    days_ru = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    months_ru = ["янв", "фев", "мар", "апр", "май", "июн",
                 "июл", "авг", "сен", "окт", "ноя", "дек"]
    today = datetime.now().date()
    for i in range(14):
        day = today + timedelta(days=i)
        if i == 0:
            prefix = "Сегодня"
        elif i == 1:
            prefix = "Завтра"
        else:
            prefix = days_ru[day.weekday()]
        label = f"{prefix}, {day.day} {months_ru[day.month - 1]}"
        builder.button(text=label, callback_data=f"adm_date:{day.strftime('%Y-%m-%d')}")
    builder.button(text="✏️ Ввести дату вручную", callback_data="adm_date:manual")
    builder.adjust(2)
    return builder.as_markup()

# ─── Выбор времени (админ) — с 10:00 до 20:00 каждые 15 минут + галочки ──────

def admin_time_picker_keyboard(selected: list):
    builder = InlineKeyboardBuilder()
    start = datetime.strptime("10:00", "%H:%M")
    end = datetime.strptime("20:00", "%H:%M")
    current = start
    while current <= end:
        t = current.strftime("%H:%M")
        if t in selected:
            label = f"✅ {t}"
        else:
            label = t
        builder.button(text=label, callback_data=f"adm_time:{t}")
        current += timedelta(minutes=15)
    builder.button(text="✏️ Добавить своё время", callback_data="adm_time:manual")
    builder.button(text="💾 Сохранить", callback_data="adm_time:save")
    builder.adjust(4)
    return builder.as_markup()
