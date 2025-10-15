import os
import requests
from datetime import datetime

def get_base_url():
    """
    Determine the base API URL.
    - Uses localhost when running locally.
    - Uses the Render public URL in production.
    """
    render_service_url = os.getenv("RENDER_EXTERNAL_URL")  # Render sets this automatically
    if render_service_url:
        return render_service_url.rstrip("/")
    return "http://localhost:8000"  # Local default

def get_delivery_time():
    """Return 'morning' or 'evening' based on the current time."""
    hour = datetime.now().hour
    return "morning" if hour < 12 else "evening"

def main():
    print("🚀 Starting news digest job...")
    base_url = get_base_url()
    delivery_time = get_delivery_time()

    digest_url = f"{base_url}/api/v1/news/digest?delivery_time={delivery_time}"
    print(f"Fetching digest from {digest_url}")

    try:
        response = requests.get(digest_url, timeout=20)
        response.raise_for_status()
    except Exception as e:
        print(f"❌ Failed to fetch digest: {e}")
        return

    digest_data = response.json() if response.content else None

    if not digest_data:
        print("❌ No digest data found, aborting.")
        return

    print("✅ Digest fetched successfully.")

    # If you’re sending via Twilio or another service, you can trigger it here:
    # send_via_twilio(digest_data)

    print("✅ News digest job completed successfully!")

if __name__ == "__main__":
    main()
