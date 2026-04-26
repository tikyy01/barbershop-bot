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
    schedule_menu_keyboard, admin_date_picker_keyboard, admin_time_picker_keyboard,
    schedule_view_slots_keyboard, slot_action_keyboard
)
from datetime import datetime, timedelta

router = Router()

STATUS_EMOJI = {"pending": "⏳", "confirmed": "✅", "cancelled": "❌"}
STATUS_RU = {"pending": "Ожидает", "confirmed": "Подтверждена", "cancelled": "Отменена"}

def is_admin(user_id): return user_id == ADMIN_ID

class AdminState(StatesGroup):
    waiting_date = State()
    # просмотр расписания
    view_picking_date = State()
    view_manual_date = State()
    # добавление слотов
    add_picking_date = State()
    add_manual_date = State()
    add_picking_times = State()
    add_manual_time = State()
    # удаление / закрытие
    schedule_delete_date = State()
    close_slot_date = State()
    close_slot_time = State()

# ─── /aksizovadmin ────────────────────────────────────────────────────────────

@router.message(Command("aksizovadmin"))
async def cmd_admin(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await state.clear()
    await message.answer("👨‍💼 <b>Панель администратора</b>",
                         reply_markup=admin_main_menu(), parse_mode="HTML")

@router.message(F.text == "👤 Режим клиента", F.from_user.id == ADMIN_ID)
async def switch_to_client(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Режим клиента:", reply_markup=client_main_menu())

@router.message(F.text == "🔙 Назад", F.from_user.id == ADMIN_ID)
async def back_to_admin(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Главное меню:", reply_markup=admin_main_menu())

# ─── Записи на сегодня ────────────────────────────────────────────────────────

@router.message(F.text == "📅 Записи на сегодня", F.from_user.id == ADMIN_ID)
async def today_appointments(message: Message):
    today = datetime.now().strftime("%Y-%m-%d")
    appointments = await get_appointments_by_date(today)
    if not appointments:
        await message.answer(f"📅 На сегодня записей нет.")
        return
    await message.answer(f"📅 <b>Записи на сегодня ({today}):</b>", parse_mode="HTML")
    for appt in appointments:
        await send_appointment_card(message.bot, message.chat.id, appt, show_manage=True)

@router.message(F.text == "📆 Все записи", F.from_user.id == ADMIN_ID)
async def all_appointments(message: Message):
    appointments = await get_all_appointments()
    if not appointments:
        await message.answer("📭 Записей пока нет.")
        return
    await message.answer(f"📆 <b>Все записи ({len(appointments)} шт.):</b>", parse_mode="HTML")
    for appt in appointments:
        await send_appointment_card(message.bot, message.chat.id, appt, show_manage=True)

@router.message(F.text == "🗂 Записи по дате", F.from_user.id == ADMIN_ID)
async def by_date_ask(message: Message, state: FSMContext):
    await state.set_state(AdminState.waiting_date)
    await message.answer("📅 Введи дату: <b>ГГГГ-ММ-ДД</b>", parse_mode="HTML")

@router.message(AdminState.waiting_date, F.from_user.id == ADMIN_ID)
async def by_date_result(message: Message, state: FSMContext):
    date_str = message.text.strip()
    try: datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        await message.answer("❗ Например: <code>2025-03-15</code>", parse_mode="HTML")
        return
    await state.clear()
    appointments = await get_appointments_by_date(date_str)
    if not appointments:
        await message.answer(f"📭 На {date_str} записей нет.", reply_markup=admin_main_menu())
        return
    await message.answer(f"📅 <b>Записи на {date_str}:</b>", parse_mode="HTML", reply_markup=admin_main_menu())
    for appt in appointments:
        await send_appointment_card(message.bot, message.chat.id, appt, show_manage=True)

# ─── Управление расписанием ───────────────────────────────────────────────────

@router.message(F.text == "🕐 Управление расписанием", F.from_user.id == ADMIN_ID)
async def schedule_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🕐 <b>Управление расписанием</b>",
                         reply_markup=schedule_menu_keyboard(), parse_mode="HTML")

# ─── ПРОСМОТР РАСПИСАНИЯ — выбор даты кнопками ───────────────────────────────

@router.message(F.text == "📋 Посмотреть расписание", F.from_user.id == ADMIN_ID)
async def schedule_view_pick_date(message: Message, state: FSMContext):
    await state.set_state(AdminState.view_picking_date)
    await message.answer("📅 <b>Выбери дату для просмотра:</b>",
                         reply_markup=admin_date_picker_keyboard(prefix="view_date"),
                         parse_mode="HTML")

@router.callback_query(AdminState.view_picking_date, F.data.startswith("view_date:"), F.from_user.id == ADMIN_ID)
async def schedule_view_date_chosen(callback: CallbackQuery, state: FSMContext):
    value = callback.data.split(":", 1)[1]
    if value == "manual":
        await state.set_state(AdminState.view_manual_date)
        await callback.message.edit_text("✏️ Введи дату: <b>ГГГГ-ММ-ДД</b>", parse_mode="HTML")
        return
    await state.clear()
    await show_schedule(callback.message, value, edit=True)

@router.message(AdminState.view_manual_date, F.from_user.id == ADMIN_ID)
async def schedule_view_manual_date(message: Message, state: FSMContext):
    date_str = message.text.strip()
    try: datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        await message.answer("❗ Например: <code>2025-08-20</code>", parse_mode="HTML")
        return
    await state.clear()
    await show_schedule(message, date_str, edit=False)

async def show_schedule(msg, date_str: str, edit: bool):
    all_slots = await get_slots_by_date(date_str)
    booked = await get_booked_times(date_str)

    if not all_slots:
        text = f"📭 На <b>{date_str}</b> нет добавленных слотов."
        if edit:
            await msg.edit_text(text, parse_mode="HTML", reply_markup=None)
        else:
            await msg.answer(text, parse_mode="HTML", reply_markup=schedule_menu_keyboard())
        return

    free_count = len([s for s in all_slots if s not in booked])
    busy_count = len(booked)
    text = (
        f"📅 <b>Расписание на {date_str}</b>\n"
        f"✅ Свободно: {free_count}  |  ❌ Занято: {busy_count}\n\n"
        f"Нажми на слот для управления:"
    )
    kb = schedule_view_slots_keyboard(all_slots, booked)
    if edit:
        await msg.edit_text(text, parse_mode="HTML", reply_markup=kb)
    else:
        await msg.answer(text, parse_mode="HTML", reply_markup=kb)

# ─── Нажатие на слот в расписании ────────────────────────────────────────────

@router.callback_query(F.data.startswith("view_slot:"), F.from_user.id == ADMIN_ID)
async def view_slot_action(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    slot = parts[1]
    status = parts[2]

    # Достаём дату из текста сообщения
    import re
    match = re.search(r"(\d{4}-\d{2}-\d{2})", callback.message.text)
    date_str = match.group(1) if match else ""

    if status == "free":
        text = f"🕐 <b>{slot}</b> — свободно\n\nЧто сделать с этим слотом?"
        kb = slot_action_keyboard(date_str, slot)
    else:
        # Найти запись на это время
        appointments = await get_appointments_by_date(date_str)
        appt = next((a for a in appointments if a["time"] == slot and a["status"] != "cancelled"), None)
        if appt:
            text = (
                f"❌ <b>{slot}</b> — занято\n\n"
                f"👤 {appt['full_name']}\n"
                f"📞 {appt['phone']}\n"
                f"✂️ {appt['service']}\n"
                f"Статус: {STATUS_RU.get(appt['status'], appt['status'])}"
            )
            kb = slot_action_keyboard(date_str, slot, appt_id=appt["id"])
        else:
            text = f"❌ <b>{slot}</b> — занято"
            kb = slot_action_keyboard(date_str, slot)

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)

# ─── Кнопка "Назад" в слоте — возврат к расписанию ──────────────────────────

@router.callback_query(F.data.startswith("view_back:"), F.from_user.id == ADMIN_ID)
async def view_back(callback: CallbackQuery):
    date_str = callback.data.split(":", 1)[1]
    await show_schedule(callback.message, date_str, edit=True)

# ─── Закрыть / удалить слот через кнопку ─────────────────────────────────────

@router.callback_query(F.data.startswith("close_slot:"), F.from_user.id == ADMIN_ID)
async def close_slot_inline(callback: CallbackQuery):
    parts = callback.data.split(":")
    date_str, time_str = parts[1], parts[2]
    await add_appointment(user_id=0, username="admin", full_name="⛔ Закрыто",
                          phone="—", service="Закрыто вручную", date=date_str, time=time_str)
    await callback.answer("Слот закрыт!")
    await show_schedule(callback.message, date_str, edit=True)

@router.callback_query(F.data.startswith("del_slot:"), F.from_user.id == ADMIN_ID)
async def delete_slot_inline(callback: CallbackQuery):
    parts = callback.data.split(":")
    date_str, time_str = parts[1], parts[2]
    await delete_time_slot(date_str, time_str)
    await callback.answer("Слот удалён!")
    await show_schedule(callback.message, date_str, edit=True)

# ─── ДОБАВЛЕНИЕ СЛОТОВ ────────────────────────────────────────────────────────

@router.message(F.text == "➕ Добавить слоты на дату", F.from_user.id == ADMIN_ID)
async def add_slots_pick_date(message: Message, state: FSMContext):
    await state.set_state(AdminState.add_picking_date)
    await message.answer("📅 <b>Выбери дату:</b>",
                         reply_markup=admin_date_picker_keyboard(prefix="adm_date"),
                         parse_mode="HTML")

@router.callback_query(AdminState.add_picking_date, F.data.startswith("adm_date:"), F.from_user.id == ADMIN_ID)
async def add_slots_date_chosen(callback: CallbackQuery, state: FSMContext):
    value = callback.data.split(":", 1)[1]
    if value == "manual":
        await state.set_state(AdminState.add_manual_date)
        await callback.message.edit_text("✏️ Введи дату: <b>ГГГГ-ММ-ДД</b>", parse_mode="HTML")
        return
    await _show_time_picker(callback.message, state, value, edit=True)

@router.message(AdminState.add_manual_date, F.from_user.id == ADMIN_ID)
async def add_slots_manual_date(message: Message, state: FSMContext):
    date_str = message.text.strip()
    try: datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        await message.answer("❗ Например: <code>2025-08-20</code>", parse_mode="HTML")
        return
    await _show_time_picker(message, state, date_str, edit=False)

async def _show_time_picker(msg, state: FSMContext, date_str: str, edit: bool):
    existing = await get_slots_by_date(date_str)
    await state.set_state(AdminState.add_picking_times)
    await state.update_data(add_date=date_str, selected_times=list(existing))
    text = (
        f"📅 Дата: <b>{date_str}</b>\n\n"
        f"⏰ <b>Выбери время</b> (нажимай — появится ✅)\n"
        f"Уже добавлено: <i>{', '.join(existing) if existing else 'нет'}</i>\n\n"
        f"Нажми <b>💾 Сохранить</b> когда выберешь всё."
    )
    kb = admin_time_picker_keyboard(existing)
    if edit:
        await msg.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await msg.answer(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(AdminState.add_picking_times, F.data.startswith("adm_time:"), F.from_user.id == ADMIN_ID)
async def add_slots_time_toggle(callback: CallbackQuery, state: FSMContext):
    value = callback.data.split(":", 1)[1]
    data = await state.get_data()
    date_str = data["add_date"]
    selected: list = data.get("selected_times", [])

    if value == "save":
        added, skipped = [], []
        for t in selected:
            ok = await add_time_slot(date_str, t)
            (added if ok else skipped).append(t)
        await state.clear()
        result = [f"📅 <b>Сохранено для {date_str}:</b>\n"]
        if added: result.append(f"✅ Добавлено: {', '.join(sorted(added))}")
        if skipped: result.append(f"⚠️ Уже были: {', '.join(sorted(skipped))}")
        if not added and not skipped: result.append("Ничего не выбрано.")
        await callback.message.edit_text("\n".join(result), parse_mode="HTML")
        await callback.message.answer("Меню расписания:", reply_markup=schedule_menu_keyboard())
        return

    if value == "manual":
        await state.set_state(AdminState.add_manual_time)
        await callback.message.answer("✏️ Введи время: <code>21:30</code>", parse_mode="HTML")
        await callback.answer()
        return

    if value in selected:
        selected.remove(value)
    else:
        selected.append(value)
    await state.update_data(selected_times=selected)
    await callback.message.edit_reply_markup(reply_markup=admin_time_picker_keyboard(selected))
    await callback.answer(f"{'✅' if value in selected else '☐'} {value}")

@router.message(AdminState.add_manual_time, F.from_user.id == ADMIN_ID)
async def add_slots_manual_time(message: Message, state: FSMContext):
    time_str = message.text.strip()
    try: datetime.strptime(time_str, "%H:%M")
    except ValueError:
        await message.answer("❗ Введи как <code>21:30</code>", parse_mode="HTML")
        return
    data = await state.get_data()
    date_str = data["add_date"]
    selected: list = data.get("selected_times", [])
    if time_str not in selected:
        selected.append(time_str)
    await state.update_data(selected_times=selected)
    await state.set_state(AdminState.add_picking_times)
    await message.answer(
        f"✅ Время <b>{time_str}</b> добавлено.\n\nНажми <b>💾 Сохранить</b> или выбери ещё:",
        reply_markup=admin_time_picker_keyboard(selected), parse_mode="HTML")

# ─── Удалить все слоты на дату ────────────────────────────────────────────────

@router.message(F.text == "🗑 Удалить все слоты на дату", F.from_user.id == ADMIN_ID)
async def schedule_delete_ask(message: Message, state: FSMContext):
    await state.set_state(AdminState.schedule_delete_date)
    await message.answer("📅 Введи дату: <b>ГГГГ-ММ-ДД</b>", parse_mode="HTML")

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
    await message.answer("📅 Введи дату: <b>ГГГГ-ММ-ДД</b>", parse_mode="HTML")

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
    await message.answer(f"Свободные слоты на <b>{date_str}</b>:\n{slots_str}\n\n"
                         f"Введи время: <code>14:00</code>", parse_mode="HTML")

@router.message(AdminState.close_slot_time, F.from_user.id == ADMIN_ID)
async def close_slot_do(message: Message, state: FSMContext):
    data = await state.get_data()
    date_str = data["close_date"]
    time_str = message.text.strip()
    try: datetime.strptime(time_str, "%H:%M")
    except ValueError:
        await message.answer("❗ Введи как <code>14:00</code>", parse_mode="HTML")
        return
    await state.clear()
    await add_appointment(user_id=0, username="admin", full_name="⛔ Закрыто",
                          phone="—", service="Закрыто вручную", date=date_str, time=time_str)
    await message.answer(f"🔒 Слот <b>{time_str}</b> на <b>{date_str}</b> закрыт.",
                         reply_markup=schedule_menu_keyboard(), parse_mode="HTML")

# ─── Карточка записи ─────────────────────────────────────────────────────────

async def send_appointment_card(bot: Bot, chat_id: int, appt, show_manage=False):
    emoji = STATUS_EMOJI.get(appt["status"], "❓")
    status_text = STATUS_RU.get(appt["status"], appt["status"])
    username_str = f"@{appt['username']}" if appt["username"] else "нет"
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

# ─── Подтвердить / отменить / удалить запись ─────────────────────────────────

@router.callback_query(F.data.startswith("admin_confirm:"), F.from_user.id == ADMIN_ID)
async def admin_confirm(callback: CallbackQuery, bot: Bot):
    appt_id = int(callback.data.split(":")[1])
    appt = await get_appointment_by_id(appt_id)
    if not appt:
        await callback.answer("Запись не найдена.", show_alert=True)
        return
    await update_appointment_status(appt_id, "confirmed")
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("✅ Подтверждено!")
    await callback.message.answer(f"✅ Запись <b>#{appt_id}</b> подтверждена.", parse_mode="HTML")
    if appt["user_id"] != 0:
        await bot.send_message(appt["user_id"],
            f"✅ <b>Ваша запись подтверждена!</b>\n\n"
            f"✂️ {appt['service']}\n📅 {appt['date']} в {appt['time']}\n\n"
            f"📍 Ждём вас по адресу: <b>ул. Астраханская 19</b> 💈", parse_mode="HTML")

@router.callback_query(F.data.startswith("admin_cancel:"), F.from_user.id == ADMIN_ID)
async def admin_cancel(callback: CallbackQuery, bot: Bot):
    appt_id = int(callback.data.split(":")[1])
    appt = await get_appointment_by_id(appt_id)
    if not appt:
        await callback.answer("Запись не найдена.", show_alert=True)
        return
    await update_appointment_status(appt_id, "cancelled")
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("❌ Отменено!")
    await callback.message.answer(f"❌ Запись <b>#{appt_id}</b> отменена.", parse_mode="HTML")
    if appt["user_id"] != 0:
        await bot.send_message(appt["user_id"],
            f"❌ <b>Ваша запись отменена.</b>\n\n"
            f"✂️ {appt['service']}\n📅 {appt['date']} в {appt['time']}\n\n"
            f"Запишитесь на другое время.", parse_mode="HTML")

@router.callback_query(F.data.startswith("admin_delete:"), F.from_user.id == ADMIN_ID)
async def admin_delete(callback: CallbackQuery):
    appt_id = int(callback.data.split(":")[1])
    appt = await get_appointment_by_id(appt_id)
    await delete_appointment(appt_id)
    await callback.answer("🗑 Удалено!")
    # Если удаляем из просмотра расписания — возвращаемся к расписанию
    if appt:
        import re
        match = re.search(r"(\d{4}-\d{2}-\d{2})", callback.message.text)
        if match:
            await show_schedule(callback.message, match.group(1), edit=True)
            return
    await callback.message.edit_text(
        callback.message.text + "\n\n<i>🗑 Удалено</i>", parse_mode="HTML", reply_markup=None)
