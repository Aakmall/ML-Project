# ============================================================
# 🤖 WhatsApp AI Gizi Anak – Flask Webhook Server (Group & Personal, Markdown Rapi)
# ============================================================
from flask import Flask, request, jsonify
import requests
import google.generativeai as genai
import logging
import os
import re

# ------------------------------------------------------------
# 🔧 KONFIGURASI DASAR
# ------------------------------------------------------------
app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("whatsapp-bot.log"),
        logging.StreamHandler()
    ]
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyDdYeOAOohUwcSrb1gLLHpfb7sBfmrETVM")
FONNTE_TOKEN = os.getenv("FONNTE_TOKEN", "uqMuVhM4YKzujVg38BiB")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

# ------------------------------------------------------------
# 🧠 FUNGSI RESPON AI
# ------------------------------------------------------------
def get_ai_response(user_message: str) -> str:
    """
    Menghasilkan jawaban AI seputar program kehamilan dan perkembangan janin
    maksimal 200 kata, markdown rapi untuk WhatsApp tanpa **
    """
    try:
        prompt = f"""
Anda adalah AI-Pendamping-Ibu-Hamil, asisten edukasi bagi ibu hamil.

Fokus Utama:
- Perkembangan janin per minggu
- Ukuran dan berat bayi
- Pembentukan organ
- Gejala umum yang dirasakan ibu
- Tips kesehatan, nutrisi, dan perawatan diri selama hamil
- Informasi perubahan tubuh ibu per minggu kehamilan

Aturan:
- Jawab maksimal 200 kata.
- Gunakan format rapi agar mudah dibaca di WhatsApp.
- Jika pertanyaan di luar topik kehamilan, jawab:
  "Maaf, saya hanya bisa membantu seputar informasi kehamilan dan perkembangan janin."
- Gaya bahasa: ramah, sopan, hangat, dan menenangkan.
- Jika user menyapa (halo, hai, dsb), sambut hangat lalu arahkan ke topik kehamilan.
- Jika user menyebut minggu kehamilan tertentu, jelaskan perkembangan janin dan kondisi ibu pada minggu tersebut.
- Hindari penggunaan tanda ** atau -- dalam jawaban.
Contoh Pertanyaan:
- "Apa yang terjadi pada janin di minggu ke-12?"
- "Berapa ukuran bayi di minggu ke-20?"
- "Apa saja gejala umum di trimester pertama?"
- "Bagaimana cara menjaga kesehatan selama kehamilan?"
- "Apa saja perubahan tubuh yang terjadi pada ibu hamil di minggu ke-30?"

Pesan pengguna:
"{user_message}"
"""
        response = model.generate_content(
            prompt,
            request_options={"timeout": 30}
        )
        text = response.text.strip()
        words = text.split()
        if len(words) > 200:
            text = " ".join(words[:200]) + "..."
        # hapus tanda ** atau -- jika ada
        text = text.replace("**", "").replace("--", "")
        return text
    except Exception as e:
        logging.error(f"⚠️ Error dari Gemini: {e}")
        return "_Maaf, sistem sedang sibuk. Coba lagi nanti ya._"

# ------------------------------------------------------------
# 📤 KIRIM PESAN KE FONNTE
# ------------------------------------------------------------
def send_message_to_fonnte(phone: str, message: str):
    url = "https://api.fonnte.com/send"
    headers = {"Authorization": FONNTE_TOKEN}
    data = {"target": phone, "message": message, "countryCode": "62"}

    try:
        resp = requests.post(url, headers=headers, data=data, timeout=10)
        resp.raise_for_status()
        logging.info(f"✅ Balasan terkirim ke {phone}: {message[:60]}...")
        return resp.json()
    except Exception as e:
        logging.error(f"❌ Gagal kirim pesan ke Fonnte: {e}")
        return {"sent": False, "error": str(e)}

# ------------------------------------------------------------
# 🌐 WEBHOOK FONNTE UNTUK TERIMA PESAN
# ------------------------------------------------------------
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return jsonify({"ok": True, "message": "Webhook aktif."})

    try:
        payload = request.get_json(force=True)
        logging.info(f"📩 Pesan masuk: {payload}")

        sender = payload.get("sender") or payload.get("from") or payload.get("number")
        message = payload.get("message") or payload.get("text")
        is_group = payload.get("isgroup", False)
        group_id = payload.get("sender") if is_group else None

        if not sender or not message:
            return jsonify({"ok": False, "error": "Payload tidak valid"}), 400

        message_lower = message.lower().strip()
        sapaan = ["halo", "hai", "hallo", "pagi", "siang", "malam", "hey", "hei"]

        # 🔹 Trigger mention @aigizi untuk group
        trigger = "@aigizi"
        if trigger in message_lower:
            user_message = message_lower.replace(trigger, "").strip()
            ai_reply = get_ai_response(user_message)
            target = group_id if is_group else sender
            send_result = send_message_to_fonnte(target, ai_reply)

        elif any(word in message_lower for word in sapaan):
            ai_reply = (
                "👋 Hai! Saya AI-Gizi-Anak, asisten edukasi kesehatan.\n\n"
                "Saya siap bantu kamu memahami seputar gizi anak, stunting, dan nutrisi seimbang.\n"
                "Silakan tanya apa yang ingin kamu ketahui 😊"
            )
            target = group_id if is_group else sender
            send_result = send_message_to_fonnte(target, ai_reply)

        else:
            ai_reply = get_ai_response(message)
            target = group_id if is_group else sender
            send_result = send_message_to_fonnte(target, ai_reply)

        return jsonify({"ok": True, "sent": send_result}), 200

    except Exception as e:
        logging.error(f"💥 Error di webhook: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

# ------------------------------------------------------------
# 🚀 JALANKAN SERVER
# ------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logging.info(f"🚀 WhatsApp AI-Gizi-Anak aktif di port {port}")
    app.run(host="0.0.0.0", port=port)
