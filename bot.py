import logging
import os
from config import BOT_TOKEN, ADMIN_ID
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    BotCommand
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    PicklePersistence,
    PersistenceInput
)
from datetime import datetime
import pytz
import asyncio

# Настройка логгирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
MOSCOW_TZ = pytz.timezone('Europe/Moscow')

# Состояния
STATE_WAITING_WHITELIST = 1
STATE_WAITING_APPLICATION = 2
STATE_WAITING_CHANNEL = 3
STATE_WAITING_DISCOUNT_TEXT = 4
STATE_WAITING_DATETIME = 5
STATE_CHECK_RIGHTS = 6
STATE_WAITING_BROADCAST_TEXT = 7
STATE_WAITING_BROADCAST_TIME = 8
STATE_WAITING_ADMIN_CHANNEL = 9
STATE_WAITING_ADMIN_POST_TEXT = 10
STATE_WAITING_ADMIN_POST_TIME = 11
STATE_WAITING_UN_WHITELIST = 12  # Новое состояние для удаления из белого списка

# Клавиатуры
def get_default_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("❓ Информация ❓"), KeyboardButton("✔️ Добавить ТГК ✔️")]
        ],
        resize_keyboard=True,
        is_persistent=True
    )

def get_approved_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("❓ Информация ❓"), KeyboardButton("✔️ Добавить ТГК ✔️")],
            [KeyboardButton("➕ Добавить бота в канал ➕"), KeyboardButton("💰Создать скидку💰")],
            [KeyboardButton("🔍 Проверить права бота")]
        ],
        resize_keyboard=True,
        is_persistent=True
    )

def get_admin_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("❓ Информация ❓"), KeyboardButton("✔️ Добавить ТГК ✔️")],
            [KeyboardButton("➕ Добавить бота в канал ➕"), KeyboardButton("💰Создать скидку💰")],
            [KeyboardButton("🔍 Проверить права бота"), KeyboardButton("📋 Список ТГ каналов")],
            [KeyboardButton("📢 Запустить Скидон"), KeyboardButton("📨 Отправить всем")]
        ],
        resize_keyboard=True,
        is_persistent=True
    )

def get_approval_keyboard(application_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{application_id}"),
            InlineKeyboardButton("❌ Отказать", callback_data=f"reject_{application_id}")
        ]
    ])

