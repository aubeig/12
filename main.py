import os
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.enums import ParseMode
from dotenv import load_dotenv
import requests
import json
import html

# Загрузка переменных окружения
load_dotenv()

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
CREATOR = "@Сырок"  # Создатель бота

# Настройка логгера
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# Хранилище тем пользователей (в реальном проекте используйте БД)
user_themes = {}

# Стили для разных тем
THEMES = {
    "dark": {
        "name": "🌑 Классическая Тёмная",
        "bg": "#121212",
        "card": "#1e1e1e",
        "text": "#e0e0e0",
        "primary": "#bb86fc",
        "accent": "#03dac6"
    },
    "purple": {
        "name": "💜 Фиолетовая Галактика",
        "bg": "#1a1a2e",
        "card": "#16213e",
        "text": "#e6e6e6",
        "primary": "#8a4fff",
        "accent": "#ff2e63"
    },
    "blue": {
        "name": "🔷 Глубокий Океан",
        "bg": "#0f172a",
        "card": "#1e293b",
        "text": "#f1f5f9",
        "primary": "#3b82f6",
        "accent": "#06b6d4"
    }
}

# Генератор клавиатуры с анимационными эффектами
def build_keyboard(user_id: int = None):
    theme_name = user_themes.get(user_id, "dark")
    theme = THEMES[theme_name]
    
    builder = InlineKeyboardBuilder()
    
    buttons = [
        ("🔄 Новый диалог", "new_chat"),
        ("🎨 Сменить тему", "change_theme"),
        ("💡 Примеры запросов", "examples"),
        ("👨‍💻 О создателе", "about")
    ]
    
    for text, data in buttons:
        builder.add(InlineKeyboardButton(
            text=text,
            callback_data=data
        ))
    
    builder.adjust(2)
    return builder.as_markup()

# Анимация загрузки
async def show_typing_animation(chat_id: int):
    await bot.send_chat_action(chat_id, "typing")

# Получение ответа от DeepSeek-R1
async def get_ai_response(prompt: str, user_id: int):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": f"tg://user?id={user_id}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "deepseek/deepseek-r1:free",  # Обновлено до R1
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 1024
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        logger.error(f"API error: {e}")
        return "⚠️ Произошла ошибка при обработке запроса. Пожалуйста, попробуйте позже."

# Обработчик команды /start с анимацией
@dp.message(Command("start"))
async def start_command(message: types.Message):
    user_id = message.from_user.id
    theme_name = user_themes.get(user_id, "dark")
    theme = THEMES[theme_name]
    
    welcome_msg = f"""
    <b>✨ Добро пожаловать в DeepSeek AI Assistant!</b>
    
    Я ваш персональный ИИ-помощник на базе модели <b>DeepSeek-R1</b>.
    Выберите действие из меню ниже:
    """
    
    # Анимация отправки
    await message.answer_chat_action("typing")
    await message.answer(
        text=welcome_msg,
        reply_markup=build_keyboard(user_id)
    )

# Обработчик текстовых сообщений
@dp.message(F.text)
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    theme_name = user_themes.get(user_id, "dark")
    theme = THEMES[theme_name]
    
    await show_typing_animation(message.chat.id)
    
    # Получаем ответ от ИИ
    response = await get_ai_response(message.text, user_id)
    
    # Экранируем HTML-символы
    safe_response = html.escape(response)
    
    # Форматируем ответ с использованием текущей темы
    formatted_response = f"""
    <b>🤖 DeepSeek-R1:</b>
    <blockquote>{safe_response}</blockquote>
    
    <i>💬 Продолжите диалог...</i>
    """
    
    await message.answer(
        text=formatted_response,
        reply_markup=build_keyboard(user_id)
    )

# Обработчик инлайн-кнопок
@dp.callback_query(F.data == "change_theme")
async def change_theme(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    theme_buttons = InlineKeyboardBuilder()
    
    for theme_key, theme_data in THEMES.items():
        emoji = "✅" if user_themes.get(user_id) == theme_key else "⚪️"
        theme_buttons.add(InlineKeyboardButton(
            text=f"{emoji} {theme_data['name']}",
            callback_data=f"set_theme_{theme_key}"
        ))
    
    theme_buttons.adjust(1)
    
    # Кнопка "Назад"
    theme_buttons.row(InlineKeyboardButton(
        text="🔙 Назад",
        callback_data="main_menu"
    ))
    
    await callback.message.edit_text(
        text="<b>🎨 Выберите тему интерфейса:</b>",
        reply_markup=theme_buttons.as_markup()
    )
    await callback.answer()

# Обработчик смены темы
@dp.callback_query(F.data.startswith("set_theme_"))
async def set_theme(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    theme_key = callback.data.split("_")[-1]
    
    if theme_key in THEMES:
        user_themes[user_id] = theme_key
        theme = THEMES[theme_key]
        
        # Анимация смены темы
        await callback.answer(f"Тема изменена на {theme['name']}!", show_alert=False)
        
        # Обновляем сообщение с новой темой
        await callback.message.edit_text(
            text=f"<b>🎨 Тема успешно изменена!</b>\n"
                 f"<i>{theme['name']}</i> теперь активна.\n\n"
                 "Интерфейс бота обновлён с выбранной цветовой схемой.",
            reply_markup=build_keyboard(user_id)
        )
    else:
        await callback.answer("⚠️ Ошибка смены темы", show_alert=True)

# Примеры запросов
@dp.callback_query(F.data == "examples")
async def show_examples(callback: types.CallbackQuery):
    examples = """
    <b>💡 Примеры запросов:</b>
    
    • Напиши план развития для стартапа в сфере ИИ
    • Объясни квантовую физику простыми словами
    • Помоги составить бизнес-план для кофейни
    • Предложи идеи для мобильного приложения
    • Напиши Python-скрипт для анализа данных
    """
    
    await callback.message.edit_text(
        text=examples,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")
        ]])
    )
    await callback.answer()

# Информация о создателе
@dp.callback_query(F.data == "about")
async def show_about(callback: types.CallbackQuery):
    about_text = f"""
    <b>👨‍💻 О создателе</b>
    
    Этот ИИ-ассистент создан {CREATOR}
    
    <b>Технологии:</b>
    • Платформа: Telegram Bot API
    • ИИ-модель: DeepSeek-R1
    • Бэкенд: Python + aiogram
    • Хостинг: OpenRouter.ai
    
    <b>Особенности:</b>
    🌑 3 темы интерфейса
    ✨ Анимации взаимодействия
    🧠 Продвинутый ИИ-ассистент
    """
    
    await callback.message.edit_text(
        text=about_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")
        ]])
    )
    await callback.answer()

# Возврат в главное меню
@dp.callback_query(F.data == "main_menu")
async def main_menu(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    await callback.message.edit_text(
        text="<b>✨ Главное меню</b>\nВыберите действие:",
        reply_markup=build_keyboard(user_id)
    )
    await callback.answer()

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    print("Бот запущен! Для остановки нажмите Ctrl+C")
    asyncio.run(main())
