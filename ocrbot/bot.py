from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import logging
from .config import BOT_TOKEN
from .commands.start import start
from .commands.help import help
from .commands.invalid_command import invalid_command
from .handlers.extract_image import extract_image

# Включаем логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    updater.bot.set_my_commands([
        ("start", "Запустить бота"),
        ("help", "Список команд")
    ])

    dp = updater.dispatcher
    dp.add_handler(CommandHandler('start', start, run_async=True))
    dp.add_handler(CommandHandler('help', help, run_async=True))
    dp.add_handler(MessageHandler(Filters.photo, extract_image, run_async=True))
    dp.add_handler(MessageHandler(Filters.command, invalid_command, run_async=True))

    updater.start_polling(drop_pending_updates=True)
    print("Бот запущен ✅")
    updater.idle()