async def setup_commands(application):
    await application.bot.set_my_commands([
        BotCommand("start", "Запустить бота"),
        BotCommand("check_rights", "Проверить права бота в канале"),
        BotCommand("whitelist", "Добавить в белый список (админ)"),
        BotCommand("un_whitelist", "Удалить из белого списка (админ)"),
        BotCommand("show_whitelist", "Показать белый список (админ)")
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_approved = user_id in context.bot_data.get('whitelist', set())
    
    # Добавляем пользователя в список подписчиков
    if 'subscribers' not in context.bot_data:
        context.bot_data['subscribers'] = set()
    context.bot_data['subscribers'].add(user_id)
    
    welcome_text = "Не выключай уведомления и ты будешь узнавать 1-м о скидках/конкурсах во всех ПРОВЕРЕННЫХ телеграмм каналах."
    
    if user_id == ADMIN_ID:
        await update.message.reply_text(welcome_text, reply_markup=get_admin_keyboard())
    elif is_approved:
        await update.message.reply_text(welcome_text, reply_markup=get_approved_keyboard())
    else:
        await update.message.reply_text(welcome_text, reply_markup=get_default_keyboard())

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info_text = """Бот создан для твоего удобства: 
-Надоела куча объявлений? 
-Отключил уведомления? 
-Устал, дорого? 
Тогда ты по адресу. 

**ОСТАВЛЯЙ УВЕДОМЛЕНИЯ** и узнавай 1-й о скидках и конкурсах в каналах с одеждой

- - - - - - - - - - - - - - - - - - - - - - -

И да можешь не переживать! Мусорок с 100 подписчиками в этом боте нет,
строго проверенные временем каналы,
с хорошим наличием и качественным сервисом."""
    await update.message.reply_text(info_text)

async def list_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⚠️ Эта функция только для владельца")
        return
    
    # Получаем список каналов из данных бота
    channels = context.bot_data.get('channels', [])
    
    if not channels:
        await update.message.reply_text("🤷‍♂️ Бот еще не добавлен ни в один канал")
        return
    
    message = "📋 Список каналов с ботом:\n\n"
    for i, channel in enumerate(channels, 1):
        message += f"{i}. {channel}\n"
    
    await update.message.reply_text(message)

async def start_discount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⚠️ Эта функция только для владельца")
        return
    
    await update.message.reply_text(
        "Укажите канал в формате @channelname, куда бот должен разместить пост:",
        reply_markup=get_admin_keyboard()
    )
    context.user_data['state'] = STATE_WAITING_ADMIN_CHANNEL

async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⚠️ Эта функция только для владельца")
        return
    
    await update.message.reply_text(
        "Введите текст сообщения для рассылки всем подписчикам:",
        reply_markup=get_admin_keyboard()
    )
    context.user_data['state'] = STATE_WAITING_BROADCAST_TEXT

async def send_broadcast(context: ContextTypes.DEFAULT_TYPE):
    if 'broadcast_text' not in context.bot_data:
        logger.error("Текст рассылки не найден в bot_data")
        return
    
    text = context.bot_data['broadcast_text']
    subscribers = context.bot_data.get('subscribers', set())
    
    if not subscribers:
        logger.error("Нет подписчиков для рассылки")
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text="❌ Нет подписчиков для рассылки"
        )
        return
    
    success = 0
    failed = 0
    
    for user_id in subscribers:
        try:
            await context.bot.send_message(chat_id=user_id, text=text)
            success += 1
            # Небольшая задержка между сообщениями, чтобы избежать ограничений Telegram
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")
            failed += 1
    
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"✅ Рассылка завершена:\nУспешно: {success}\nНе удалось: {failed}"
    )

async def schedule_broadcast(context: ContextTypes.DEFAULT_TYPE, broadcast_time: datetime):
    """Планирует рассылку на указанное время"""
    now = datetime.now(MOSCOW_TZ)
    delay = (broadcast_time - now).total_seconds()
    
    if delay > 0:
        logger.info(f"Запланирована рассылка через {delay} секунд")
        await asyncio.sleep(delay)
        await send_broadcast(context)
    else:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text="❌ Указанное время уже прошло. Рассылка не выполнена."
        )

async def schedule_post(context: ContextTypes.DEFAULT_TYPE, channel: str, post_text: str, post_time: datetime):
    """Планирует публикацию поста на указанное время"""
    now = datetime.now(MOSCOW_TZ)
    delay = (post_time - now).total_seconds()
    
    if delay > 0:
        logger.info(f"Запланирована публикация поста через {delay} секунд")
        await asyncio.sleep(delay)
        try:
            # Удаляем @ из начала имени канала, если он есть
            channel = channel.lstrip('@')
            await context.bot.send_message(chat_id=f"@{channel}", text=post_text)
            
            # Добавляем канал в список, если его там еще нет
            if 'channels' not in context.bot_data:
                context.bot_data['channels'] = []
            if channel not in context.bot_data['channels']:
                context.bot_data['channels'].append(channel)
            
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"✅ Пост опубликован в @{channel} в запланированное время:\n\n{post_text}"
            )
        except Exception as e:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"❌ Ошибка при публикации поста в @{channel}: {e}"
            )
    else:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text="❌ Указанное время уже прошло. Пост не опубликован."
        )

