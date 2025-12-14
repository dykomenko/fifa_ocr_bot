from ocrbot.helpers.decorators import send_typing_action
from ocrbot.helpers.mock_database import insert_file_path
from telegram import Update
from telegram.ext import CallbackContext
import re
import requests
import unicodedata
import traceback
from ocrbot.config import API_KEY


@send_typing_action
def extract_image(update: Update, context: CallbackContext):
    """
    Принимает фото, сразу отправляет в OCR и возвращает распознанный текст.
    """
    chat_id = update.effective_chat.id
    file_id = update.message.photo[-1].file_id

    # Получаем ссылку на изображение
    new_file = context.bot.get_file(file_id)
    file_path = new_file.file_path
    insert_file_path(chat_id, update.message.message_id, file_path)

    # Отправляем сообщение о начале обработки
    processing_message = update.message.reply_text("🕐 Распознаю текст, пожалуйста подождите...")

    try:
        # Запрос к OCR.Space
        response = requests.get(
            "https://api.ocr.space/parse/imageurl",
            params={
                "apikey": API_KEY,
                "url": file_path,
                "language": "rus",
                "detectOrientation": True,
                "filetype": "JPG",
                "OCREngine": 1,
                "isTable": True,
                "scale": True
            },
            timeout=30
        )

        response.encoding = 'utf-8'
        data = response.json()

        if not data.get("IsErroredOnProcessing", True):
            raw_text = data['ParsedResults'][0].get('ParsedText', '').strip()

            # --- Обработка Unicode (исправляем é, ł, ü и т.д.) ---
            text = unicodedata.normalize("NFKC", raw_text)
            text = text.encode('utf-8', 'ignore').decode('utf-8', 'ignore')
            text = re.sub(r'[\r\n]+', '\n', text)  # аккуратная очистка переносов строк
            text = text.strip()

            print(f"[DEBUG OCR TEXT]\n{text}")  # отладочный вывод

            if not text:
                processing_message.edit_text("⚠️ Текст не найден на изображении.")
                return

            # --- Поиск фамилий (латинских слов) ---
            # \b[^\W\dА-Яа-яЁё]+\b — латинские слова без цифр и кириллицы
            pattern = re.compile(r"\b[^\W\dА-Яа-яЁё]+\b", re.UNICODE)
            names = pattern.findall(text)

            banlist = {"Старт", "цена", "Продан", "за", "Купить",
                       "сейчас", "Время", "Просрочено", "О", "V", "Profit"}
            names = [w for w in names if w not in banlist and len(w) > 2]

            if names:
                text_out = '\n'.join(names)
                # Для Telegram убеждаемся, что текст безопасен
                safe_text = text_out.encode('utf-8', 'ignore').decode('utf-8', 'ignore')
                processing_message.edit_text(f"{safe_text}")
            else:
                # Если фамилии не найдены — отправляем весь текст
                safe_text = text.encode('utf-8', 'ignore').decode('utf-8', 'ignore')
                processing_message.edit_text(f"📄 Распознанный текст:\n\n{safe_text}")

        else:
            err_msg = data.get('ErrorMessage') or "Неизвестная ошибка OCR"
            processing_message.edit_text(f"⚠️ Ошибка OCR: {err_msg}")

    except Exception as e:
        print("=== OCR ERROR ===")
        print(e)
        print(traceback.format_exc())
        processing_message.edit_text("🚫 Произошла ошибка при обработке. Попробуйте снова позже.")
