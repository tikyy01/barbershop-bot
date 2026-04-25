from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import CommandStart

from config import ADMIN_ID, PHONE_NUMBER, BARBERSHOP_NAME
from database import (
    add_appointment, get_booked_times, get_user_appointments,
    update_appointment_status, get_free_slots, get_dates_with_slots
)
from keyboards import (
    client_main_menu, services_keyboard, available_dates_keyboard,
    free_times_keyboard, contact_keyboard, confirm_keyboard,
    cancel_appointment_keyboard, SERVICE_LABELS
)

router = Router()

STATUS_EMOJI = {
    "pending": "⏳",
    "confirmed": "✅",
    "cancelled": "❌"
}

STATUS_RU = {
    "pending": "Ожидает подтверждения",
    "confirmed": "Подтверждена",
    "cancelled": "Отменена"
}

class BookingState(StatesGroup):
    service = State()
    date = State()
    time = State()
    phone = State()
    confirm = State()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    name = message.from_user.first_name
    await message.answer(
        f"👋 Привет, {name}!\n\n"
        f"Добро пожаловать в <b>{BARBERSHOP_NAME}</b>!\n\n"
        f"Здесь ты можешь записаться на стрижку онлайн.\n"
        f"После записи мы перезвоним тебе для подтверждения.",
        reply_markup=client_main_menu(),
        parse_mode="HTML"
    )

@router.message(F.text == "📋 Мои записи")
async def my_appointments(message: Message):
    appointments = await get_user_appointments(message.from_user.id)
    if not appointments:
        await message.answer("У тебя пока нет записей. Нажми «✂️ Записаться»!")
        return
    for appt in appointments:
        emoji = STATUS_EMOJI.get(appt["status"], "❓")
        status_text = STATUS_RU.get(appt["status"], appt["status"])
        text = (
            f"{emoji} <b>Запись #{appt['id']}</b>\n"
            f"📅 {appt['date']} в {appt['time']}\n"
            f"✂️ {appt['service']}\n"
            f"📞 {appt['phone']}\n"
            f"Статус: {status_text}"
        )
        if appt["status"] in ("pending", "confirmed"):
            await message.answer(text, parse_mode="HTML",
                                 reply_markup=cancel_appointment_keyboard(appt["id"]))
        else:
            await message.answer(text, parse_mode="HTML")