async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"🔔 Новый запрос на добавление ТГК:\nID: {user.id}\nUsername: @{user.username if user.username else 'нет'}\nИмя: {user.full_name}"
    )
    
    text = "ЭТО БЕСПЛАТНО Привет, хочешь что бы bot отправлял твои скидки/акции всем участникам? Жми кнопку: «Отправить заявку»"
    keyboard = [[InlineKeyboardButton("«Отправить заявку»", callback_data='send_application')]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def add_to_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📢 Добавить бота в канал", url=f"https://t.me/{context.bot.username}?startchannel&admin=post_messages")],
        [InlineKeyboardButton("✅ Я добавил бота", callback_data="bot_added")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    instructions = (
        "Чтобы бот мог публиковать скидки в вашем канале:\n\n"
        "1. Нажмите кнопку ниже «Добавить бота в канал»\n"
        "2. Выберите нужный канал\n"
        "3. Назначьте права:\n"
        "   - ✉️ Отправка сообщений\n\n"
        "4. Нажмите «✅ Я добавил бота» для проверки"
    )
    
    await update.message.reply_text(instructions, reply_markup=reply_markup)

async def check_channel_rights(bot, channel_username):
    try:
        channel_username = channel_username.lstrip('@')
        chat = await bot.get_chat(f"@{channel_username}")
        
        # Проверяем, является ли бот администратором канала
        try:
            member = await chat.get_member(bot.id)
            if not member.status == "administrator":
                return False, "❌ Бот не является администратором канала"
            
            if not member.can_post_messages:
                return False, "❌ Бот не имеет прав на отправку сообщений"
            
            return True, "✅ Все права в порядке: бот администратор с правом публикации"
            
        except Exception as e:
            return False, f"❌ Бот не является участником канала или произошла ошибка: {str(e)}"
        
    except Exception as e:
        return False, f"⚠️ Ошибка проверки прав: {str(e)}. Убедитесь, что:\n1. Бот добавлен в канал как администратор\n2. Вы указали правильное имя канала (например, @channelname)"

async def check_rights(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Введите @username вашего канала для проверки прав бота:",
        reply_markup=get_approved_keyboard()
    )
    context.user_data['state'] = STATE_CHECK_RIGHTS

async def create_discount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in context.bot_data.get('whitelist', set()):
        await update.message.reply_text("❌ Сначала добавьте бота в канал и проверьте права")
        return
    
    await update.message.reply_text(
        "Укажите ваш канал в формате @channelname:",
        reply_markup=get_approved_keyboard()
    )
    context.user_data['state'] = STATE_WAITING_CHANNEL

async def whitelist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⚠️ Эта команда только для администратора")
        return
    
    await update.message.reply_text(
        "Введите ID пользователя для добавления в белый список:",
        reply_markup=get_admin_keyboard()
    )
    context.user_data['state'] = STATE_WAITING_WHITELIST
    logger.info(f"Администратор {update.effective_user.id} начал добавление в белый список")

async def un_whitelist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⚠️ Эта команда только для администратора")
        return
    
    await update.message.reply_text(
        "Введите ID пользователя для удаления из белого списка:",
        reply_markup=get_admin_keyboard()
    )
    context.user_data['state'] = STATE_WAITING_UN_WHITELIST
    logger.info(f"Администратор {update.effective_user.id} начал удаление из белого списка")

async def show_whitelist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⚠️ Эта команда только для администратора")
        return
    
    whitelist = context.bot_data.get('whitelist', set())
    if not whitelist:
        await update.message.reply_text("Белый список пуст")
        return
    
    message = "📋 Белый список:\n" + "\n".join(str(user_id) for user_id in whitelist)
    await update.message.reply_text(message)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'send_application':
        user = query.from_user
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"📝 Пользователь начал заполнять заявку:\nID: {user.id}\nUsername: @{user.username if user.username else 'нет'}"
        )
        
        await query.edit_message_text("Заполни форму и отправь её мне:\nжми на текст ниже (он скопируется сам).")
        
        form_text = """```
Ваш ник с @:
Ссылка на ваш канал:
Количество подписчиков:
Как часто у вас бывают скидки:
Как часто у вас бывают конкурсы:
Цель вступления в программу рассылки:
```"""
        await context.bot.send_message(chat_id=query.message.chat_id, text=form_text, parse_mode='Markdown')
        context.user_data['state'] = STATE_WAITING_APPLICATION
    
    elif query.data == 'bot_added':
        await query.edit_message_text(
            "Введите @username вашего канала для проверки прав бота:",
            reply_markup=None
        )
        context.user_data['state'] = STATE_CHECK_RIGHTS
        context.user_data['after_add'] = True
    
    elif query.data.startswith('approve_'):
        application_id = query.data.split('_')[1]
        original_message = query.message.text
        
        # Извлекаем информацию о пользователе из сообщения
        lines = original_message.split('\n')
        user_info = lines[0]
        
        try:
            # Парсим ID пользователя
            if "ID:" in user_info:
                user_id = int(user_info.split("ID:")[1].strip().split(")")[0])
                
                # Добавляем пользователя в белый список
                if 'whitelist' not in context.bot_data:
                    context.bot_data['whitelist'] = set()
                context.bot_data['whitelist'].add(user_id)
                
                # Добавляем пользователя в список подписчиков
                if 'subscribers' not in context.bot_data:
                    context.bot_data['subscribers'] = set()
                context.bot_data['subscribers'].add(user_id)
                
                # Сохраняем изменения
                await context.application.persistence.flush()
                logger.info(f"Пользователь {user_id} добавлен в белый список")
                
                # Отправляем сообщение пользователю
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text="✅ Заявка одобрена! Ваша реклама с Скидкой будет автоматически опубликована в боте и в вашем канале.",
                        reply_markup=get_approved_keyboard()
                    )
                    await query.edit_message_text(
                        f"✅ Заявка одобрена и пользователь {user_id} добавлен в белый список:\n{original_message}"
                    )
                except Exception as e:
                    logger.error(f"Ошибка при отправке уведомления пользователю {user_id}: {e}")
                    await query.edit_message_text(
                        f"✅ Заявка одобрена, но не удалось уведомить пользователя:\n{original_message}"
                    )
            else:
                raise ValueError("ID пользователя не найден в сообщении")
        
        except Exception as e:
            logger.error(f"Ошибка при обработке заявки: {e}")
            await query.edit_message_text(
                f"❌ Ошибка при обработке заявки: {e}"
            )
    
    elif query.data.startswith('reject_'):
        application_id = query.data.split('_')[1]
        original_message = query.message.text
        
        # Извлекаем информацию о пользователе из сообщения
        lines = original_message.split('\n')
        user_info = lines[0]
        
        try:
            # Парсим ID пользователя
            if "ID:" in user_info:
                user_id = int(user_info.split("ID:")[1].strip().split(")")[0])
                
                # Отправляем сообщение пользователю
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text="❌ К сожалению в публикации 'Скидки' вам отказано, попробуйте подать заявку ещё раз."
                    )
                    await query.edit_message_text(
                        f"❌ Заявка отклонена:\n{original_message}\n\nПользователь уведомлен."
                    )
                except Exception as e:
                    logger.error(f"Ошибка при отправке уведомления пользователю {user_id}: {e}")
                    await query.edit_message_text(
                        f"❌ Заявка отклонена, но не удалось уведомить пользователя:\n{original_message}"
                    )
            else:
                raise ValueError("ID пользователя не найден в сообщении")
        
        except Exception as e:
            logger.error(f"Ошибка при обработке заявки: {e}")
            await query.edit_message_text(
                f"❌ Ошибка при обработке заявки: {e}"
            )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    logger.info(f"Получено сообщение от {user.id}: {text}")

    # Обработка состояний для администратора
    if user.id == ADMIN_ID:
        if context.user_data.get('state') == STATE_WAITING_WHITELIST:
            try:
                user_id = int(text.strip())
                
                # Инициализация whitelist, если его нет
                if 'whitelist' not in context.bot_data:
                    context.bot_data['whitelist'] = set()
                
                # Добавляем пользователя в белый список
                context.bot_data['whitelist'].add(user_id)
                
                # Инициализация subscribers, если его нет
                if 'subscribers' not in context.bot_data:
                    context.bot_data['subscribers'] = set()
                context.bot_data['subscribers'].add(user_id)
                
                # Сохраняем изменения
                await context.application.persistence.flush()
                
                # Пытаемся уведомить пользователя
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text="🎉 Ваш канал одобрен! Теперь вам доступны дополнительные функции.",
                        reply_markup=get_approved_keyboard()
                    )
                    await update.message.reply_text(
                        f"✅ Пользователь {user_id} добавлен в белый список и уведомлен.",
                        reply_markup=get_admin_keyboard()
                    )
                except Exception as e:
                    await update.message.reply_text(
                        f"✅ Пользователь {user_id} добавлен в белый список, но не удалось отправить уведомление: {e}",
                        reply_markup=get_admin_keyboard()
                    )
                
            except ValueError:
                await update.message.reply_text(
                    "❌ Неверный формат ID. Введите числовой ID.",
                    reply_markup=get_admin_keyboard()
                )
            finally:
                context.user_data.pop('state', None)
                return
        
        elif context.user_data.get('state') == STATE_WAITING_UN_WHITELIST:
            try:
                user_id = int(text.strip())
                
                # Проверяем существование whitelist
                if 'whitelist' not in context.bot_data:
                    context.bot_data['whitelist'] = set()
                    await update.message.reply_text(
                        "ℹ️ Белый список был пуст, создан новый",
                        reply_markup=get_admin_keyboard()
                    )
                    context.user_data.pop('state', None)
                    return
                
                # Удаляем пользователя из белого списка
                if user_id in context.bot_data['whitelist']:
                    context.bot_data['whitelist'].remove(user_id)
                    
                    # Сохраняем изменения
                    await context.application.persistence.flush()
                    
                    # Пытаемся уведомить пользователя
                    try:
                        await context.bot.send_message(
                            chat_id=user_id,
                            text="❌ Ваш канал больше не одобрен. Некоторые функции бота стали недоступны.",
                            reply_markup=get_default_keyboard()
                        )
                        await update.message.reply_text(
                            f"✅ Пользователь {user_id} удален из белого списка и уведомлен.",
                            reply_markup=get_admin_keyboard()
                        )
                    except Exception as e:
                        await update.message.reply_text(
                            f"✅ Пользователь {user_id} удален из белого списка, но не удалось отправить уведомление: {e}",
                            reply_markup=get_admin_keyboard()
                        )
                else:
                    await update.message.reply_text(
                        f"ℹ️ Пользователь {user_id} не найден в белом списке",
                        reply_markup=get_admin_keyboard()
                    )
                
            except ValueError:
                await update.message.reply_text(
                    "❌ Неверный формат ID. Введите числовой ID.",
                    reply_markup=get_admin_keyboard()
                )
            finally:
                context.user_data.pop('state', None)
                return
            
        elif context.user_data.get('state') == STATE_WAITING_ADMIN_CHANNEL:
            context.user_data['admin_channel'] = text
            await update.message.reply_text(
                "Введите текст для поста:",
                reply_markup=get_admin_keyboard()
            )
            context.user_data['state'] = STATE_WAITING_ADMIN_POST_TEXT
            return
        
        elif context.user_data.get('state') == STATE_WAITING_ADMIN_POST_TEXT:
            context.user_data['admin_post_text'] = text
            await update.message.reply_text(
                "Введите дату и время публикации по Москве (формат: ДД.ММ.ГГГГ ЧЧ:ММ):",
                reply_markup=get_admin_keyboard()
            )
            context.user_data['state'] = STATE_WAITING_ADMIN_POST_TIME
            return
        
        elif context.user_data.get('state') == STATE_WAITING_ADMIN_POST_TIME:
            channel = context.user_data['admin_channel']
            post_text = context.user_data['admin_post_text']
            post_time = text
            
            try:
                post_time = datetime.strptime(post_time, "%d.%m.%Y %H:%M")
                post_time = MOSCOW_TZ.localize(post_time)
                
                if post_time < datetime.now(MOSCOW_TZ):
                    await update.message.reply_text(
                        "❌ Указанное время уже прошло. Введите будущее время.",
                        reply_markup=get_admin_keyboard()
                    )
                    return
                
                await update.message.reply_text(
                    f"✅ Пост запланирован на публикацию в {channel} в {post_time.strftime('%d.%m.%Y %H:%M')}",
                    reply_markup=get_admin_keyboard()
                )
                asyncio.create_task(schedule_post(context, channel, post_text, post_time))
                
            except ValueError:
                await update.message.reply_text(
                    "❌ Неверный формат времени. Используйте ДД.ММ.ГГГГ ЧЧ:ММ",
                    reply_markup=get_admin_keyboard()
                )
            finally:
                context.user_data.pop('state', None)
                return
        
        elif context.user_data.get('state') == STATE_WAITING_BROADCAST_TEXT:
            context.bot_data['broadcast_text'] = text
            await update.message.reply_text(
                "Введите дату и время рассылки по Москве (формат: ДД.ММ.ГГГГ ЧЧ:ММ):",
                reply_markup=get_admin_keyboard()
            )
            context.user_data['state'] = STATE_WAITING_BROADCAST_TIME
            return
        
        elif context.user_data.get('state') == STATE_WAITING_BROADCAST_TIME:
            try:
                broadcast_time = datetime.strptime(text, "%d.%m.%Y %H:%M")
                broadcast_time = MOSCOW_TZ.localize(broadcast_time)
                
                if broadcast_time < datetime.now(MOSCOW_TZ):
                    await update.message.reply_text(
                        "❌ Указанное время уже прошло. Введите будущее время.",
                        reply_markup=get_admin_keyboard()
                    )
                    return
                
                await update.message.reply_text(
                    f"✅ Рассылка запланирована на {broadcast_time.strftime('%d.%m.%Y %H:%M')}",
                    reply_markup=get_admin_keyboard()
                )
                asyncio.create_task(schedule_broadcast(context, broadcast_time))
                
            except ValueError:
                await update.message.reply_text(
                    "❌ Неверный формат времени. Используйте ДД.ММ.ГГГГ ЧЧ:ММ",
                    reply_markup=get_admin_keyboard()
                )
            finally:
                context.user_data.pop('state', None)
                return
    
    # Обработка заявки
    if context.user_data.get('state') == STATE_WAITING_APPLICATION:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"📄 Новая заявка от @{user.username if user.username else 'нет_username'} (ID: {user.id}):\n{text}"
        )
        await update.message.reply_text("Спасибо за заявку! Мы свяжемся с вами в течение 24 часов.")
        context.user_data.pop('state', None)
        return
    
    # Проверка прав бота
    if context.user_data.get('state') == STATE_CHECK_RIGHTS:
        channel_username = text.lstrip('@')
        checking_msg = await update.message.reply_text("🔍 Проверяем права...")
        
        success, result = await check_channel_rights(context.bot, channel_username)
        
        await context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=checking_msg.message_id
        )
        
        if success:
            response = f"{result}\n\n✅ Теперь вы можете создавать скидки!"
            
            # Добавляем канал в список каналов бота
            if 'channels' not in context.bot_data:
                context.bot_data['channels'] = []
            if channel_username not in context.bot_data['channels']:
                context.bot_data['channels'].append(channel_username)
        else:
            response = f"{result}\n\nПожалуйста, добавьте бота снова и назначьте нужные права."
        
        if context.user_data.get('after_add'):
            response += "\n\nИспользуйте кнопку «💰Создать скидку💰»"
            context.user_data.pop('after_add', None)
        
        await update.message.reply_text(
            response,
            reply_markup=get_approved_keyboard()
        )
        context.user_data.pop('state', None)
        return
    
    # Обработка создания скидки
    if context.user_data.get('state') == STATE_WAITING_CHANNEL:
        context.user_data['channel'] = text
        context.user_data['user_username'] = f"@{user.username}" if user.username else f"ID:{user.id}"
        context.user_data['user_id'] = user.id
        await update.message.reply_text("ПРИШЛИТЕ ТЕКСТ СКИДКИ, например - Скидка 44% до конца дня на весь товар, ищи #вналичии@ваш_канал:")
        context.user_data['state'] = STATE_WAITING_DISCOUNT_TEXT
        return
    
    if context.user_data.get('state') == STATE_WAITING_DISCOUNT_TEXT:
        context.user_data['discount_text'] = text
        await update.message.reply_text("Укажите дату и время публикации, Например: (20.09.2025 12:00):")
        context.user_data['state'] = STATE_WAITING_DATETIME
        return
    
    if context.user_data.get('state') == STATE_WAITING_DATETIME:
        username = context.user_data.get('user_username', 'неизвестный_пользователь')
        user_id = context.user_data.get('user_id', None)
        application_id = f"{user_id}_{int(update.message.date.timestamp())}"
        
        message_text = (
            f"⏰ Новая заявка на скидку от {username} (ID: {user_id}):\n"
            f"Канал: {context.user_data['channel']}\n"
            f"Текст: {context.user_data['discount_text']}\n"
            f"Время: {text}"
        )
        
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=message_text,
            reply_markup=get_approval_keyboard(application_id)
        )
        
        await update.message.reply_text("✅ Скидка отправлена на модерацию!")
        context.user_data.pop('state', None)
        return
    
    # Обработка обычных сообщений
    if update.message.text == "❓ Информация ❓":
        await info(update, context)
    elif update.message.text == "✔️ Добавить ТГК ✔️":
        await add_channel(update, context)
    elif update.message.text == "➕ Добавить бота в канал ➕":
        await add_to_channel(update, context)
    elif update.message.text == "💰Создать скидку💰":
        await create_discount(update, context)
    elif update.message.text == "🔍 Проверить права бота":
        await check_rights(update, context)
    elif update.message.text == "📢 Запустить Скидон" and update.effective_user.id == ADMIN_ID:
        await start_discount(update, context)
    elif update.message.text == "📨 Отправить всем" and update.effective_user.id == ADMIN_ID:
        await start_broadcast(update, context)
    elif update.message.text == "📋 Список ТГ каналов" and update.effective_user.id == ADMIN_ID:
        await list_channels(update, context)

