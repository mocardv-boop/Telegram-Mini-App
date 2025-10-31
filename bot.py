import logging
import sqlite3
import random
import os
import shutil
import time
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.error import NetworkError, TelegramError

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# === КОНФИГУРАЦИЯ ===
BOT_TOKEN = "8455502884:AAHNPG2Ou_QlX0M4GZq3uZcpODd6zIkraZo"
ADMIN_IDS = [8378217976]  # ЗАМЕНИТЕ НА ВАШ ID!

# Папки для файлов
IMAGE_FOLDER = "bot_images"
os.makedirs(IMAGE_FOLDER, exist_ok=True)

print("🎯 Запуск бота...")

class Database:
    def __init__(self, db_name="bot_database.db"):
        self.db_name = db_name
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                registration_date TEXT,
                last_game_date TEXT,
                prizes_count INTEGER DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_prizes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                prize_name TEXT,
                won_date TEXT,
                expires_date TEXT,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS prize_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                chance INTEGER,
                duration_hours INTEGER
            )
        ''')
        
        cursor.execute('SELECT COUNT(*) FROM prize_config')
        if cursor.fetchone()[0] == 0:
            default_prizes = [
                ("🎁 10% скидка", 40, 24),
                ("🎁 Бесплатная доставка", 30, 24),
                ("🎁 Подарок от партнера", 20, 24),
                ("🎁 Специальный приз", 10, 24),
            ]
            for prize in default_prizes:
                cursor.execute(
                    'INSERT INTO prize_config (name, chance, duration_hours) VALUES (?, ?, ?)',
                    prize
                )
        
        conn.commit()
        conn.close()
        print("✅ База данных готова")

    def register_user(self, user_id, username, first_name, last_name):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO users 
                (user_id, username, first_name, last_name, registration_date, prizes_count)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, username, first_name, last_name, 
                  datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 0))
            conn.commit()
            return True
        except Exception as e:
            print(f"Ошибка регистрации: {e}")
            return False
        finally:
            conn.close()

    def get_user_profile(self, user_id):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT username, first_name, last_name, registration_date, last_game_date, prizes_count 
            FROM users WHERE user_id = ?
        ''', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'username': result[0] or 'Не указан',
                'first_name': result[1] or 'Не указано',
                'last_name': result[2] or 'Не указано',
                'registration_date': result[3] or 'Не указана',
                'last_game_date': result[4] or 'Никогда',
                'prizes_count': result[5] or 0
            }
        return None

    def can_play_today(self, user_id):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('SELECT last_game_date FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result or not result[0]:
            return True
            
        try:
            last_game = datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S")
            return datetime.now() - last_game >= timedelta(days=1)
        except:
            return True

    def update_last_game(self, user_id):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users 
            SET last_game_date = ?, prizes_count = prizes_count + 1 
            WHERE user_id = ?
        ''', (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id))
        conn.commit()
        conn.close()

    def add_prize(self, user_id, prize_name, duration_hours):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        won_date = datetime.now()
        expires_date = won_date + timedelta(hours=duration_hours)
        cursor.execute('''
            INSERT INTO user_prizes (user_id, prize_name, won_date, expires_date)
            VALUES (?, ?, ?, ?)
        ''', (user_id, prize_name, 
              won_date.strftime("%Y-%m-%d %H:%M:%S"),
              expires_date.strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()

    def get_user_prizes(self, user_id):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT prize_name, won_date, expires_date, is_active 
            FROM user_prizes 
            WHERE user_id = ? 
            ORDER BY won_date DESC
        ''', (user_id,))
        prizes = []
        for row in cursor.fetchall():
            prizes.append({
                'name': row[0],
                'won_date': row[1],
                'expires_date': row[2],
                'is_active': bool(row[3])
            })
        conn.close()
        return prizes

    def get_prize_config(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, chance, duration_hours FROM prize_config')
        prizes = []
        for row in cursor.fetchall():
            prizes.append({
                'id': row[0],
                'name': row[1],
                'chance': row[2],
                'duration_hours': row[3]
            })
        conn.close()
        return prizes

    def add_prize_config(self, name, chance, duration_hours):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO prize_config (name, chance, duration_hours) VALUES (?, ?, ?)',
            (name, chance, duration_hours)
        )
        conn.commit()
        conn.close()

    def delete_prize_config(self, prize_id):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM prize_config WHERE id = ?', (prize_id,))
        conn.commit()
        conn.close()

    def get_all_users(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users')
        users = [row[0] for row in cursor.fetchall()]
        conn.close()
        return users

    def get_stats(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM user_prizes')
        total_prizes = cursor.fetchone()[0]
        today = datetime.now().strftime("%Y-%m-%d")
        cursor.execute('SELECT COUNT(*) FROM users WHERE registration_date LIKE ?', (f'{today}%',))
        users_today = cursor.fetchone()[0]
        conn.close()
        return {
            'total_users': total_users,
            'total_prizes': total_prizes,
            'users_today': users_today
        }

# Глобальные переменные
db = Database()
admin_states = {}

def is_admin(user_id):
    return user_id in ADMIN_IDS

def get_image_files():
    """Получить список JPG файлов в папке"""
    images = []
    for file in os.listdir(IMAGE_FOLDER):
        if file.lower().endswith(('.jpg', '.jpeg', '.png')):
            images.append(file)
    return images

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.register_user(user.id, user.username, user.first_name, user.last_name)
    await show_main_menu(update, context)

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Только для администраторов!")
        return
    await show_admin_menu(update, context)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("👤 Мой профиль", callback_data="profile")],
        [InlineKeyboardButton("🎁 Выиграть приз", callback_data="win_prize")],
        [InlineKeyboardButton("📦 Мои подарки", callback_data="my_prizes")],
        [InlineKeyboardButton("🖼️ Меню", callback_data="menu_images")],
        [InlineKeyboardButton("📞 Поддержка", callback_data="support")],
        [InlineKeyboardButton("🔥 Акции", callback_data="promotions")],
    ]
    
    user_id = update.effective_user.id if update.effective_user else update.callback_query.from_user.id
    if is_admin(user_id):
        keyboard.append([InlineKeyboardButton("⚙️ Админ-панель", callback_data="admin_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text("👋 Добро пожаловать! Выберите действие:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("👋 Добро пожаловать! Выберите действие:", reply_markup=reply_markup)

async def show_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎁 Добавить приз", callback_data="add_prize")],
        [InlineKeyboardButton("🗑️ Удалить приз", callback_data="delete_prize")],
        [InlineKeyboardButton("📋 Список призов", callback_data="view_prizes")],
        [InlineKeyboardButton("📢 Отправить уведомление", callback_data="send_notification")],
        [InlineKeyboardButton("🖼️ Управление изображениями", callback_data="manage_images")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "⚙️ **Панель администратора**\n\nВыберите действие:"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == "main_menu":
        await show_main_menu(update, context)
    elif query.data == "profile":
        await show_profile(update, context, user_id)
    elif query.data == "win_prize":
        await win_prize(update, context, user_id)
    elif query.data == "my_prizes":
        await show_my_prizes(update, context, user_id)
    elif query.data == "menu_images":
        await show_menu_images(update, context)
    elif query.data == "support":
        await show_support(update, context, user_id)
    elif query.data == "promotions":
        await show_promotions(update, context, user_id)
    elif query.data == "admin_menu":
        if not is_admin(user_id):
            await query.edit_message_text("❌ Только для администраторов!")
            return
        await show_admin_menu(update, context)
    elif query.data == "add_prize":
        if not is_admin(user_id):
            await query.edit_message_text("❌ Только для администраторов!")
            return
        await start_add_prize(update, context, user_id)
    elif query.data == "delete_prize":
        if not is_admin(user_id):
            await query.edit_message_text("❌ Только для администраторов!")
            return
        await show_delete_prize_menu(update, context, user_id)
    elif query.data.startswith("delete_prize_"):
        if not is_admin(user_id):
            await query.edit_message_text("❌ Только для администраторов!")
            return
        prize_id = int(query.data.split("_")[2])
        await delete_prize(update, context, user_id, prize_id)
    elif query.data == "view_prizes":
        if not is_admin(user_id):
            await query.edit_message_text("❌ Только для администраторов!")
            return
        await show_prize_list(update, context, user_id)
    elif query.data == "send_notification":
        if not is_admin(user_id):
            await query.edit_message_text("❌ Только для администраторов!")
            return
        await start_send_notification(update, context, user_id)
    elif query.data == "manage_images":
        if not is_admin(user_id):
            await query.edit_message_text("❌ Только для администраторов!")
            return
        await show_manage_images(update, context, user_id)
    elif query.data == "stats":
        if not is_admin(user_id):
            await query.edit_message_text("❌ Только для администраторов!")
            return
        await show_stats(update, context, user_id)

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    profile = db.get_user_profile(user_id)
    if profile:
        text = f"""📊 **Ваш профиль:**

👤 Имя: {profile['first_name']} {profile['last_name']}
📱 Username: {profile['username']}
📅 Регистрация: {profile['registration_date']}
🎁 Получено призов: {profile['prizes_count']}
⏰ Последняя игра: {profile['last_game_date']}"""
    else:
        text = "❌ Профиль не найден"
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]]
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def win_prize(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    if not db.can_play_today(user_id):
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]]
        await update.callback_query.edit_message_text(
            "⏰ Вы уже участвовали сегодня. Попробуйте завтра!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    prizes = db.get_prize_config()
    if not prizes:
        prize = {"name": "🎁 Базовый приз", "duration_hours": 24}
    else:
        rand = random.randint(1, 100)
        current_chance = 0
        for p in prizes:
            current_chance += p["chance"]
            if rand <= current_chance:
                prize = p
                break
        else:
            prize = prizes[0]
    
    db.add_prize(user_id, prize["name"], prize["duration_hours"])
    db.update_last_game(user_id)
    
    text = f"🎉 **Поздравляем!**\n\nВы выиграли: **{prize['name']}**\n⏰ Приз действует: {prize['duration_hours']} часов"
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]]
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def show_my_prizes(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    prizes = db.get_user_prizes(user_id)
    if not prizes:
        text = "📦 У вас пока нет призов"
    else:
        text = "📦 **Ваши призы:**\n\n"
        for i, prize in enumerate(prizes, 1):
            status = "✅ Активен" if prize['is_active'] else "❌ Неактивен"
            text += f"{i}. **{prize['name']}**\n"
            text += f"   🕐 Получен: {prize['won_date']}\n"
            text += f"   ⏰ Истекает: {prize['expires_date']}\n"
            text += f"   {status}\n\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]]
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def show_menu_images(update: Update, context: ContextTypes.DEFAULT_TYPE):
    images = get_image_files()
    if not images:
        text = "🖼️ Изображения меню пока не добавлены"
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]]
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    # Отправляем первое изображение
    image_path = os.path.join(IMAGE_FOLDER, images[0])
    try:
        with open(image_path, 'rb') as photo:
            await update.callback_query.message.reply_photo(
                photo=photo,
                caption="🖼️ Меню",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]])
            )
        await update.callback_query.delete_message()
    except Exception as e:
        await update.callback_query.edit_message_text(
            f"❌ Ошибка загрузки изображения: {e}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]])
        )

