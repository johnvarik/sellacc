import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import random
from database import Database

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Токен бота
API_TOKEN = '8377914455:AAECZpNv-XsRpgYg7i-EHFVRqdRy1FMzCwg'

# ID админов (укажите свой ID через запятую)
ADMIN_IDS = [8531708928]  # ЗАМЕНИТЕ НА СВОЙ ID!

# Ссылка на фото для профиля
PROFILE_PHOTO_URL = "https://i.yapx.ru/coj0i.png"

# Ссылка на инструкцию
INSTRUCTION_PHOTO_URL = "https://i.yapx.ru/coj3Q.png"

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Инициализация базы данных
db = Database()


# Класс для состояний
class Form(StatesGroup):
    waiting_for_promo = State()
    waiting_for_games = State()
    waiting_for_payment_confirmation = State()
    waiting_for_account_email = State()
    waiting_for_account_password = State()
    waiting_for_account_games = State()
    waiting_for_delete_account_id = State()
    waiting_for_broadcast_message = State()
    waiting_for_broadcast_confirmation = State()


# Функция для логирования действий и отправки админам
async def log_action(user_id: int, action: str, details: str = ""):
    """Логирование действий в базу и отправка админам"""
    db.add_log(user_id, action, details)

    # Получаем информацию о пользователе для логина
    user_data = db.get_user(user_id)
    username = user_data[0] if user_data else "Неизвестный"

    # Формируем ссылку на пользователя
    user_link = f"[{username}](tg://user?id={user_id})" if user_id else f"ID: {user_id}"

    # Формируем сообщение для админов
    log_message = f"📋 **Лог:** {action}\n👤 Пользователь: {user_link}\n"

    if details:
        log_message += f"📝 Детали: {details}\n"

    log_message += f"🕐 Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    # Отправляем логи всем админам
    admins = db.get_admins()
    for admin_id, _ in admins:
        try:
            await bot.send_message(admin_id, log_message, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Не удалось отправить лог админу {admin_id}: {e}")


# Функция проверки админа
def is_admin(user_id: int) -> bool:
    # Проверяем в списке админов
    if user_id in ADMIN_IDS:
        return True

    # Проверяем в базе данных
    user_data = db.get_user(user_id)
    return bool(user_data and user_data[2] == 1)  # is_admin поле


# ========== КЛАВИАТУРЫ ==========

# Главное меню
def get_main_menu():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎮 Выбрать аккаунт")],
            [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="⭐ Отзывы")],
            [KeyboardButton(text="📱 Инструкция по входу")]
        ],
        resize_keyboard=True
    )
    return keyboard


# Профиль клавиатура
def get_profile_menu():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Пополнить баланс", url="https://t.me/kris_moew")],
            [InlineKeyboardButton(text="🎁 Промокод", callback_data="promocode")],
            [InlineKeyboardButton(text="📜 Мои промокоды", callback_data="my_promocodes")],
            [InlineKeyboardButton(text="📱 Инструкция по входу", callback_data="show_instruction")],
            [InlineKeyboardButton(text="↩️ Вернуться в меню", callback_data="back_to_menu")]
        ]
    )
    return keyboard


# Админ меню
def get_admin_menu():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton(text="🎁 Создать промокод", callback_data="admin_create_promo")],
            [InlineKeyboardButton(text="🎁 Управление промокодами", callback_data="admin_promocodes")],
            [InlineKeyboardButton(text="👤 Добавить админа", callback_data="admin_add_admin")],
            [InlineKeyboardButton(text="💰 Изменить баланс", callback_data="admin_set_balance")],
            [InlineKeyboardButton(text="📦 История покупок", callback_data="admin_purchases")],
            [InlineKeyboardButton(text="📱 Управление аккаунтами", callback_data="admin_accounts")],
            [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
            [InlineKeyboardButton(text="📋 Последние логи", callback_data="admin_logs")],
            [InlineKeyboardButton(text="🔙 В меню", callback_data="back_to_menu")]
        ]
    )
    return keyboard


# Меню управления аккаунтами
def get_accounts_menu():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить аккаунт", callback_data="admin_add_account")],
            [InlineKeyboardButton(text="📋 Список аккаунтов", callback_data="admin_list_accounts")],
            [InlineKeyboardButton(text="🗑️ Удалить аккаунт", callback_data="admin_delete_account")],
            [InlineKeyboardButton(text="🔙 В админ-панель", callback_data="back_to_admin")]
        ]
    )
    return keyboard


# Клавиатура для рассылки
def get_broadcast_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Отправить всем", callback_data="broadcast_send_all")],
            [InlineKeyboardButton(text="📊 Только статистика", callback_data="broadcast_stats_only")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="broadcast_cancel")]
        ]
    )
    return keyboard


# Клавиатура подтверждения рассылки
def get_broadcast_confirmation_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить отправку", callback_data="confirm_broadcast")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_broadcast")]
        ]
    )
    return keyboard


# Клавиатура для оплаты
def get_payment_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Оплатить 400 руб.", callback_data="confirm_payment")],
            [InlineKeyboardButton(text="❌ Отказаться", callback_data="cancel_payment")]
        ]
    )
    return keyboard


# ========== ОБРАБОТЧИКИ КОМАНД ==========

# Обработчик команды /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name

    # Добавляем пользователя в БД если его нет
    db.add_user(user_id, username)

    # Проверяем, является ли пользователь админом
    if is_admin(user_id):
        db.set_user_admin(user_id, True)

    # Логируем вход
    await log_action(user_id, "Новый вход", f"Пользователь: {username}")

    # Приветственное сообщение
    welcome_text = f"👋 Доброго времени суток, {username}!\n\n🎮 Это бот по продаже аккаунтов с играми на iOS.\n\n👇 Ниже выбери, куда ты хочешь перейти!"

    await message.answer(
        text=welcome_text,
        reply_markup=get_main_menu()
    )


# Обработчик кнопки "Инструкция по входу"
@dp.message(lambda message: message.text == "📱 Инструкция по входу")
async def show_instruction_message(message: types.Message):
    """Показать инструкцию по входу (из главного меню)"""
    await show_instruction_handler(message)


# Обработчик инлайн кнопки "Инструкция по входу"
@dp.callback_query(lambda c: c.data == "show_instruction")
async def show_instruction_callback(callback_query: types.CallbackQuery):
    """Показать инструкцию по входу (из профиля)"""
    await callback_query.answer()
    await show_instruction_handler(callback_query.message)


