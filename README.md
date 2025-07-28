# Telegram Discount Bot

Бот для управления скидками и публикациями в Telegram каналах.

## Основные функции
- Управление белым списком каналов
- Планирование публикации скидок
- Массовая рассылка сообщений
- Проверка прав бота в каналах

## Установка
1. Клонировать репозиторий:  
   `git clone https://github.com/ваш-логин/telegram-discount-bot.git`
2. Установить зависимости:  
   `pip install -r requirements.txt`
3. Создать файл `config.py` с настройками
4. Запустить бота:  
   `python bot.py`

## Развертывание на Scalingo
1. Установить Scalingo CLI:  
   `npm install -g scalingo-cli`
2. Логин:  
   `scalingo login`
3. Создать приложение:  
   `scalingo create your-app-name`
4. Установить переменные окружения:
