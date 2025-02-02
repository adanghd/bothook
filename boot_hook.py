import requests
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext
import os

# Token Configuration
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")  # Replace with your actual token or set as environment variable
GEMINI_API_KEY = os.getenv("AIzaSyBqZpyxT9P5piAQ0q8zP_tItPm3mEGmV08")  
bot = Bot(token=TELEGRAM_TOKEN)

# Function to fetch hooks from Gemini API
def fetch_hooks(category: str, style: str) -> list:
    api_url = "https://api.gemini.com/hooks"
    response = requests.post(api_url, json={"category": category, "style": style}, headers={"Authorization": f"Bearer {GEMINI_API_KEY}"})
    if response.status_code == 200:
        return response.json().get("hooks", [])
    return ["Maaf, tidak bisa mendapatkan hook saat ini."]

# Start command handler
def start(update: Update, context: CallbackContext) -> None:
    keyboard = [[InlineKeyboardButton("Cari Hook", callback_data='hook')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Selamat datang di chatbot hook konten affiliate! Klik tombol di bawah untuk mulai.', reply_markup=reply_markup)

# Hook menu handler
def handle_hook(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    keyboard = [
        [InlineKeyboardButton("Fashion Wanita", callback_data='category_fashion_wanita')],
        [InlineKeyboardButton("Kembali", callback_data='start')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text="Pilih kategori konten:", reply_markup=reply_markup)

# Handle category selection
def handle_category(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    category = query.data.split('_')[1]
    keyboard = [
        [InlineKeyboardButton("Gaya Santai", callback_data=f'style_{category}_santai')],
        [InlineKeyboardButton("Bahasa Sesuai Audience", callback_data=f'style_{category}_audience')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text="Pilih gaya bahasa:", reply_markup=reply_markup)

# Handle style selection and fetch hooks
def handle_style(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    _, category, style = query.data.split('_')
    hooks = fetch_hooks(category, style)
    hook_text = "\n\n".join(hooks)
    keyboard = [
        [InlineKeyboardButton("Tambah Hook", callback_data=f'add_{category}_{style}')],
        [InlineKeyboardButton("Selesai", callback_data='end')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text=f"Berikut 5 hook untuk kategori {category} dengan gaya {style}:\n\n{hook_text}", reply_markup=reply_markup)

# Add more hooks
def handle_add_hooks(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    _, category, style = query.data.split('_')
    hooks = fetch_hooks(category, style)
    hook_text = "\n\n".join(hooks)
    keyboard = [
        [InlineKeyboardButton("Tambah Hook", callback_data=f'add_{category}_{style}')],
        [InlineKeyboardButton("Selesai", callback_data='end')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text=f"Berikut tambahan 5 hook:\n\n{hook_text}", reply_markup=reply_markup)

# End interaction
def handle_end(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    query.edit_message_text(text="Terima kasih telah menggunakan chatbot hook konten affiliate!")

# Main function to set up handlers
def main() -> None:
    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CallbackQueryHandler(handle_hook, pattern='^hook$'))
    dispatcher.add_handler(CallbackQueryHandler(handle_category, pattern='^category_'))
    dispatcher.add_handler(CallbackQueryHandler(handle_style, pattern='^style_'))
    dispatcher.add_handler(CallbackQueryHandler(handle_add_hooks, pattern='^add_'))
    dispatcher.add_handler(CallbackQueryHandler(handle_end, pattern='^end$'))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