async def show_instruction_handler(message_source):
    """Общий обработчик инструкции"""
    instruction_text = (
        "📱 <b>ИНСТРУКЦИЯ ПО ВХОДУ В АККАУНТ APPLE ID</b>\n\n"

        "⚠️ <b>ВАЖНОЕ ЗАМЕЧАНИЕ:</b>\n"
        "В связи нововведением Apple о моментальной блокировке аккаунтов, на которых входит множество людей с разных устройств и IP-адресов, мы выдаем аккаунты по другой инструкции, дабы их не блокировали и вы могли пользоваться ими.\n\n"

        "🔑 <b>ПРАВИЛЬНЫЙ ВХОД:</b>\n"
        "1. Откройте <b>Настройки</b> на вашем iPhone/iPad\n"
        "2. В самом верху нажмите на свой Apple ID\n"
        "3. Прокрутите вниз и выберите <b>«Выйти»</b>\n"
        "4. После выхода вернитесь в <b>Настройки</b>\n"
        "5. Нажмите <b>«Войти»</b> вверху экрана\n"
        "6. Введите email и пароль из купленного аккаунта\n"
        "7. При запросе двухфакторной аутентификации - пропустите\n"
        "8. Подтвердите вход\n\n"

        "📱 <b>ЗАПУСК ИГР:</b>\n"
        "1. После входа в App Store НЕ входите!\n"
        "2. Откройте <b>App Store</b>\n"
        "3. Нажмите на иконку профиля вверху справа\n"
        "4. Прокрутите вниз до раздела <b>«Покупки»</b>\n"
        "5. Там будут все игры, купленные на этот аккаунт\n"
        "6. Нажмите на облачко ⬇️ рядом с игрой для загрузки\n\n"

        "🚫 <b>ЧТО НЕЛЬЗЯ ДЕЛАТЬ:</b>\n"
        "• Входить через App Store напрямую\n"
        "• Использовать аккаунт на нескольких устройствах одновременно\n"
        "• Менять пароль или данные аккаунта\n"
        "• Включать двухфакторную аутентификацию\n\n"

        "📞 <b>ПОДДЕРЖКА:</b>\n"
        "Если возникли проблемы с входом или игры не отображаются, обратитесь в поддержку: @kris_moew"
    )

    try:
        # Отправляем фото инструкции
        await message_source.answer_photo(
            photo=INSTRUCTION_PHOTO_URL,
            caption="📱 <b>НАГЛЯДНАЯ ИНСТРУКЦИЯ ПО ВХОДУ:</b>",
            parse_mode="HTML"
        )

        # Отправляем текстовую инструкцию
        await message_source.answer(
            text=instruction_text,
            parse_mode="HTML"
        )

    except Exception as e:
        # Если фото не загрузилось, отправляем только текст
        logger.error(f"Ошибка при отправке фото: {e}")
        await message_source.answer(
            text=instruction_text,
            parse_mode="HTML"
        )


# Команда админ панели
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    user_id = message.from_user.id

    if not is_admin(user_id):
        await message.answer("❌ У вас нет прав администратора!")
        return

    admin_text = "👑 Панель администратора\n\nВыберите действие:"

    await message.answer(
        text=admin_text,
        reply_markup=get_admin_menu()
    )


# Обработчик кнопки "Профиль" (С ФОТО ПРОФИЛЯ)
@dp.message(lambda message: message.text == "👤 Профиль")
async def show_profile(message: types.Message):
    user_id = message.from_user.id

    # Получаем данные пользователя
    user_data = db.get_user(user_id)

    if user_data:
        username, balance, is_admin_flag = user_data

        # Добавляем статус админа в профиль
        admin_status = "👑 Администратор" if is_admin_flag == 1 else "👤 Пользователь"

        profile_text = (
            f"👤 <b>Ваш профиль:</b>\n\n"
            f"📛 <b>Ваше имя:</b> {username}\n"
            f"{admin_status}\n"
            f"💰 <b>Баланс:</b> {balance} руб.\n\n"
            f"👇 <b>Выберите действие:</b>"
        )

        try:
            # Пробуем отправить с фото профиля
            await message.answer_photo(
                photo=PROFILE_PHOTO_URL,
                caption=profile_text,
                reply_markup=get_profile_menu(),
                parse_mode="HTML"
            )
        except Exception as e:
            # Если фото не загрузилось, отправляем только текст
            logger.error(f"Ошибка при отправке фото профиля: {e}")
            await message.answer(
                text=profile_text,
                reply_markup=get_profile_menu(),
                parse_mode="HTML"
            )
    else:
        await message.answer("❌ Профиль не найден!")


# Обработчик кнопки "Отзывы"
@dp.message(lambda message: message.text == "⭐ Отзывы")
async def show_reviews(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Перейти к отзывам", url="https://t.me/otzivi_gam")]
        ]
    )
    await message.answer("Нажмите на кнопку ниже, чтобы перейти к отзывам:", reply_markup=keyboard)


# Обработчик кнопки "Выбрать аккаунт"
@dp.message(lambda message: message.text == "🎮 Выбрать аккаунт")
async def choose_account(message: types.Message, state: FSMContext):
    await message.answer(
        "🎮 <b>Поиск аккаунта</b>\n\n"
        "Введите названия игр (до 3 штук), которые вы хотите найти в одном аккаунте.\n"
        "Например: <i>Call of Duty, PUBG, Genshin Impact</i>\n\n"
        "📝 <b>Вводите игры через запятую</b>",
        parse_mode="HTML"
    )
    await state.set_state(Form.waiting_for_games)


