# 🤖 WhatsApp PregnaBot –
from flask import Flask, request, jsonify
import requests
import google.generativeai as genai
import logging
import os
from datetime import datetime, timedelta

app = Flask(__name__)

# Konfigurasi Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("whatsapp-bot.log"),
        logging.StreamHandler()
    ]
)

# Konfigurasi API Key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyBTby5ifvkFIJgCuegEcUbzkXrpAFh0654")
FONNTE_TOKEN = os.getenv("FONNTE_TOKEN", "xFq3eM7QRWXfnhzJrXLg")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")


def calculate_hpl(hpht_str: str) -> str:
    """
    Menghitung Hari Perkiraan Lahir (HPL) berdasarkan HPHT (Hari Pertama Haid Terakhir).
    Rumus Naegele:
    - Hari + 7
    - Bulan - 3 (atau +9)
    - Tahun + 1 (jika bulan > 3)
    """
    try:
        # Format tanggal input: DD-MM-YYYY
        hpht = datetime.strptime(hpht_str, "%d-%m-%Y")
        
        # Hitung HPL
        # Cara simpel: HPHT + 280 hari (40 minggu)
        hpl = hpht + timedelta(days=280)
        
        # Hitung usia kehamilan saat ini
        today = datetime.now()
        age_days = (today - hpht).days
        age_weeks = age_days // 7
        age_remainder_days = age_days % 7
        
        return (
            f"📅 *Kalkulator Kehamilan*\n"
            f"HPHT: {hpht.strftime('%d-%m-%Y')}\n"
            f"HPL (Perkiraan Lahir): {hpl.strftime('%d-%m-%Y')}\n"
            f"Usia Kehamilan: {age_weeks} minggu {age_remainder_days} hari\n\n"
            f"Semoga ibu dan janin sehat selalu! 💖"
        )
    except ValueError:
        return "⚠️ Format tanggal salah. Gunakan format DD-MM-YYYY. Contoh: !hpl 01-01-2024"


def get_ai_response(user_message: str) -> str:
    """
    Menghasilkan jawaban AI dengan persona PregnaBot.
    """
    try:
        prompt = f"""
Anda adalah **PregnaBot**, asisten pribadi virtual yang ramah, hangat, dan empatik khusus untuk ibu hamil.
Nama kamu adalah PregnaBot.

Tugas Utama:
1. Menjawab pertanyaan seputar kehamilan, perkembangan janin, nutrisi, dan kesehatan ibu hamil.
2. Memberikan dukungan emosional yang menenangkan.
3. Jawaban harus **RINGKAS**, **PADAT**, dan **JELAS**. Maksimal 150 kata.
4. Gunakan emoji yang relevan (👶, 🤰, 💖, ✨) agar pesan terasa personal.

Aturan Penting:
- Jangan gunakan tanda ** (bold markdown) karena kadang tidak rapi di beberapa perangkat, gunakan plain text atau emoji saja.
- Jika ditanya soal medis serius (pendarahan, nyeri hebat), sarankan segera ke dokter.
- Jika user menyapa, balas dengan ramah sebagai PregnaBot.

Pertanyaan User:
"{user_message}"

Jawab sebagai PregnaBot:
"""
        response = model.generate_content(
            prompt,
            request_options={"timeout": 30}
        )
        text = response.text.strip()
        
        # Bersihkan markdown bold jika masih ada
        text = text.replace("**", "")
        
        return text
    except Exception as e:
        error_msg = str(e)
        logging.error(f"⚠️ Error dari Gemini: {error_msg}")
        
        # Cek apakah error karena limit kuota (429)
        if "429" in error_msg or "Resource has been exhausted" in error_msg:
            return "Maaf Bunda, kuota harian PregnaBot sudah habis. Silakan tanya lagi besok ya! 💖"
        
        return "Maaf Bunda, PregnaBot sedang pusing sedikit. Bisa ulangi pertanyaannya? 🤕"


def send_message_to_fonnte(phone: str, message: str):
    url = "https://api.fonnte.com/send"
    headers = {"Authorization": FONNTE_TOKEN}
    data = {"target": phone, "message": message, "countryCode": "62"}

    try:
        resp = requests.post(url, headers=headers, data=data, timeout=10)
        resp.raise_for_status()
        logging.info(f"✅ Balasan terkirim ke {phone}")
        return resp.json()
    except Exception as e:
        logging.error(f"❌ Gagal kirim pesan ke Fonnte: {e}")
        return {"sent": False, "error": str(e)}


@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return jsonify({"ok": True, "message": "PregnaBot Webhook Aktif 🤰"})

    try:
        payload = request.get_json(force=True)
        logging.info(f"📩 Pesan masuk: {payload}")

        sender = payload.get("sender") or payload.get("from") or payload.get("number")
        message = payload.get("message") or payload.get("text")
        is_group = payload.get("isgroup", False)
        group_id = payload.get("sender") if is_group else None
        
        if not sender or not message:
            return jsonify({"ok": False, "error": "Payload tidak valid"}), 400

        message_original = message.strip()
        message_lower = message.lower().strip()
        
        # Tentukan target balasan
        target = group_id if is_group else sender
        ai_reply = ""

        # 1. Fitur Cek HPL (!hpl DD-MM-YYYY)
        if message_lower.startswith("!hpl"):
            parts = message_original.split()
            if len(parts) > 1:
                date_str = parts[1]
                ai_reply = calculate_hpl(date_str)
            else:
                ai_reply = "Untuk cek HPL, ketik: !hpl TANGGAL-HPHT\nContoh: !hpl 25-12-2023"

        # 2. Fitur Menu / Bantuan
        elif message_lower in ["!menu", "!help", "menu", "help", "bantuan"]:
            ai_reply = (
                "🌸 **Menu PregnaBot** 🌸\n\n"
                "🤰 **Tanya Jawab**: Ketik pertanyaan apa saja seputar kehamilan.\n"
                "📅 **Cek HPL**: Ketik `!hpl DD-MM-YYYY` (contoh: `!hpl 01-01-2024`)\n"
                "✨ **Tips**: Tanyakan 'Tips minggu ini' untuk info sesuai usia kehamilan.\n\n"
                "Semoga sehat selalu Bunda! 💖"
            )

        # 3. Chatbot AI (PregnaBot)
        else:
            # Logic untuk grup: hanya balas jika di-mention
            if is_group:
                trigger = "@aiPregnaBot" # Sesuaikan jika perlu
                if trigger in message_original:
                    clean_msg = message_original.replace(trigger, "").strip()
                    ai_reply = get_ai_response(clean_msg)
            else:
                # Personal chat: balas semua
                ai_reply = get_ai_response(message_original)

        # Kirim balasan jika ada
        if ai_reply:
            send_result = send_message_to_fonnte(target, ai_reply)
            return jsonify({"ok": True, "sent": send_result}), 200
        else:
            return jsonify({"ok": True, "ignored": True}), 200

    except Exception as e:
        logging.error(f"💥 Error di webhook: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"🤰 PregnaBot siap melayani di port {port}...")
    app.run(host="0.0.0.0", port=port)
