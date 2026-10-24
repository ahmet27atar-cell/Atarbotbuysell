"""
TradingView -> Telegram köprüsü
--------------------------------
TradingView'den gelen webhook alert'lerini alır ve Telegram'a mesaj olarak iletir.

Ortam değişkenleri (environment variables):
  TELEGRAM_BOT_TOKEN  : BotFather'dan aldığın token
  TELEGRAM_CHAT_ID    : Mesajın gideceği chat/grup ID'si
  WEBHOOK_SECRET      : (opsiyonel ama önerilir) TradingView mesajının içinde
                        olması gereken gizli anahtar. Başkalarının seni
                        sahte sinyallerle bombalamasını engeller.

Çalıştırma:
  pip install -r requirements.txt
  python webhook_to_telegram.py

Deploy (Render/Railway gibi servislerde):
  Start command: gunicorn webhook_to_telegram:app
"""

import os
import logging
from flask import Flask, request, jsonify
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tv2tg")

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")


def send_telegram_message(text: str) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error("TELEGRAM_BOT_TOKEN veya TELEGRAM_CHAT_ID tanımlı değil.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        if not r.ok:
            logger.error("Telegram API hatası: %s - %s", r.status_code, r.text)
        return r.ok
    except requests.RequestException as e:
        logger.exception("Telegram'a istek atılırken hata oluştu: %s", e)
        return False


@app.route("/webhook", methods=["POST"])
def webhook():
    raw_body = request.get_data(as_text=True)
    logger.info("Gelen webhook: %s", raw_body)

    # Güvenlik: secret anahtar mesajda geçmiyorsa reddet
    if WEBHOOK_SECRET and WEBHOOK_SECRET not in raw_body:
        logger.warning("Geçersiz/eksik secret ile istek geldi, reddedildi.")
        return jsonify({"status": "unauthorized"}), 401

    # TradingView mesajı JSON ya da düz metin olarak gönderebilir
    message_text = raw_body
    try:
        payload = request.get_json(force=True, silent=True)
        if payload and isinstance(payload, dict) and "message" in payload:
            message_text = payload["message"]
    except Exception:
        pass  # düz metin olarak devam et

    ok = send_telegram_message(message_text)
    if ok:
        return jsonify({"status": "sent"}), 200
    return jsonify({"status": "failed"}), 500


@app.route("/", methods=["GET"])
def health():
    return "OK - webhook ayakta", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