# Обработчик ввода игр
@dp.message(Form.waiting_for_games)
async def process_games_input(message: types.Message, state: FSMContext):
    games = message.text.strip()

    if len(games) < 3:
        await message.answer("❌ Пожалуйста, введите названия игр (минимум 3 символа)")
        return

    await state.update_data(games=games)

    # Сообщение о начале поиска
    search_msg = await message.answer("🔍 <b>Ищем подходящий аккаунт...</b>", parse_mode="HTML")

    # Имитация поиска в течение 10 секунд
    await asyncio.sleep(3)
    await search_msg.edit_text("🔍 <b>Ищем подходящий аккаунт...</b>\n\n📊 Проверяем базу данных...", parse_mode="HTML")
    await asyncio.sleep(3)
    await search_msg.edit_text(
        "🔍 <b>Ищем подходящий аккаунт...</b>\n\n📊 Проверяем базу данных...\n✅ Находим совпадения...", parse_mode="HTML")
    await asyncio.sleep(4)

    # Удаляем сообщение о поиска
    await search_msg.delete()

    # Ищем случайный аккаунт в базе данных
    account = db.get_random_account(games)

    if not account:
        # Если нет подходящего аккаунта, берем любой
        account = db.get_random_account()

    if account:
        account_id, email, password, account_games = account
        await state.update_data(account_id=account_id, email=email, password=password)

        # Сообщение о найденном аккаунте
        result_text = (
            f"✅ <b>Аккаунт найден!</b>\n\n"
            f"🎮 <b>Запрошенные игры:</b> {games}\n"
            f"🎲 <b>Игры на аккаунте:</b> {account_games if account_games else 'Не указаны'}\n"
            f"💰 <b>Стоимость:</b> 400 руб.\n\n"
            f"📱 <b>Данные аккаунта будут высланы после оплаты</b>\n\n"
            f"👇 <b>Выберите действие:</b>"
        )
    else:
        await message.answer("❌ Извините, в данный момент нет доступных аккаунтов. Попробуйте позже.")
        await state.clear()
        return

    await message.answer(
        text=result_text,
        reply_markup=get_payment_keyboard(),
        parse_mode="HTML"
    )


# ========== ОБРАБОТЧИКИ ПРОМОКОДОВ ==========

