from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta

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
        if day < today:
            continue
        diff = (day - today).days
        prefix = "Сегодня" if diff == 0 else "Завтра" if diff == 1 else days_ru[day.weekday()]
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
        resize_keyboard=True, one_time_keyboard=True
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
    return builder.as_markup()

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

def admin_date_picker_keyboard(prefix="adm_date"):
    """Выбор даты на 14 дней вперёд — используется и для добавления и для просмотра."""
    builder = InlineKeyboardBuilder()
    days_ru = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    months_ru = ["янв", "фев", "мар", "апр", "май", "июн",
                 "июл", "авг", "сен", "окт", "ноя", "дек"]
    today = datetime.now().date()
    for i in range(14):
        day = today + timedelta(days=i)
        prefix_label = "Сегодня" if i == 0 else "Завтра" if i == 1 else days_ru[day.weekday()]
        label = f"{prefix_label}, {day.day} {months_ru[day.month - 1]}"
        builder.button(text=label, callback_data=f"{prefix}:{day.strftime('%Y-%m-%d')}")
    builder.button(text="✏️ Ввести дату вручную", callback_data=f"{prefix}:manual")
    builder.adjust(2)
    return builder.as_markup()

def admin_time_picker_keyboard(selected: list):
    builder = InlineKeyboardBuilder()
    start = datetime.strptime("10:00", "%H:%M")
    end = datetime.strptime("20:00", "%H:%M")
    current = start
    while current <= end:
        t = current.strftime("%H:%M")
        label = f"✅ {t}" if t in selected else t
        builder.button(text=label, callback_data=f"adm_time:{t}")
        current += timedelta(minutes=15)
    builder.button(text="✏️ Добавить своё время", callback_data="adm_time:manual")
    builder.button(text="💾 Сохранить", callback_data="adm_time:save")
    builder.adjust(4)
    return builder.as_markup()

def schedule_view_slots_keyboard(all_slots: list, booked: list):
    """Расписание кнопками: ❌ занято, ✅ свободно."""
    builder = InlineKeyboardBuilder()
    for slot in all_slots:
        if slot in booked:
            builder.button(text=f"❌ {slot}", callback_data=f"view_slot:{slot}:busy")
        else:
            builder.button(text=f"✅ {slot}", callback_data=f"view_slot:{slot}:free")
    builder.adjust(3)
    return builder.as_markup()

def slot_action_keyboard(date: str, slot: str, appt_id: int = None):
    """Меню действий при нажатии на слот."""
    builder = InlineKeyboardBuilder()
    if appt_id:
        builder.button(text="🗑 Удалить запись", callback_data=f"admin_delete:{appt_id}")
        builder.button(text="✅ Подтвердить", callback_data=f"admin_confirm:{appt_id}")
        builder.button(text="❌ Отменить запись", callback_data=f"admin_cancel:{appt_id}")
    else:
        builder.button(text="🔒 Закрыть слот", callback_data=f"close_slot:{date}:{slot}")
        builder.button(text="🗑 Удалить слот", callback_data=f"del_slot:{date}:{slot}")
    builder.button(text="🔙 Назад", callback_data=f"view_back:{date}")
    builder.adjust(2)
    return builder.as_markup()
