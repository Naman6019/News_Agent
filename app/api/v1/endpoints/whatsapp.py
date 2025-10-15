"""
WhatsApp endpoints for testing and managing WhatsApp functionality
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime

from app.services.whatsapp import WhatsAppService
from app.services.news_service import NewsService

router = APIRouter()
whatsapp_service = WhatsAppService()
news_service = NewsService()


@router.post("/test")
async def test_whatsapp():
    """Send a test message via WhatsApp."""
    try:
        success = await whatsapp_service.send_test_message()

        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to send test message"
            )

        return {
            "message": "Test message sent successfully",
            "timestamp": datetime.now().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending test message: {str(e)}")


@router.post("/send-digest")
async def send_whatsapp_digest(delivery_time: str = "morning"):
    """Manually send a news digest via WhatsApp."""
    try:
        if delivery_time not in ["morning", "evening"]:
            raise HTTPException(
                status_code=400,
                detail="delivery_time must be 'morning' or 'evening'"
            )

        # Generate digest with delivery time
        digest = await news_service.generate_daily_digest(delivery_time)

        if not digest:
            raise HTTPException(
                status_code=404,
                detail="No news content available for digest"
            )

        # Send via WhatsApp
        success = await whatsapp_service.send_news_digest(digest, delivery_time)

        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to send digest via WhatsApp"
            )

        return {
            "message": f"{delivery_time.title()} news digest sent successfully via WhatsApp",
            "delivery_time": delivery_time,
            "timestamp": datetime.now().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending digest: {str(e)}")


@router.get("/validate")
async def validate_whatsapp_config():
    """Validate WhatsApp configuration."""
    try:
        validation = whatsapp_service.validate_phone_numbers()

        return {
            "validation": validation,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error validating configuration: {str(e)}")


@router.post("/send-custom")
async def send_custom_message(message: str):
    """Send a custom message via WhatsApp."""
    try:
        if not message.strip():
            raise HTTPException(
                status_code=400,
                detail="Message cannot be empty"
            )

        success = await whatsapp_service.send_message(message)

        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to send custom message"
            )

        return {
            "message": "Custom message sent successfully",
            "timestamp": datetime.now().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending custom message: {str(e)}")