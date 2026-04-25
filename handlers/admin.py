from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import ADMIN_ID
from database import (
    get_all_appointments, get_appointments_by_date,
    get_appointment_by_id, update_appointment_status, delete_appointment,
    add_time_slot, delete_time_slot, get_slots_by_date,
    get_booked_times, delete_slots_by_date, add_appointment
)
from keyboards import (
    admin_main_menu, client_main_menu, appointment_manage_keyboard,
    schedule_menu_keyboard
)
from datetime import datetime

router = Router()

STATUS_EMOJI = {"pending": "⏳", "confirmed": "✅", "cancelled": "❌"}
STATUS_RU = {"pending": "Ожидает", "confirmed": "Подтверждена", "cancelled": "Отменена"}

def is_admin(user_id): return user_id == ADMIN_ID

# ─── FSM ─────────────────────────────────────────────────────────────────────

class AdminState(StatesGroup):
    waiting_date = State()
    schedule_view_date = State()
    schedule_add_date = State()
    schedule_add_times = State()
    schedule_delete_date = State()
    close_slot_date = State()
    close_slot_time = State()
    delete_slot_date = State()

# ─── /aksizovadmin ────────────────────────────────────────────────────────────

@router.message(Command("aksizovadmin"))
async def cmd_admin(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await state.clear()
    await message.answer("👨‍💼 <b>Панель администратора</b>\n\nВыбери действие:",
                         reply_markup=admin_main_menu(), parse_mode="HTML")

# ─── Режим клиента ────────────────────────────────────────────────────────────

@router.message(F.text == "👤 Режим клиента", F.from_user.id == ADMIN_ID)
async def switch_to_client(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Переключено в режим клиента.", reply_markup=client_main_menu())

# ─── Записи на сегодня ────────────────────────────────────────────────────────

@router.message(F.text == "📅 Записи на сегодня", F.from_user.id == ADMIN_ID)
async def today_appointments(message: Message):
    today = datetime.now().strftime("%Y-%m-%d")
    appointments = await get_appointments_by_date(today)
    if not appointments:
        await message.answer(f"📅 На сегодня ({today}) записей нет.")
        return
    await message.answer(f"📅 <b>Записи на сегодня ({today}):</b>", parse_mode="HTML")
    for appt in appointments:
        await send_appointment_card(message.bot, message.chat.id, appt, show_manage=True)

# ─── Все записи ──────────────────────────────────────────────────────────────

@router.message(F.text == "📆 Все записи", F.from_user.id == ADMIN_ID)
async def all_appointments(message: Message):
    appointments = await get_all_appointments()
    if not appointments:
        await message.answer("📭 Записей пока нет.")
        return
    await message.answer(f"📆 <b>Все записи ({len(appointments)} шт.):</b>", parse_mode="HTML")
    for appt in appointments:
        await send_appointment_card(message.bot, message.chat.id, appt, show_manage=True)

# ─── Записи по дате ──────────────────────────────────────────────────────────

@router.message(F.text == "🗂 Записи по дате", F.from_user.id == ADMIN_ID)
async def by_date_ask(message: Message, state: FSMContext):
    await state.set_state(AdminState.waiting_date)
    await message.answer("📅 Введи дату в формате <b>ГГГГ-ММ-ДД</b>\nНапример: <code>2025-03-15</code>", parse_mode="HTML")

@router.message(AdminState.waiting_date, F.from_user.id == ADMIN_ID)
async def by_date_result(message: Message, state: FSMContext):
    date_str = message.text.strip()
    try: datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        await message.answer("❗ Неверный формат. Введи дату как: <code>2025-03-15</code>", parse_mode="HTML")
        return
    await state.clear()
    appointments = await get_appointments_by_date(date_str)
    if not appointments:
        await message.answer(f"📭 На {date_str} записей нет.", reply_markup=admin_main_menu())
        return
    await message.answer(f"📅 <b>Записи на {date_str}:</b>", parse_mode="HTML", reply_markup=admin_main_menu())
    for appt in appointments:
        await send_appointment_card(message.bot, message.chat.id, appt, show_manage=True)

# ─── УПРАВЛЕНИЕ РАСПИСАНИЕМ ───────────────────────────────────────────────────

@router.message(F.text == "🕐 Управление расписанием", F.from_user.id == ADMIN_ID)
async def schedule_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🕐 <b>Управление расписанием</b>",
                         reply_markup=schedule_menu_keyboard(), parse_mode="HTML")

@router.message(F.text == "🔙 Назад", F.from_user.id == ADMIN_ID)
async def back_to_admin(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Главное меню:", reply_markup=admin_main_menu())

# ─── Посмотреть расписание (с кнопками удаления слотов) ──────────────────────

@router.message(F.text == "📋 Посмотреть расписание", F.from_user.id == ADMIN_ID)
async def schedule_view_ask(message: Message, state: FSMContext):
    await state.set_state(AdminState.schedule_view_date)
    await message.answer("📅 Введи дату для просмотра расписания\nФормат: <b>ГГГГ-ММ-ДД</b>\nНапример: <code>2025-06-15</code>", parse_mode="HTML")

@router.message(AdminState.schedule_view_date, F.from_user.id == ADMIN_ID)
async def schedule_view_result(message: Message, state: FSMContext):
    date_str = message.text.strip()
    try: datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        await message.answer("❗ Неверный формат.", parse_mode="HTML")
        return
    await state.clear()

    all_slots = await get_slots_by_date(date_str)
    booked = await get_booked_times(date_str)
    appointments = await get_appointments_by_date(date_str)
    appt_by_time = {a["time"]: a for a in appointments if a["status"] != "cancelled"}

    if not all_slots:
        await message.answer(
            f"📭 На <b>{date_str}</b> нет добавленных слотов.",
            reply_markup=schedule_menu_keyboard(), parse_mode="HTML")
        return

    # Отправляем каждый слот отдельным сообщением с кнопками управления
    await message.answer(f"📅 <b>Расписание на {date_str}:</b>", parse_mode="HTML")

    for slot in all_slots:
        if slot in booked and slot in appt_by_time:
            appt = appt_by_time[slot]
            name = appt["full_name"] or "—"
            phone = appt["phone"] or "—"
            service = appt["service"] or "—"
            text = f"❌ <b>{slot}</b> — {name}, {phone}\n    📋 {service}"
            # Для занятых слотов — кнопка отмены записи
            builder = InlineKeyboardBuilder()
            builder.button(text="🗑 Удалить запись", callback_data=f"admin_delete:{appt['id']}")
            await message.answer(text, parse_mode="HTML", reply_markup=builder.as_markup())
        else:
            text = f"🕐 <b>{slot}</b> — свободно"
            # Для свободных слотов — кнопка удаления слота и закрытия
            builder = InlineKeyboardBuilder()
            builder.button(text="🔒 Закрыть", callback_data=f"close_slot:{date_str}:{slot}")
            builder.button(text="🗑 Удалить слот", callback_data=f"del_slot:{date_str}:{slot}")
            builder.adjust(2)
            await message.answer(text, parse_mode="HTML", reply_markup=builder.as_markup())

    await message.answer("─────────────────", reply_markup=schedule_menu_keyboard())

# ─── Закрыть один свободный слот (через кнопку в расписании) ─────────────────

@router.callback_query(F.data.startswith("close_slot:"), F.from_user.id == ADMIN_ID)
async def close_slot_inline(callback: CallbackQuery):
    _, date_str, time_str = callback.data.split(":")
    await add_appointment(
        user_id=0, username="admin", full_name="⛔ Закрыто",
        phone="—", service="Закрыто вручную", date=date_str, time=time_str
    )
    await callback.message.edit_text(
        f"🔒 <b>{time_str}</b> — закрыто вручную", parse_mode="HTML", reply_markup=None)
    await callback.answer("Слот закрыт!")

# ─── Удалить один слот из расписания (через кнопку в расписании) ─────────────

@router.callback_query(F.data.startswith("del_slot:"), F.from_user.id == ADMIN_ID)
async def delete_slot_inline(callback: CallbackQuery):
    _, date_str, time_str = callback.data.split(":")
    await delete_time_slot(date_str, time_str)
    await callback.message.edit_text(
        f"🗑 <b>{time_str}</b> — слот удалён", parse_mode="HTML", reply_markup=None)
    await callback.answer("Слот удалён!")

# ─── Добавить слоты на дату ───────────────────────────────────────────────────

@router.message(F.text == "➕ Добавить слоты на дату", F.from_user.id == ADMIN_ID)
async def schedule_add_ask_date(message: Message, state: FSMContext):
    await state.set_state(AdminState.schedule_add_date)
    await message.answer("📅 Введи дату\nФормат: <b>ГГГГ-ММ-ДД</b>\nНапример: <code>2025-06-15</code>", parse_mode="HTML")

@router.message(AdminState.schedule_add_date, F.from_user.id == ADMIN_ID)
async def schedule_add_ask_times(message: Message, state: FSMContext):
    date_str = message.text.strip()
    try: datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        await message.answer("❗ Неверный формат.", parse_mode="HTML")
        return
    await state.update_data(add_date=date_str)
    await state.set_state(AdminState.schedule_add_times)
    existing = await get_slots_by_date(date_str)
    existing_str = ", ".join(existing) if existing else "нет"
    await message.answer(
        f"✅ Дата: <b>{date_str}</b>\nУже добавлены: <i>{existing_str}</i>\n\n"
        f"⏰ Введи время через запятую или с новой строки\nФормат: <b>ЧЧ:ММ</b>\n\n"
        f"Пример:\n<code>09:00, 10:00, 11:30, 14:00</code>", parse_mode="HTML")

@router.message(AdminState.schedule_add_times, F.from_user.id == ADMIN_ID)
async def schedule_add_do(message: Message, state: FSMContext):
    data = await state.get_data()
    date_str = data["add_date"]
    raw = message.text.strip().replace("\n", ",")
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    added, skipped, errors = [], [], []
    for part in parts:
        try:
            datetime.strptime(part, "%H:%M")
            ok = await add_time_slot(date_str, part)
            (added if ok else skipped).append(part)
        except ValueError:
            errors.append(part)
    await state.clear()
    result = [f"📅 <b>Результат для {date_str}:</b>\n"]
    if added: result.append(f"✅ Добавлено: {', '.join(added)}")
    if skipped: result.append(f"⚠️ Уже были: {', '.join(skipped)}")
    if errors: result.append(f"❗ Неверный формат: {', '.join(errors)}")
    await message.answer("\n".join(result), reply_markup=schedule_menu_keyboard(), parse_mode="HTML")

# ─── Удалить все слоты на дату ────────────────────────────────────────────────

@router.message(F.text == "🗑 Удалить все слоты на дату", F.from_user.id == ADMIN_ID)
async def schedule_delete_ask(message: Message, state: FSMContext):
    await state.set_state(AdminState.schedule_delete_date)
    await message.answer("📅 Введи дату для удаления всех слотов\nФормат: <b>ГГГГ-ММ-ДД</b>", parse_mode="HTML")

@router.message(AdminState.schedule_delete_date, F.from_user.id == ADMIN_ID)
async def schedule_delete_do(message: Message, state: FSMContext):
    date_str = message.text.strip()
    try: datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        await message.answer("❗ Неверный формат.", parse_mode="HTML")
        return
    await state.clear()
    existing = await get_slots_by_date(date_str)
    if not existing:
        await message.answer(f"📭 На {date_str} слотов нет.", reply_markup=schedule_menu_keyboard())
        return
    await delete_slots_by_date(date_str)
    await message.answer(f"🗑 Все слоты на <b>{date_str}</b> удалены ({len(existing)} шт.)",
                         reply_markup=schedule_menu_keyboard(), parse_mode="HTML")

# ─── Закрыть слот вручную (через меню) ───────────────────────────────────────

@router.message(F.text == "🔒 Закрыть слот вручную", F.from_user.id == ADMIN_ID)
async def close_slot_ask_date(message: Message, state: FSMContext):
    await state.set_state(AdminState.close_slot_date)
    await message.answer("📅 Введи дату слота который нужно закрыть\nФормат: <b>ГГГГ-ММ-ДД</b>", parse_mode="HTML")

@router.message(AdminState.close_slot_date, F.from_user.id == ADMIN_ID)
async def close_slot_ask_time(message: Message, state: FSMContext):
    date_str = message.text.strip()
    try: datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        await message.answer("❗ Неверный формат.", parse_mode="HTML")
        return
    from database import get_free_slots
    free = await get_free_slots(date_str)
    if not free:
        await message.answer(f"📭 На {date_str} нет свободных слотов.", reply_markup=schedule_menu_keyboard())
        await state.clear()
        return
    await state.update_data(close_date=date_str)
    await state.set_state(AdminState.close_slot_time)
    slots_str = "\n".join([f"• {s}" for s in free])
    await message.answer(
        f"Свободные слоты на <b>{date_str}</b>:\n{slots_str}\n\n"
        f"Введи время: <code>14:00</code>", parse_mode="HTML")

@router.message(AdminState.close_slot_time, F.from_user.id == ADMIN_ID)
async def close_slot_do(message: Message, state: FSMContext):
    data = await state.get_data()
    date_str = data["close_date"]
    time_str = message.text.strip()
    try: datetime.strptime(time_str, "%H:%M")
    except ValueError:
        await message.answer("❗ Неверный формат. Введи как <code>14:00</code>", parse_mode="HTML")
        return
    await state.clear()
    await add_appointment(user_id=0, username="admin", full_name="⛔ Закрыто",
                          phone="—", service="Закрыто вручную", date=date_str, time=time_str)
    await message.answer(
        f"🔒 Слот <b>{time_str}</b> на <b>{date_str}</b> закрыт.",
        reply_markup=schedule_menu_keyboard(), parse_mode="HTML")

# ─── Карточка записи ─────────────────────────────────────────────────────────

async def send_appointment_card(bot: Bot, chat_id: int, appt, show_manage=False):
    emoji = STATUS_EMOJI.get(appt["status"], "❓")
    status_text = STATUS_RU.get(appt["status"], appt["status"])
    username_str = f"@{appt['username']}" if appt["username"] else "нет username"
    text = (
        f"{emoji} <b>Запись #{appt['id']}</b>\n"
        f"👤 {appt['full_name']} ({username_str})\n"
        f"📞 {appt['phone']}\n"
        f"✂️ {appt['service']}\n"
        f"📅 {appt['date']} в {appt['time']}\n"
        f"Статус: {status_text}"
    )
    markup = appointment_manage_keyboard(appt["id"]) if show_manage and appt["status"] != "cancelled" else None
    await bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=markup)

# ─── Подтвердить запись ───────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin_confirm:"), F.from_user.id == ADMIN_ID)
async def admin_confirm(callback: CallbackQuery, bot: Bot):
    appt_id = int(callback.data.split(":")[1])
    appt = await get_appointment_by_id(appt_id)
    if not appt:
        await callback.answer("Запись не найдена.", show_alert=True)
        return
    await update_appointment_status(appt_id, "confirmed")
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("✅ Запись подтверждена!")
    await callback.message.answer(f"✅ Запись <b>#{appt_id}</b> подтверждена.", parse_mode="HTML")
    await bot.send_message(appt["user_id"],
        f"✅ <b>Ваша запись подтверждена!</b>\n\n"
        f"✂️ {appt['service']}\n📅 {appt['date']} в {appt['time']}\n\n"
        f"📍 Ждём вас по адресу: <b>ул. Астраханская 19</b> 💈", parse_mode="HTML")

# ─── Отменить запись ─────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin_cancel:"), F.from_user.id == ADMIN_ID)
async def admin_cancel(callback: CallbackQuery, bot: Bot):
    appt_id = int(callback.data.split(":")[1])
    appt = await get_appointment_by_id(appt_id)
    if not appt:
        await callback.answer("Запись не найдена.", show_alert=True)
        return
    await update_appointment_status(appt_id, "cancelled")
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("❌ Запись отменена!")
    await callback.message.answer(f"❌ Запись <b>#{appt_id}</b> отменена.", parse_mode="HTML")
    if appt["user_id"] != 0:
        await bot.send_message(appt["user_id"],
            f"❌ <b>Ваша запись отменена.</b>\n\n"
            f"✂️ {appt['service']}\n📅 {appt['date']} в {appt['time']}\n\n"
            f"Пожалуйста, запишитесь на другое время.", parse_mode="HTML")

# ─── Удалить запись ──────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin_delete:"), F.from_user.id == ADMIN_ID)
async def admin_delete(callback: CallbackQuery):
    appt_id = int(callback.data.split(":")[1])
    appt = await get_appointment_by_id(appt_id)
    await delete_appointment(appt_id)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("🗑 Удалено!")
    await callback.message.edit_text(
        callback.message.text + "\n\n<i>🗑 Запись удалена</i>", parse_mode="HTML")
