# URL для GitHub Pages
GITHUB_PAGES_URL = "https://mocardv-boop.github.io/Telegram_bot"

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("👤 Мой профиль", callback_data="profile")],
        [InlineKeyboardButton("🎁 Выиграть приз", callback_data="win_prize")],
        [InlineKeyboardButton("📦 Мои подарки", callback_data="my_prizes")],
        [InlineKeyboardButton("📱 Открыть Mini App", web_app=WebAppInfo(url=GITHUB_PAGES_URL))],
        [InlineKeyboardButton("📞 Поддержка", callback_data="support")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("👋 Добро пожаловать!", reply_markup=reply_markup)