async def show_support(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    text = "📞 **Поддержка**\n\nПо всем вопросам обращайтесь: @yab2701"
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]]
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def show_promotions(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    text = """🔥 **Текущие акции:**

• 🎁 Скидка 15% на первый заказ
• 🚚 Бесплатная доставка при заказе от 1000 руб.
• ⭐ Специальные предложения для постоянных клиентов
• 💎 Участвуйте в розыгрышах каждый день!"""
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]]
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def start_add_prize(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    admin_states[user_id] = {"step": "waiting_prize_name"}
    keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="admin_menu")]]
    await update.callback_query.edit_message_text(
        "📝 **Добавление приза**\n\nВведите название приза:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def show_delete_prize_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    prizes = db.get_prize_config()
    if not prizes:
        text = "📭 Призы для удаления не найдены"
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_menu")]]
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    keyboard = []
    for prize in prizes:
        keyboard.append([InlineKeyboardButton(
            f"🗑️ {prize['name']} ({prize['chance']}%)", 
            callback_data=f"delete_prize_{prize['id']}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_menu")])
    
    text = "🗑️ **Удаление приза**\n\nВыберите приз для удаления:"
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def delete_prize(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, prize_id: int):
    prizes = db.get_prize_config()
    prize_name = next((p['name'] for p in prizes if p['id'] == prize_id), "Неизвестный приз")
    
    db.delete_prize_config(prize_id)
    
    text = f"✅ Приз **{prize_name}** успешно удален!"
    keyboard = [[InlineKeyboardButton("🔙 В админ-панель", callback_data="admin_menu")]]
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def show_prize_list(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    prizes = db.get_prize_config()
    if not prizes:
        text = "📭 Призы еще не настроены"
    else:
        text = "🎁 **Список призов:**\n\n"
        for i, prize in enumerate(prizes, 1):
            text += f"{i}. **{prize['name']}**\n"
            text += f"   🎯 Шанс: {prize['chance']}%\n"
            text += f"   ⏰ Длительность: {prize['duration_hours']}ч\n\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_menu")]]
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def start_send_notification(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    admin_states[user_id] = {"step": "waiting_notification_text"}
    keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="admin_menu")]]
    await update.callback_query.edit_message_text(
        "📢 **Отправка уведомления**\n\nВведите текст уведомления для всех пользователей:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def show_manage_images(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    images = get_image_files()
    text = "🖼️ **Управление изображениями**\n\n"
    
    if images:
        text += "📁 Текущие изображения:\n"
        for img in images:
            text += f"• {img}\n"
        text += "\n"
    else:
        text += "📭 Изображения не найдены\n\n"
    
    text += "📤 Чтобы добавить/заменить изображения, просто отправьте JPG/PNG файл в этот чат"
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_menu")]]
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    stats = db.get_stats()
    images_count = len(get_image_files())
    
    text = f"""📈 **Статистика бота:**

👥 Всего пользователей: {stats['total_users']}
🎁 Всего выдано призов: {stats['total_prizes']}
📅 Новых пользователей сегодня: {stats['users_today']}
🖼️ Изображений в меню: {images_count}"""
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_menu")]]
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Обработка документов (изображений) от админа
    if update.message.document or update.message.photo:
        if not is_admin(user_id):
            await update.message.reply_text("❌ Только администраторы могут загружать изображения!")
            return
        
        try:
            # Получаем файл
            if update.message.document:
                file = await update.message.document.get_file()
                file_extension = os.path.splitext(update.message.document.file_name)[1].lower()
            else:
                file = await update.message.photo[-1].get_file()
                file_extension = '.jpg'
            
            # Сохраняем файл
            filename = f"menu_image{file_extension}"
            file_path = os.path.join(IMAGE_FOLDER, filename)
            await file.download_to_drive(file_path)
            
            await update.message.reply_text(f"✅ Изображение успешно сохранено как: {filename}")
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка при сохранении изображения: {e}")
        return
    
    # Обработка текстовых сообщений для админских состояний
    if user_id not in admin_states:
        return
    
    state = admin_states[user_id]
    text = update.message.text
    
    if state["step"] == "waiting_prize_name":
        state["step"] = "waiting_prize_chance"
        state["name"] = text
        await update.message.reply_text("🎯 Введите шанс выпадения (1-100%):")
        
    elif state["step"] == "waiting_prize_chance":
        try:
            chance = int(text)
            if 1 <= chance <= 100:
                state["step"] = "waiting_prize_duration"
                state["chance"] = chance
                await update.message.reply_text("⏰ Введите длительность приза в часах:")
            else:
                await update.message.reply_text("❌ Шанс должен быть от 1 до 100%!")
        except ValueError:
            await update.message.reply_text("❌ Введите число!")
            
    elif state["step"] == "waiting_prize_duration":
        try:
            duration = int(text)
            if duration > 0:
                db.add_prize_config(state["name"], state["chance"], duration)
                del admin_states[user_id]
                await update.message.reply_text("✅ Приз успешно добавлен!")
            else:
                await update.message.reply_text("❌ Длительность должна быть больше 0!")
        except ValueError:
            await update.message.reply_text("❌ Введите число!")
    
    elif state["step"] == "waiting_notification_text":
        # Отправка уведомления всем пользователям
        users = db.get_all_users()
        success_count = 0
        fail_count = 0
        
        await update.message.reply_text(f"📢 Отправка уведомления {len(users)} пользователям...")
        
        for user_id in users:
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"📢 **Уведомление от администратора:**\n\n{text}",
                    parse_mode='Markdown'
                )
                success_count += 1
                # Небольшая задержка чтобы не превысить лимиты Telegram
                await asyncio.sleep(0.1)
            except Exception as e:
                print(f"Ошибка отправки пользователю {user_id}: {e}")
                fail_count += 1
        
        del admin_states[user_id]
        
        await update.message.reply_text(
            f"✅ Уведомление отправлено!\n"
            f"✅ Успешно: {success_count}\n"
            f"❌ Не удалось: {fail_count}"
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    try:
        raise context.error
    except NetworkError:
        print("🌐 Ошибка сети. Переподключение...")
    except TelegramError as e:
        print(f"📱 Ошибка Telegram: {e}")
    except Exception as e:
        print(f"💥 Неожиданная ошибка: {e}")

def main():
    """Основная функция запуска"""
    print("=" * 50)
    print("🤖 ЗАПУСК ТЕЛЕГРАМ БОТА")
    print("=" * 50)
    
    try:
        # Создаем application с настройками для плохого интернета
        application = (
            Application.builder()
            .token(BOT_TOKEN)
            .read_timeout(30)
            .write_timeout(30)
            .connect_timeout(30)
            .pool_timeout(30)
            .build()
        )
        
        # Добавляем обработчик ошибок
        application.add_error_handler(error_handler)
        
        # Добавляем обработчики команд
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("admin", admin_panel))
        
        patterns = [
            "main_menu", "profile", "win_prize", "my_prizes", "menu_images",
            "support", "promotions", "admin_menu", "add_prize", "delete_prize",
            "view_prizes", "send_notification", "manage_images", "stats"
        ]
        for pattern in patterns:
            application.add_handler(CallbackQueryHandler(button_handler, pattern=f"^{pattern}$"))
        
        # Обработчик для удаления призов
        application.add_handler(CallbackQueryHandler(button_handler, pattern="^delete_prize_"))
        
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, handle_message))
        
        print("✅ Бот инициализирован")
        print("📡 Запуск опроса...")
        print("=" * 50)
        print("💡 Напишите боту в Telegram:")
        print("   /start - основное меню")
        print("   /admin - админ-панель (если настроен ADMIN_ID)")
        print("=" * 50)
        
        if ADMIN_IDS[0] == 8378217976:
            print("⚠️  Замените ADMIN_ID на ваш ID из @userinfobot")
        
        # Запускаем бота с обработкой ошибок
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
        
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем")
    except Exception as e:
        print(f"💥 Критическая ошибка при запуске: {e}")
        print("🔄 Перезапуск через 5 секунд...")
        time.sleep(5)
        main()

if __name__ == "__main__":
    main()