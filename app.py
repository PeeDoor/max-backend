import os
import json
import gspread
from google.oauth2.service_account import Credentials
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# ==================== НАСТРОЙКИ (через переменные окружения) ====================
MAX_BOT_TOKEN = os.environ.get("MAX_BOT_TOKEN")
MAX_CHAT_ID = os.environ.get("MAX_CHAT_ID")
GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID")

# ==================== ПОДКЛЮЧЕНИЕ К GOOGLE SHEETS ====================
def get_google_client():
    # Читаем JSON-ключ из переменной окружения (передадим как строку)
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if not creds_json:
        # Если переменная не задана, пробуем прочитать локальный файл (для теста)
        with open("google-credentials.json", "r") as f:
            creds_json = f.read()

    creds_dict = json.loads(creds_json)
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly"
    ]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)


# ==================== ЭНДПОИНТ: ПОЛУЧИТЬ ОПЦИИ ====================
@app.route("/get-options", methods=["GET"])
def get_options():
    try:
        client = get_google_client()
        ss = client.open_by_key(GOOGLE_SHEET_ID)

        # Список названий листов (машин)
        machines = [
            "Ампульная машина", "Флаконажка", "Этикетировщик",
            "П/а розлив", "Саше машина жидкая", "Упаковка",
            "Маркировка Честный Знак", "Котел 200 л",
            "Котел 300 л", "Котел 1 000 л"
        ]

        result = []
        for idx, name in enumerate(machines):
            try:
                sheet = ss.worksheet(name)
                # Читаем столбец A, начиная с A2
                values = sheet.col_values(1)[1:]  # пропускаем заголовок
                # Убираем пустые и дубликаты
                seen = set()
                options = []
                for v in values:
                    v = str(v).strip()
                    if v and v not in seen:
                        seen.add(v)
                        options.append(v)
                result.append({"index": idx, "title": name, "options": options})
            except Exception as e:
                result.append({"index": idx, "title": name, "options": [], "error": str(e)})

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== ЭНДПОИНТ: ОТПРАВИТЬ В MAX ====================
@app.route("/send-to-max", methods=["POST"])
def send_to_max():
    try:
        data = request.get_json()
        text = data.get("text", "")

        if not text:
            return jsonify({"error": "Empty text"}), 400

        url = f"https://platform-api2.max.ru/messages?chat_id={MAX_CHAT_ID}"
        headers = {
            "Authorization": MAX_BOT_TOKEN,  # БЕЗ "Bearer" [citation:18]
            "Content-Type": "application/json"
        }
        payload = {
            "text": text,
            "format": "html",
            "notify": True
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        return jsonify({"status": resp.status_code, "response": resp.text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== ТЕСТОВЫЙ ЭНДПОИНТ ====================
@app.route("/")
def index():
    return "MAX Backend is running"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))