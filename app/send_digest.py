"""
send_digest.py
------------------
Triggered by Render Cron Job.
Fetches the latest news digest and sends it via WhatsApp using Twilio.
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Configuration ---
API_URL = os.getenv("SERVER_HOST", "http://localhost:8000")
DELIVERY_TIME = "morning"  # or "evening"

# Twilio credentials
TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
WHATSAPP_TO = os.getenv("WHATSAPP_RECIPIENT_NUMBER")

def fetch_news_digest():
    """Fetches the latest news digest from your own API."""
    try:
        url = f"{API_URL}/api/v1/news/digest?delivery_time={DELIVERY_TIME}"
        print(f"Fetching digest from {url}")
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Failed to fetch digest: {e}")
        return None

def send_whatsapp_message(message):
    """Sends the digest via Twilio WhatsApp."""
    try:
        from twilio.rest import Client
        client = Client(TWILIO_SID, TWILIO_AUTH)
        message = client.messages.create(
            body=message,
            from_=f"whatsapp:{TWILIO_NUMBER}",
            to=f"whatsapp:{WHATSAPP_TO}",
        )
        print(f"✅ WhatsApp message sent successfully (SID: {message.sid})")
    except Exception as e:
        print(f"❌ Failed to send WhatsApp message: {e}")

def main():
    print("🚀 Starting news digest job...")
    digest_data = fetch_news_digest()

    if not digest_data or "digest" not in digest_data:
        print("❌ No digest data found, aborting.")
        return

    message = digest_data["digest"]
    print("📰 Sending WhatsApp message...")
    send_whatsapp_message(message)
    print("✅ Job completed successfully.")

if __name__ == "__main__":
    main()
