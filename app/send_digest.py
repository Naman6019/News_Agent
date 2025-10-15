import os
import requests
from datetime import datetime
from twilio.rest import Client

def get_delivery_time():
    """Determine delivery time based on IST."""
    ist_hour = (datetime.utcnow().hour + 5) % 24  # UTC→IST
    if 5 <= ist_hour < 12:
        return "morning"
    elif 17 <= ist_hour < 22:
        return "evening"
    else:
        return None  # skip sending during off hours

def get_greeting(delivery_time):
    return "Good morning" if delivery_time == "morning" else "Good evening"

def fetch_digest(api_url, delivery_time):
    """Fetch digest from API."""
    try:
        print(f"🚀 Fetching {delivery_time} digest from {api_url}")
        response = requests.get(f"{api_url}/api/v1/news/digest?delivery_time={delivery_time}", timeout=30)
        response.raise_for_status()
        data = response.json()
        print("✅ Digest fetched successfully.")
        return data
    except Exception as e:
        print(f"❌ Failed to fetch digest: {e}")
        return None

def send_whatsapp_message(account_sid, auth_token, from_number, to_number, message):
    """Send WhatsApp message via Twilio."""
    try:
        client = Client(account_sid, auth_token)
        msg = client.messages.create(
            from_=f"whatsapp:{from_number}",
            to=f"whatsapp:{to_number}",
            body=message
        )
        print(f"✅ Message sent successfully (SID: {msg.sid})")
    except Exception as e:
        print(f"❌ Failed to send WhatsApp message: {e}")

def format_message(digest_data, delivery_time):
    """Format the digest into a WhatsApp message."""
    greeting = get_greeting(delivery_time)
    date_str = datetime.now().strftime("%d/%m/%Y")
    header = f"📰 *{greeting}! Here's your {delivery_time.capitalize()} News Digest*\n📅 {date_str}\n\n"

    body = ""
    if "articles" in digest_data:
        for i, article in enumerate(digest_data["articles"][:5], 1):
            title = article.get("title", "Untitled")
            summary = article.get("summary", "")
            link = article.get("link", "#")
            body += f"{i}. *{title}*\n_{summary}_\n🔗 {link}\n\n"
    else:
        body = "No articles found.\n\n"

    footer = "_Powered by Ollama & AI News Agent_"
    return header + body + footer

def main():
    api_url = os.getenv("API_URL", "https://news-agent-three.vercel.app")
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_PHONE_NUMBER", "+14155238886")
    to_number = os.getenv("WHATSAPP_RECIPIENT_NUMBER", "+918530356515")

    delivery_time = get_delivery_time()
    if not delivery_time:
        print("⏰ Not morning or evening — skipping send.")
        return

    digest_data = fetch_digest(api_url, delivery_time)
    if digest_data:
        message = format_message(digest_data, delivery_time)
        send_whatsapp_message(account_sid, auth_token, from_number, to_number, message)
    else:
        print("❌ No digest data found. Aborting WhatsApp send.")

if __name__ == "__main__":
    main()