# Обработчик кнопки "Промокод"
@dp.callback_query(lambda c: c.data == "promocode")
async def process_promocode_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик нажатия на кнопку 'Промокод'"""
    await callback_query.answer()

    # Получаем историю использования промокодов пользователем
    user_id = callback_query.from_user.id

    await callback_query.message.answer("Введите промокод:")
    await state.set_state(Form.waiting_for_promo)


# Обработчик кнопки "Мои промокоды"
@dp.callback_query(lambda c: c.data == "my_promocodes")
async def my_promocodes_callback(callback_query: types.CallbackQuery):
    """Обработчик нажатия на кнопку 'Мои промокоды'"""
    await callback_query.answer()

    user_id = callback_query.from_user.id

    # Получаем историю использования промокодов пользователем
    promo_history = db.get_user_promocode_history(user_id, 20)

    if not promo_history:
        await callback_query.message.answer("📭 Вы еще не использовали ни одного промокода")
        return

    promo_list = "📜 <b>Ваша история промокодов:</b>\n\n"
    total_amount = 0

    for promo_code, amount, used_date in promo_history:
        promo_list += f"🔹 <b>{promo_code}</b>\n"
        promo_list += f"   💰 +{amount} руб.\n"
        promo_list += f"   📅 {used_date}\n"
        promo_list += "   ──────────────\n"
        total_amount += amount

    promo_list += f"\n💰 <b>Всего получено с промокодов:</b> {total_amount} руб."

    await callback_query.message.answer(promo_list, parse_mode="HTML")


# Обработчик ввода промокода
@dp.message(Form.waiting_for_promo)
async def process_promocode(message: types.Message, state: FSMContext):
    promocode = message.text.strip().upper()
    user_id = message.from_user.id

    # Используем промокод (проверка валидности внутри метода use_promocode)
    success, result = db.use_promocode(promocode, user_id)

    if success:
        amount = result

        # Получаем старый баланс
        user_data = db.get_user(user_id)
        old_balance = user_data[1] if user_data else 0

        # Обновляем баланс пользователя
        db.update_user_balance(user_id, amount)

        # Получаем новый баланс
        new_user_data = db.get_user(user_id)
        new_balance = new_user_data[1]

        # Получаем данные промокода для информации
        promo_data = db.get_promocode(promocode)
        if promo_data:
            _, used_count, use_limit, valid_until = promo_data

            # Формируем информацию о промокоде
            usage_info = f"🔄 Использовано: {used_count}"
            if use_limit > 0:
                usage_info += f"/{use_limit}"
            else:
                usage_info += " (безлимитный)"

        # Логируем активацию промокода
        await log_action(user_id, "Активирован промокод",
                         f"Код: {promocode} | Сумма: +{amount} руб. | Баланс был: {old_balance}, стал: {new_balance}")

        response_text = (
            f"✅ <b>Промокод активирован!</b>\n\n"
            f"💎 <b>На ваш баланс зачислено:</b> {amount} руб.\n"
            f"💰 <b>Новый баланс:</b> {new_balance} руб.\n"
            f"📝 <b>Промокод:</b> {promocode}\n"
        )

        if promo_data:
            response_text += f"📊 <b>Использование промокода:</b> {used_count}"
            if use_limit > 0:
                response_text += f"/{use_limit}"
            else:
                response_text += " (безлимитный)"

        await message.answer(response_text, parse_mode="HTML")

    else:
        # result содержит сообщение об ошибке
        await message.answer(f"❌ {result}")

    await state.clear()


# ========== ОБРАБОТЧИК ПОДТВЕРЖДЕНИЯ ОПЛАТЫ ==========

@dp.callback_query(lambda c: c.data == "confirm_payment")
async def confirm_payment(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()

    user_id = callback_query.from_user.id

    # Получаем данные из состояния
    data = await state.get_data()
    games = data.get('games')
    account_id = data.get('account_id')
    email = data.get('email')
    password = data.get('password')

    # Проверяем баланс пользователя
    user_data = db.get_user(user_id)

    if not user_data:
        await callback_query.message.answer("❌ Ошибка: пользователь не найден")
        await state.clear()
        return

    balance = user_data[1]  # balance поле

    if balance < 400:
        await callback_query.message.answer(
            f"❌ <b>Недостаточно средств!</b>\n\n"
            f"💰 <b>Текущий баланс:</b> {balance} руб.\n"
            f"💵 <b>Требуется:</b> 400 руб.\n\n"
            f"Пополните баланс через профиль.",
            parse_mode="HTML"
        )
        return

    # Списываем средства
    db.update_user_balance(user_id, -400)

    # Сохраняем покупку в БД
    account_data = f"Email: {email}\nPassword: {password}"
    db.add_purchase(user_id, games, 400, account_id, account_data)

    # Получаем новый баланс
    new_user_data = db.get_user(user_id)
    new_balance = new_user_data[1]

    # Форматируем данные аккаунта для копирования
    account_info = (
        f"✅ <b>ОПЛАТА ПРОШЛА УСПЕШНО!</b>\n\n"
        f"🎮 <b>Купленные игры:</b> {games}\n"
        f"💰 <b>Списано:</b> 400 руб.\n"
        f"💳 <b>Остаток баланса:</b> {new_balance} руб.\n\n"
        f"🔐 <b>ДАННЫЕ АККАУНТА:</b>\n\n"
        f"📧 <b>Email:</b>\n<code>{email}</code>\n\n"
        f"🔑 <b>Пароль:</b>\n<code>{password}</code>\n\n"
        f"⚠️ <b>СОХРАНИТЕ ЭТИ ДАННЫЕ В НАДЕЖНОМ МЕСТЕ!</b>\n\n"
    )

    # Логируем покупку
    await log_action(user_id, "Покупка аккаунта",
                     f"Аккаунт #{account_id} | Игры: {games} | Цена: 400 руб.")

    # Отправляем данные аккаунта
    await callback_query.message.edit_text(
        text=account_info,
        parse_mode="HTML"
    )

    # ОТДЕЛЬНО ОТПРАВЛЯЕМ ВАЖНУЮ ИНФОРМАЦИЮ С БОЛЬШИМ АКЦЕНТОМ
    important_info = (
        f"🚨 <b>ВНИМАНИЕ! ВАЖНАЯ ИНФОРМАЦИЯ!</b>\n\n"
        f"⚠️ <b>В связи нововведением Apple о моментальной блокировке аккаунтов, на которых входит множество людей с разных устройств и IP-адресов, мы выдаем аккаунты по другой инструкции, дабы их не блокировали и вы могли пользоваться ими.</b>\n\n"
        f"📱 <b>ПРАВИЛЬНЫЙ ВХОД (ОБЯЗАТЕЛЬНО!):</b>\n"
        f"1. Откройте <b>Настройки</b> → вверху нажмите на свой Apple ID → <b>«Выйти»</b>\n"
        f"2. Вернитесь в <b>Настройки</b> → нажмите <b>«Войти»</b> вверху экрана\n"
        f"3. Введите данные из купленного аккаунта\n\n"
        f"🚫 <b>НЕЛЬЗЯ:</b>\n"
        f"• Входить через App Store напрямую\n"
        f"• Если вы входите через App Store, то синхронизация не пройдет и игр не будет!\n\n"
        f"🔑 <b>ПОСЛЕ ВХОДА:</b>\n"
        f"1. Откройте <b>App Store</b> → иконка профиля вверху справа\n"
        f"2. Прокрутите вниз до раздела <b>«Покупки»</b>\n"
        f"3. Там будут все игры, нажмите ⬇️ для загрузки\n\n"
        f"📞 <b>Если возникнут проблемы - пишите:</b> @kris_moew"
    )

    await callback_query.message.answer(
        text=important_info,
        parse_mode="HTML"
    )

    # Отправляем фото инструкции
    try:
        await callback_query.message.answer_photo(
            photo=INSTRUCTION_PHOTO_URL,
            caption="📱 <b>НАГЛЯДНАЯ ИНСТРУКЦИЯ ПО ВХОДУ (СОХРАНИТЕ!):</b>",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке фото инструкции: {e}")
        await callback_query.message.answer(
            "📱 <b>Инструкция по входу доступна в меню бота</b>",
            parse_mode="HTML"
        )

    await state.clear()


# Обработчик отказа от оплаты
@dp.callback_query(lambda c: c.data == "cancel_payment")
async def cancel_payment(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()

    await callback_query.message.edit_text(
        text="❌ Вы отказались от покупки.\n\nВозвращаемся в главное меню..."
    )

    # Возвращаем в меню через 1 секунду
    await asyncio.sleep(1)

    username = callback_query.from_user.username or callback_query.from_user.first_name
    welcome_text = f"👋 Доброго времени суток, {username}!\n\n🎮 Это бот по продаже аккаунтов с играми на iOS.\n\n👇 Ниже выбери, куда ты хочешь перейти!"

    await callback_query.message.answer(
        text=welcome_text,
        reply_markup=get_main_menu()
    )

    await state.clear()


# ========== ОБРАБОТЧИКИ РАССЫЛКИ ==========

# Обработчик нажатия на кнопку "Рассылка"
@dp.callback_query(lambda c: c.data == "admin_broadcast")
async def admin_broadcast(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()

    user_id = callback_query.from_user.id

    if not is_admin(user_id):
        await callback_query.message.answer("❌ У вас нет прав администратора!")
        return

    # Получаем статистику
    total_users = db.get_users_count()

    broadcast_text = (
        f"📢 <b>Рассылка сообщений</b>\n\n"
        f"👥 Всего пользователей в базе: {total_users}\n\n"
        f"Выберите тип рассылки:"
    )

    await callback_query.message.answer(
        text=broadcast_text,
        reply_markup=get_broadcast_keyboard(),
        parse_mode="HTML"
    )


# Обработчик кнопки "Отправить всем"
@dp.callback_query(lambda c: c.data == "broadcast_send_all")
async def broadcast_send_all(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()

    await callback_query.message.answer(
        "📝 <b>Введите сообщение для рассылки:</b>\n\n"
        "Вы можете использовать HTML разметку:\n"
        "- <b>жирный</b>\n"
        "- <i>курсив</i>\n"
        "- <code>код</code>\n"
        "- <a href='ссылка'>текст</a>",
        parse_mode="HTML"
    )
    await state.set_state(Form.waiting_for_broadcast_message)


# Обработчик кнопки "Только статистика"
@dp.callback_query(lambda c: c.data == "broadcast_stats_only")
async def broadcast_stats_only(callback_query: types.CallbackQuery):
    await callback_query.answer()

    # Получаем статистику
    stats = db.get_statistics()

    stats_message = (
        f"📊 <b>Статистика бота:</b>\n\n"
        f"👥 Всего пользователей: {stats['total_users']}\n"
        f"🛒 Всего покупок: {stats['total_purchases']}\n"
        f"💰 Общая выручка: {stats['total_revenue']} руб.\n"
        f"📱 Всего аккаунтов: {stats['total_accounts']}\n\n"
        f"🎮 <i>Бот работает стабильно!</i>"
    )

    await callback_query.message.answer(
        f"📝 <b>Сообщение для рассылки:</b>\n\n{stats_message}\n\n"
        f"👥 Будет отправлено: {stats['total_users']} пользователям\n\n"
        f"<b>Подтвердить отправку?</b>",
        reply_markup=get_broadcast_confirmation_keyboard(),
        parse_mode="HTML"
    )

    # Сохраняем сообщение в состоянии
    from aiogram.fsm.context import FSMContext
    context = FSMContext(storage=storage, key=callback_query.from_user.id)
    await context.update_data(broadcast_message=stats_message)


# Обработчик ввода сообщения для рассылки
@dp.message(Form.waiting_for_broadcast_message)
async def process_broadcast_message(message: types.Message, state: FSMContext):
    broadcast_message = message.text
    total_users = db.get_users_count()

    await state.update_data(broadcast_message=broadcast_message)

    preview_text = (
        f"📝 <b>Сообщение для рассылки:</b>\n\n"
        f"{broadcast_message}\n\n"
        f"👥 Будет отправлено: {total_users} пользователям\n\n"
        f"<b>Подтвердить отправку?</b>"
    )

    await message.answer(
        text=preview_text,
        reply_markup=get_broadcast_confirmation_keyboard(),
        parse_mode="HTML"
    )


# Обработчик подтверждения рассылки
@dp.callback_query(lambda c: c.data == "confirm_broadcast")
async def confirm_broadcast(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()

    user_id = callback_query.from_user.id

    # Получаем сообщение из состояния
    data = await state.get_data()
    broadcast_message = data.get('broadcast_message', '')

    if not broadcast_message:
        await callback_query.message.answer("❌ Ошибка: сообщение не найдено")
        await state.clear()
        return

    # Получаем всех пользователей
    users = db.get_all_users()
    total_users = len(users)

    # Отправляем сообщение о начале рассылки
    status_msg = await callback_query.message.answer(f"🔄 Начинаю рассылку...\nОтправлено: 0/{total_users}")

    # Счетчики
    sent_count = 0
    failed_count = 0
    blocked_count = 0

    # Рассылаем сообщение всем пользователям
    for user_id_db, username in users:
        try:
            await bot.send_message(
                user_id_db,
                broadcast_message,
                parse_mode="HTML"
            )
            sent_count += 1

            # Обновляем статус каждые 10 сообщений
            if sent_count % 10 == 0:
                await status_msg.edit_text(
                    f"🔄 Рассылка в процессе...\n"
                    f"Отправлено: {sent_count}/{total_users}\n"
                    f"Не удалось: {failed_count}\n"
                    f"Заблокировали: {blocked_count}"
                )

            # Небольшая задержка, чтобы не превысить лимиты Telegram
            await asyncio.sleep(0.1)

        except Exception as e:
            error_msg = str(e)
            if "bot was blocked" in error_msg.lower() or "user is deactivated" in error_msg.lower():
                blocked_count += 1
            else:
                failed_count += 1

    # Финальное сообщение о результатах
    result_text = (
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"📊 <b>Результаты:</b>\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"✅ Успешно отправлено: {sent_count}\n"
        f"❌ Не удалось отправить: {failed_count}\n"
        f"🚫 Заблокировали бота: {blocked_count}\n\n"
        f"📈 Успешных отправок: {sent_count / total_users * 100:.1f}%"
    )

    await status_msg.edit_text(result_text, parse_mode="HTML")

    # Логируем рассылку
    await log_action(callback_query.from_user.id, "Рассылка сообщений",
                     f"Отправлено: {sent_count}/{total_users} | Успех: {sent_count / total_users * 100:.1f}%")

    await state.clear()


# Обработчик отмены рассылки
@dp.callback_query(lambda c: c.data in ["broadcast_cancel", "cancel_broadcast"])
async def cancel_broadcast(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()

    await callback_query.message.answer("❌ Рассылка отменена")
    await state.clear()


# ========== ОБРАБОТЧИКИ АДМИН ПАНЕЛИ ==========

@dp.callback_query(lambda c: c.data.startswith("admin_"))
async def process_admin_callback(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()

    user_id = callback_query.from_user.id

    if not is_admin(user_id):
        await callback_query.message.answer("❌ У вас нет прав администратора!")
        return

    action = callback_query.data

    if action == "admin_stats":
        # Статистика
        stats = db.get_statistics()

        stats_text = (
            f"📊 <b>Статистика бота:</b>\n\n"
            f"👥 <b>Всего пользователей:</b> {stats['total_users']}\n"
            f"🛒 <b>Всего покупок:</b> {stats['total_purchases']}\n"
            f"💰 <b>Общая выручка:</b> {stats['total_revenue']} руб.\n"
            f"👑 <b>Админов:</b> {stats['total_admins']}\n"
            f"📱 <b>Всего аккаунтов:</b> {stats['total_accounts']}\n"
            f"🎁 <b>Промокодов:</b> {stats['total_promocodes']}\n"
            f"✅ <b>Активных промокодов:</b> {stats['active_promocodes']}\n"
            f"🔄 <b>Активаций промокодов:</b> {stats['total_promo_activations']}"
        )

        await callback_query.message.answer(stats_text, parse_mode="HTML")

    elif action == "admin_create_promo":
        # Создание промокода
        await callback_query.message.answer(
            "📝 <b>Создание промокода</b>\n\n"
            "Используйте команду:\n"
            "<code>/add_promo КОД СУММА [ЛИМИТ] [СРОК]</code>\n\n"
            "<b>Примеры:</b>\n"
            "• <code>/add_promo SUMMER2024 500</code> - промокод на 500 руб.\n"
            "• <code>/add_promo WELCOME100 100 10</code> - на 10 использований\n"
            "• <code>/add_promo UNLIMITED50 50 0</code> - бесконечный промокод\n"
            "• <code>/add_promo NEWYEAR500 500 50 2024-12-31</code> - с сроком\n\n"
            "💡 <b>Важно:</b> Каждый пользователь может использовать промокод только 1 раз!\n"
            "💡 <b>Лимит 0 = бесконечное использование для разных пользователей</b>",
            parse_mode="HTML"
        )

    elif action == "admin_promocodes":
        # Управление промокодами
        promocodes = db.get_all_promocodes()

        if not promocodes:
            await callback_query.message.answer("📭 Промокодов пока нет")
            return

        # Подсчитываем статистику
        active_count = 0
        total_amount = 0
        total_used = 0

        for promo in promocodes:
            amount, used_count, use_limit, valid_until = promo[1:5]
            total_amount += amount
            total_used += used_count

            # Проверяем активен ли промокод
            if (use_limit <= 0 or used_count < use_limit) and \
                    (not valid_until or datetime.now() < datetime.strptime(valid_until, '%Y-%m-%d %H:%M:%S')):
                active_count += 1

        stats_text = (
            f"🎁 <b>Управление промокодами</b>\n\n"
            f"📊 <b>Статистика:</b>\n"
            f"• Всего промокодов: {len(promocodes)}\n"
            f"• Активных: {active_count}\n"
            f"• Общая сумма: {total_amount} руб.\n"
            f"• Всего использований: {total_used}\n\n"
            f"<b>Доступные команды:</b>\n"
            f"• /add_promo - создать промокод\n"
            f"• /promo_list - список всех промокодов\n"
            f"• /promo_info КОД - информация о промокоде\n"
            f"• /delete_promo КОД - удалить промокод"
        )

        await callback_query.message.answer(stats_text, parse_mode="HTML")

    elif action == "admin_add_admin":
        # Добавление админа
        await callback_query.message.answer(
            "Для добавления администратора введите:\n"
            "/add_admin ID_ПОЛЬЗОВАТЕЛЯ\n\n"
            "Пример: /add_admin 123456789\n\n"
            "⚠️ Чтобы узнать ID пользователя, попросите его написать боту @userinfobot"
        )

    elif action == "admin_set_balance":
        # Изменение баланса
        await callback_query.message.answer(
            "Для изменения баланса пользователя введите:\n"
            "/set_balance ID_ПОЛЬЗОВАТЕЛЯ СУММА\n\n"
            "Пример: /set_balance 123456789 1000"
        )

    elif action == "admin_purchases":
        # История покупок
        purchases = db.get_recent_purchases(10)

        if purchases:
            purchases_text = "📦 <b>Последние 10 покупок:</b>\n\n"
            for purchase in purchases:
                purchase_id, username, games, email, price, date, account_data = purchase
                purchases_text += f"🆔 {purchase_id} | 👤 {username}\n🎮 {games}\n📧 {email if email else 'N/A'}\n💰 {price} руб. | 📅 {date}\n\n"
        else:
            purchases_text = "📭 Покупок еще не было"

        await callback_query.message.answer(purchases_text, parse_mode="HTML")

    elif action == "admin_accounts":
        # Управление аккаунтами
        accounts_text = "📱 <b>Управление аккаунтами</b>\n\nВыберите действие:"

        await callback_query.message.answer(
            text=accounts_text,
            reply_markup=get_accounts_menu(),
            parse_mode="HTML"
        )

    elif action == "admin_logs":
        # Последние логи
        logs = db.get_recent_logs(15)

        if logs:
            logs_text = "📋 <b>Последние 15 логов:</b>\n\n"
            for log in logs:
                action, details, username, user_id_log, log_date = log
                # Формируем ссылку на пользователя
                user_link = f"[{username}](tg://user?id={user_id_log})" if username else f"ID: {user_id_log}"
                logs_text += f"🕐 {log_date}\n👤 {user_link}\n📝 {action}\n"
                if details:
                    logs_text += f"🔍 {details}\n"
                logs_text += "─" * 20 + "\n"
        else:
            logs_text = "📭 Логов пока нет"

        await callback_query.message.answer(logs_text, parse_mode="Markdown")

    elif action == "admin_add_account":
        # Добавление аккаунта
        await callback_query.message.answer("📧 Введите email аккаунта:")
        await state.set_state(Form.waiting_for_account_email)

    elif action == "admin_list_accounts":
        # Список аккаунтов
        accounts = db.get_all_accounts(20)

        if accounts:
            accounts_text = "📱 <b>Список аккаунтов:</b>\n\n"
            for account in accounts:
                account_id, email, games = account
                games_display = games if games else "Не указаны"
                accounts_text += f"🆔 <b>#{account_id}</b>\n"
                accounts_text += f"📧 <code>{email}</code>\n"
                accounts_text += f"🎮 {games_display}\n"
                accounts_text += "─" * 20 + "\n"
        else:
            accounts_text = "📭 Аккаунтов пока нет"

        await callback_query.message.answer(accounts_text, parse_mode="HTML")

    elif action == "admin_delete_account":
        # Удаление аккаунта
        accounts = db.get_all_accounts(100)

        if accounts:
            accounts_list = "🗑️ <b>Доступные для удаления аккаунты:</b>\n\n"
            for account_id, email, games in accounts:
                accounts_list += f"🆔 #{account_id} | 📧 {email}\n"

            accounts_list += "\nВведите ID аккаунта для удаления:"
            await callback_query.message.answer(accounts_list, parse_mode="HTML")
            await state.set_state(Form.waiting_for_delete_account_id)
        else:
            await callback_query.message.answer("❌ Нет доступных аккаунтов для удаления")


# ========== ОБРАБОТЧИКИ УПРАВЛЕНИЯ АККАУНТАМИ ==========

# Обработчик добавления email аккаунта
@dp.message(Form.waiting_for_account_email)
async def process_account_email(message: types.Message, state: FSMContext):
    email = message.text.strip()

    if "@" not in email or "." not in email:
        await message.answer("❌ Неверный формат email. Попробуйте еще раз:")
        return

    await state.update_data(email=email)
    await message.answer("🔑 Введите пароль аккаунта:")
    await state.set_state(Form.waiting_for_account_password)


# Обработчик добавления пароля аккаунта
@dp.message(Form.waiting_for_account_password)
async def process_account_password(message: types.Message, state: FSMContext):
    password = message.text.strip()

    if len(password) < 4:
        await message.answer("❌ Пароль слишком короткий. Минимум 4 символа. Попробуйте еще раз:")
        return

    await state.update_data(password=password)
    await message.answer(
        "🎮 Введите игры на этом аккаунте (через запятую):\n"
        "Или отправьте 'нет', если не хотите указывать игры"
    )
    await state.set_state(Form.waiting_for_account_games)


# Обработчик добавления игр аккаунта
@dp.message(Form.waiting_for_account_games)
async def process_account_games(message: types.Message, state: FSMContext):
    games = message.text.strip()
    data = await state.get_data()
    email = data.get('email')
    password = data.get('password')

    # Если пользователь отправил "нет", сохраняем пустую строку
    if games.lower() == 'нет':
        games = ''

    # Сохраняем аккаунт в базу
    account_id = db.add_account(email, password, games, message.from_user.id)

    # Логируем добавление аккаунта
    await log_action(message.from_user.id, "Добавлен аккаунт",
                     f"Аккаунт #{account_id} | Email: {email}")

    await message.answer(
        f"✅ Аккаунт успешно добавлен!\n\n"
        f"🆔 ID: #{account_id}\n"
        f"📧 Email: {email}\n"
        f"🔑 Пароль: {password}\n"
        f"🎮 Игры: {games if games else 'Не указаны'}\n\n"
        f"Аккаунт готов к продаже!"
    )

    await state.clear()


# Обработчик удаления аккаунта
@dp.message(Form.waiting_for_delete_account_id)
async def process_delete_account(message: types.Message, state: FSMContext):
    try:
        account_id = int(message.text.strip())

        # Получаем аккаунт для логирования
        account = db.get_account(account_id)

        if not account:
            await message.answer(f"❌ Аккаунт #{account_id} не найден.")
            await state.clear()
            return

        email, password, games = account

        # Удаляем аккаунт
        success = db.delete_account(account_id)

        if not success:
            await message.answer(f"❌ Не удалось удалить аккаунт #{account_id}.")
            await state.clear()
            return

        # Логируем удаление аккаунта
        await log_action(message.from_user.id, "Удален аккаунт",
                         f"Аккаунт #{account_id} | Email: {email}")

        await message.answer(f"✅ Аккаунт #{account_id} успешно удален!")

    except ValueError:
        await message.answer("❌ Введите числовой ID аккаунта:")
        return

    await state.clear()


# ========== ОБРАБОТЧИКИ НАЖАТИЙ НА ИНЛАЙН КНОПКИ ==========

# Обработчик нажатий на инлайн кнопки (пользовательские)
@dp.callback_query(lambda c: c.data in ["back_to_menu", "back_to_admin"])
async def process_callback(callback_query: types.CallbackQuery):
    await callback_query.answer()

    if callback_query.data == "back_to_menu":
        username = callback_query.from_user.username or callback_query.from_user.first_name
        welcome_text = f"👋 Доброго времени суток, {username}!\n\n🎮 Это бот по продаже аккаунтов с играми на iOS.\n\n👇 Ниже выбери, куда ты хочешь перейти!"

        await callback_query.message.answer(
            text=welcome_text,
            reply_markup=get_main_menu()
        )

    elif callback_query.data == "back_to_admin":
        admin_text = "👑 Панель администратора\n\nВыберите действие:"

        await callback_query.message.answer(
            text=admin_text,
            reply_markup=get_admin_menu()
        )


# ========== АДМИН КОМАНДЫ ==========

# Команда для добавления админа
@dp.message(Command("add_admin"))
async def add_admin_command(message: types.Message):
    user_id = message.from_user.id

    if not is_admin(user_id):
        await message.answer("❌ У вас нет прав администратора!")
        return

    try:
        _, target_user_id = message.text.split()
        target_user_id = int(target_user_id)

        # Добавляем админа в базу
        db.set_user_admin(target_user_id, True)

        # Если пользователя нет в БД, создаем его
        user_data = db.get_user(target_user_id)
        if not user_data:
            db.add_user(target_user_id, "Неизвестный")
            db.set_user_admin(target_user_id, True)

        # Логируем добавление админа
        await log_action(user_id, "Добавлен администратор", f"Новый админ ID: {target_user_id}")

        await message.answer(f"✅ Пользователь {target_user_id} назначен администратором!")

        # Отправляем уведомление новому админу
        try:
            await bot.send_message(
                target_user_id,
                "👑 Поздравляем!\n\n"
                "Вы были назначены администратором бота!\n"
                "Для доступа к панели администратора используйте команду /admin"
            )
        except:
            pass  # Если не удалось отправить сообщение

    except ValueError:
        await message.answer("❌ Использование: /add_admin ID_ПОЛЬЗОВАТЕЛЯ")


# Команда для изменения баланса
@dp.message(Command("set_balance"))
async def set_balance_command(message: types.Message):
    user_id = message.from_user.id

    if not is_admin(user_id):
        await message.answer("❌ У вас нет прав администратора!")
        return

    try:
        _, target_user_id, amount = message.text.split()
        target_user_id = int(target_user_id)
        amount = float(amount)

        # Устанавливаем баланс
        db.set_user_balance(target_user_id, amount)

        # Логируем изменение баланса
        await log_action(user_id, "Изменен баланс",
                         f"Пользователь: {target_user_id} | Новый баланс: {amount} руб.")

        await message.answer(f"✅ Баланс пользователя {target_user_id} установлен: {amount} руб.")

    except ValueError:
        await message.answer("❌ Использование: /set_balance ID_ПОЛЬЗОВАТЕЛЯ СУММА")


# Функция для добавления промокода (для админа)
@dp.message(Command("add_promo"))
async def add_promocode(message: types.Message):
    user_id = message.from_user.id

    if not is_admin(user_id):
        await message.answer("❌ У вас нет прав администратора!")
        return

    try:
        # Парсим команду
        parts = message.text.split()

        if len(parts) < 3:
            await message.answer(
                "❌ Использование: /add_promo КОД СУММА [ЛИМИТ_ИСПОЛЬЗОВАНИЯ] [СРОК_ДЕЙСТВИЯ]\n\n"
                "Примеры:\n"
                "/add_promo SUMMER2024 500 - промокод на 500 руб.\n"
                "/add_promo WELCOME100 100 10 - на 10 использований\n"
                "/add_promo UNLIMITED50 50 0 - бесконечный промокод\n"
                "/add_promo NEWYEAR500 500 50 2024-12-31 - с сроком\n\n"
                "💡 <b>Важно:</b> Каждый пользователь может использовать промокод только 1 раз!\n"
                "💡 <b>Лимит 0 = бесконечное использование для разных пользователей</b>",
                parse_mode="HTML"
            )
            return

        code = parts[1].upper()
        amount = float(parts[2])

        # Парсим дополнительные параметры
        use_limit = 1  # По умолчанию одноразовый для каждого пользователя
        valid_until = None

        if len(parts) > 3:
            try:
                use_limit = int(parts[3])
                if use_limit < 0:
                    use_limit = 0  # 0 = бесконечное использование
            except ValueError:
                await message.answer("❌ Лимит использования должен быть числом!")
                return

        if len(parts) > 4:
            try:
                valid_until = parts[4]
                # Проверяем формат даты
                datetime.strptime(valid_until, '%Y-%m-%d')
                # Добавляем время окончания дня
                valid_until = f"{valid_until} 23:59:59"
            except ValueError:
                await message.answer("❌ Неверный формат даты! Используйте ГГГГ-ММ-ДД")
                return

        # Добавляем промокод в базу с новыми параметрами
        db.add_promocode(code, amount, user_id, use_limit, valid_until)

        # Формируем информацию о промокоде
        promo_info = f"✅ <b>Промокод создан!</b>\n\n"
        promo_info += f"🔑 <b>Код:</b> {code}\n"
        promo_info += f"💎 <b>Сумма:</b> {amount} руб.\n"
        promo_info += f"👥 <b>Лимит на пользователя:</b> 1 раз\n"
        promo_info += f"👥 <b>Общий лимит:</b> {use_limit if use_limit > 0 else '∞'}\n"

        if valid_until:
            promo_info += f"📅 <b>Действует до:</b> {valid_until.split()[0]}\n"
        else:
            promo_info += f"📅 <b>Срок действия:</b> бессрочно\n"

        promo_info += f"\n💡 <i>Каждый пользователь может активировать этот промокод только 1 раз!</i>"

        await message.answer(promo_info, parse_mode="HTML")

        # Логируем создание промокода
        await log_action(user_id, "Создан промокод",
                         f"Код: {code} | Сумма: {amount} руб. | Общий лимит: {use_limit} | Срок: {valid_until or 'бессрочно'}")

    except ValueError as e:
        await message.answer(f"❌ Ошибка в данных: {e}")
    except Exception as e:
        await message.answer(f"❌ Произошла ошибка: {e}")


# Команда для просмотра всех промокодов
@dp.message(Command("promo_list"))
async def list_promocodes(message: types.Message):
    user_id = message.from_user.id

    if not is_admin(user_id):
        await message.answer("❌ У вас нет прав администратора!")
        return

    # Получаем все промокоды
    promocodes = db.get_all_promocodes()

    if not promocodes:
        await message.answer("📭 Промокодов пока нет")
        return

    promo_list = "📋 <b>Список промокодов:</b>\n\n"

    for promo in promocodes:
        code, amount, used_count, use_limit, valid_until, created_by, created_date = promo

        # Определяем статус
        if use_limit > 0 and used_count >= use_limit:
            status = "❌ ИСЧЕРПАН"
        elif valid_until and datetime.now() > datetime.strptime(valid_until, '%Y-%m-%d %H:%M:%S'):
            status = "⏰ ПРОСРОЧЕН"
        else:
            status = "✅ АКТИВЕН"

        promo_list += f"🔹 <b>{code}</b> - {status}\n"
        promo_list += f"   💰 {amount} руб. | 🔄 {used_count}/{use_limit if use_limit > 0 else '∞'}\n"

        if valid_until:
            promo_list += f"   📅 {valid_until.split()[0]}\n"

        promo_list += "   ──────────────\n"

    await message.answer(promo_list, parse_mode="HTML")


# Команда для просмотра информации о промокоде
@dp.message(Command("promo_info"))
async def promocode_info(message: types.Message):
    user_id = message.from_user.id

    if not is_admin(user_id):
        await message.answer("❌ У вас нет прав администратора!")
        return

    try:
        _, code = message.text.split()
        code = code.upper()

        # Получаем данные промокода
        promo_data = db.get_promocode(code)
        if not promo_data:
            await message.answer(f"❌ Промокод '{code}' не найден!")
            return

        amount, used_count, use_limit, valid_until = promo_data

        # Получаем список пользователей, использовавших промокод
        users = db.get_promocode_users(code, 10)

        promo_info = f"📋 <b>Информация о промокоде</b>\n\n"
        promo_info += f"🔑 <b>Код:</b> {code}\n"
        promo_info += f"💎 <b>Сумма:</b> {amount} руб.\n"
        promo_info += f"🔄 <b>Использовано раз:</b> {used_count}"
        if use_limit > 0:
            promo_info += f"/{use_limit}\n"
            remaining = use_limit - used_count
            if remaining > 0:
                promo_info += f"✅ <b>Осталось использований:</b> {remaining}\n"
            else:
                promo_info += f"❌ <b>Лимит исчерпан</b>\n"
        else:
            promo_info += " (безлимитный)\n"

        if valid_until:
            promo_info += f"📅 <b>Действует до:</b> {valid_until.split()[0]}\n"
        else:
            promo_info += f"📅 <b>Срок действия:</b> бессрочно\n"

        promo_info += f"👥 <b>Лимит на пользователя:</b> 1 раз\n\n"

        if users:
            promo_info += f"👥 <b>Последние пользователи:</b>\n"
            for user_id_db, username, used_date in users:
                user_display = username if username else f"ID: {user_id_db}"
                promo_info += f"• {user_display} - {used_date}\n"
        else:
            promo_info += f"👥 <b>Еще никто не использовал этот промокод</b>\n"

        await message.answer(promo_info, parse_mode="HTML")

    except ValueError:
        await message.answer("❌ Использование: /promo_info КОД")


# Команда для удаления промокода
@dp.message(Command("delete_promo"))
async def delete_promocode(message: types.Message):
    user_id = message.from_user.id

    if not is_admin(user_id):
        await message.answer("❌ У вас нет прав администратора!")
        return

    try:
        _, code = message.text.split()
        code = code.upper()

        if db.delete_promocode(code):
            await message.answer(f"✅ Промокод '{code}' удален!")
            await log_action(user_id, "Удален промокод", f"Код: {code}")
        else:
            await message.answer(f"❌ Промокод '{code}' не найден!")

    except ValueError:
        await message.answer("❌ Использование: /delete_promo КОД")


# Команда для проверки своих промокодов
@dp.message(Command("my_promocodes"))
async def my_promocodes_command(message: types.Message):
    user_id = message.from_user.id

    # Получаем историю использования промокодов пользователем
    promo_history = db.get_user_promocode_history(user_id, 20)

    if not promo_history:
        await message.answer("📭 Вы еще не использовали ни одного промокода")
        return

    promo_list = "📜 <b>Ваша история промокодов:</b>\n\n"
    total_amount = 0

    for promo_code, amount, used_date in promo_history:
        promo_list += f"🔹 <b>{promo_code}</b>\n"
        promo_list += f"   💰 +{amount} руб.\n"
        promo_list += f"   📅 {used_date}\n"
        promo_list += "   ──────────────\n"
        total_amount += amount

    promo_list += f"\n💰 <b>Всего получено с промокодов:</b> {total_amount} руб."

    await message.answer(promo_list, parse_mode="HTML")


# Функция для проверки баланса
@dp.message(Command("balance"))
async def check_balance(message: types.Message):
    user_id = message.from_user.id

    user_data = db.get_user(user_id)

    if user_data:
        await message.answer(f"💰 Ваш баланс: {user_data[1]} руб.")
    else:
        await message.answer("❌ Пользователь не найден")


# ========== ЗАПУСК БОТА ==========

async def main():
    logger.info("🎮 Бот запущен!")
    logger.info(f"👑 Админы: {ADMIN_IDS}")

    try:
        await dp.start_polling(bot)
    finally:
        db.close()
        logger.info("Бот остановлен")


if __name__ == '__main__':
    asyncio.run(main())