@router.message(F.text == "✂️ Записаться")
async def start_booking(message: Message, state: FSMContext):
    await state.set_state(BookingState.service)
    await message.answer(
        "💈 <b>Выбери услугу:</b>",
        reply_markup=services_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(BookingState.service, F.data.startswith("s:"))
async def choose_service(callback: CallbackQuery, state: FSMContext):
    service_id = callback.data.split(":", 1)[1]
    service = SERVICE_LABELS.get(service_id, service_id)
    await state.update_data(service=service)
    await state.set_state(BookingState.date)

    dates = await get_dates_with_slots()
    if not dates:
        await callback.message.edit_text(
            "😔 К сожалению, свободных дат пока нет.\n"
            "Попробуй позже или позвони нам напрямую.",
            reply_markup=None
        )
        await state.clear()
        return

    await callback.message.edit_text(
        f"✅ Услуга: <b>{service}</b>\n\n📅 <b>Выбери дату:</b>",
        reply_markup=available_dates_keyboard(dates),
        parse_mode="HTML"
    )

@router.callback_query(BookingState.date, F.data.startswith("date:"))
async def choose_date(callback: CallbackQuery, state: FSMContext):
    date = callback.data.split(":", 1)[1]
    await state.update_data(date=date)

    free_slots = await get_free_slots(date)
    if not free_slots:
        await callback.answer("На эту дату нет свободного времени.", show_alert=True)
        return

    await state.set_state(BookingState.time)
    await callback.message.edit_text(
        f"📅 Дата: <b>{date}</b>\n\n🕐 <b>Выбери время:</b>",
        reply_markup=free_times_keyboard(free_slots),
        parse_mode="HTML"
    )

@router.callback_query(BookingState.time, F.data.startswith("time:"))
async def choose_time(callback: CallbackQuery, state: FSMContext):
    time = callback.data.split(":", 1)[1]
    await state.update_data(time=time)
    await state.set_state(BookingState.phone)
    await callback.message.delete()
    await callback.message.answer(
        f"🕐 Время: <b>{time}</b>\n\n"
        f"📱 <b>Поделись своим номером телефона</b>\n"
        f"Нажми кнопку ниже или введи вручную:",
        reply_markup=contact_keyboard(),
        parse_mode="HTML"
    )

@router.message(BookingState.phone, F.contact)
async def got_contact(message: Message, state: FSMContext):
    phone = message.contact.phone_number
    if not phone.startswith("+"):
        phone = "+" + phone
    await process_phone(message, state, phone)

@router.message(BookingState.phone, F.text)
async def got_phone_text(message: Message, state: FSMContext):
    phone = message.text.strip()
    if not any(c.isdigit() for c in phone) or len(phone) < 7:
        await message.answer("❗ Введи корректный номер телефона.")
        return
    await process_phone(message, state, phone)

async def process_phone(message: Message, state: FSMContext, phone: str):
    await state.update_data(phone=phone)
    data = await state.get_data()
    await state.set_state(BookingState.confirm)
    await message.answer(
        f"📋 <b>Проверь данные записи:</b>\n\n"
        f"✂️ Услуга: <b>{data['service']}</b>\n"
        f"📅 Дата: <b>{data['date']}</b>\n"
        f"🕐 Время: <b>{data['time']}</b>\n"
        f"📞 Телефон: <b>{phone}</b>\n\n"
        f"Всё верно?",
        reply_markup=confirm_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(BookingState.confirm, F.data == "confirm_booking")
async def confirm_booking(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    user = callback.from_user

    appt_id = await add_appointment(
        user_id=user.id,
        username=user.username or "",
        full_name=user.full_name,
        phone=data["phone"],
        service=data["service"],
        date=data["date"],
        time=data["time"]
    )

    await state.clear()

    await callback.message.edit_text(
        f"🎉 <b>Ты записан!</b>\n\n"
        f"✂️ {data['service']}\n"
        f"📅 {data['date']} в {data['time']}\n"
        f"📞 Мы перезвоним на <b>{data['phone']}</b> для подтверждения.\n\n"
        f"📍 Ждём вас по адресу: <b>ул. Астраханская 19</b>",
        parse_mode="HTML",
        reply_markup=None
    )
    await callback.message.answer("Главное меню:", reply_markup=client_main_menu())

    username_str = f"@{user.username}" if user.username else "нет username"
    admin_text = (
        f"🔔 <b>Новая запись #{appt_id}!</b>\n\n"
        f"👤 Клиент: <b>{user.full_name}</b> ({username_str})\n"
        f"📞 Телефон: <b>{data['phone']}</b>\n"
        f"✂️ Услуга: <b>{data['service']}</b>\n"
        f"📅 Дата: <b>{data['date']}</b>\n"
        f"🕐 Время: <b>{data['time']}</b>\n\n"
        f"📲 Нужно перезвонить клиенту для подтверждения!"
    )
    from keyboards import appointment_manage_keyboard
    await bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML",
                           reply_markup=appointment_manage_keyboard(appt_id))

@router.callback_query(BookingState.confirm, F.data == "cancel_booking")
async def cancel_booking_step(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Запись отменена.", reply_markup=None)
    await callback.message.answer("Главное меню:", reply_markup=client_main_menu())

@router.callback_query(F.data.startswith("client_cancel:"))
async def client_cancel_appointment(callback: CallbackQuery, bot: Bot):
    appt_id = int(callback.data.split(":")[1])
    from database import get_appointment_by_id
    appt = await get_appointment_by_id(appt_id)

    if not appt or appt["user_id"] != callback.from_user.id:
        await callback.answer("❗ Запись не найдена.", show_alert=True)
        return

    if appt["status"] == "cancelled":
        await callback.answer("Запись уже отменена.", show_alert=True)
        return

    await update_appointment_status(appt_id, "cancelled")
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(f"❌ Запись #{appt_id} отменена.")

    await bot.send_message(
        ADMIN_ID,
        f"⚠️ Клиент <b>{callback.from_user.full_name}</b> отменил запись <b>#{appt_id}</b>\n"
        f"📅 {appt['date']} в {appt['time']} — {appt['service']}",
        parse_mode="HTML"
    )