def main():
    # Используем PicklePersistence для сохранения данных между перезапусками
    persistence = PicklePersistence(
        filepath='bot_data.pickle',
        store_data=PersistenceInput(
            bot_data=True,    # Сохраняем данные бота (включая белый список)
            chat_data=False,  # Не сохраняем данные чатов
            user_data=False   # Не сохраняем данные пользователей
        )
    )
    
    application = Application.builder() \
        .token(BOT_TOKEN) \
        .persistence(persistence) \
        .post_init(setup_commands) \
        .build()

    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("whitelist", whitelist))
    application.add_handler(CommandHandler("un_whitelist", un_whitelist))
    application.add_handler(CommandHandler("check_rights", check_rights))
    application.add_handler(CommandHandler("show_whitelist", show_whitelist))
    
    # Обработчики кнопок меню
    application.add_handler(MessageHandler(filters.Regex(r'❓ Информация ❓'), info))
    application.add_handler(MessageHandler(filters.Regex(r'✔️ Добавить ТГК ✔️'), add_channel))
    application.add_handler(MessageHandler(filters.Regex(r'➕ Добавить бота в канал ➕'), add_to_channel))
    application.add_handler(MessageHandler(filters.Regex(r'💰Создать скидку💰'), create_discount))
    application.add_handler(MessageHandler(filters.Regex(r'🔍 Проверить права бота'), check_rights))
    application.add_handler(MessageHandler(filters.Regex(r'📢 Запустить Скидон') & filters.User(ADMIN_ID), start_discount))
    application.add_handler(MessageHandler(filters.Regex(r'📨 Отправить всем') & filters.User(ADMIN_ID), start_broadcast))
    application.add_handler(MessageHandler(filters.Regex(r'📋 Список ТГ каналов') & filters.User(ADMIN_ID), list_channels))
    
    # Остальные обработчики
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()

if __name__ == '__main__':
    main()
