"""
WhatsApp Message Service using Twilio API
Handles sending formatted news messages via WhatsApp
"""

import asyncio
from typing import List, Optional

from twilio.rest import Client
from twilio.base.exceptions import TwilioException

from app.core.config import settings
from app.core.logging import StructuredLogger


class WhatsAppService:
    """Service for sending WhatsApp messages via Twilio."""

    def __init__(self):
        self.logger = StructuredLogger(__name__)

        # Check if Twilio is configured
        if not all([
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN,
            settings.TWILIO_PHONE_NUMBER,
            settings.WHATSAPP_RECIPIENT_NUMBER
        ]):
            self.logger.warning("Twilio credentials not configured - WhatsApp service disabled")
            self.client = None
            self.from_number = None
            self.to_number = None
            return

        try:
            self.client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            self.from_number = f"whatsapp:{settings.TWILIO_PHONE_NUMBER}"
            self.to_number = f"whatsapp:{settings.WHATSAPP_RECIPIENT_NUMBER}"
            self.logger.info("WhatsApp service initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize WhatsApp service: {e}")
            self.client = None
            self.from_number = None
            self.to_number = None

    async def send_message(self, message: str) -> bool:
        """Send a WhatsApp message with fallback for 24-hour session expiry."""
        if not self.client:
            self.logger.warning("WhatsApp service not configured - message not sent")
            return False

        try:
            self.logger.info(f"Sending WhatsApp message to {self.to_number}")

            # Run Twilio API call in executor to avoid blocking
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.messages.create(
                    body=message,
                    from_=self.from_number,
                    to=self.to_number
                )
            )

            self.logger.info("WhatsApp message sent successfully")
            return True

        except Exception as e:
            # Handle 24-hour session restriction (error 63016)
            if hasattr(e, "code") and e.code == 63016:
                self.logger.warning("Session expired — sending WhatsApp template message fallback")

                try:
                    await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: self.client.messages.create(
                            from_=self.from_number,
                            to=self.to_number,
                            persistent_action=['template:hello_world']
                        )
                    )
                    self.logger.info("Template message sent successfully (fallback)")
                    return True
                except Exception as template_error:
                    self.logger.error(f"Failed to send template fallback: {template_error}")
                    return False

            self.logger.error(f"Twilio error sending WhatsApp message: {e}")
            return False

    async def send_news_digest(self, digest: str, delivery_time: str = "now") -> bool:
        """Send a formatted news digest via WhatsApp."""
        try:
            timestamp = asyncio.get_event_loop().run_in_executor(
                None, lambda: __import__('datetime').datetime.now().strftime("%I:%M %p IST")
            )

            formatted_message = f"""📰 *News Digest - {timestamp}*

{digest}

---
*Sent by AI News Agent*"""

            # Ensure message isn't too long for WhatsApp
            if len(formatted_message) > 4096:
                formatted_message = formatted_message[:4093] + "..."

            success = await self.send_message(formatted_message)

            if success:
                self.logger.info(f"News digest sent successfully at {delivery_time}")
            else:
                self.logger.error(f"Failed to send news digest at {delivery_time}")

            return success

        except Exception as e:
            self.logger.error(f"Error sending news digest", exc=e)
            return False

    async def send_error_notification(self, error_message: str) -> bool:
        """Send an error notification via WhatsApp."""
        try:
            timestamp = asyncio.get_event_loop().run_in_executor(
                None, lambda: __import__('datetime').datetime.now().strftime("%Y-%m-%d %I:%M %p IST")
            )

            error_msg = f"""⚠️ *AI News Agent Error*

*Time:* {timestamp}
*Error:* {error_message}

The news agent will continue to operate. Please check the logs for more details.

---
*Automated Error Notification*"""

            return await self.send_message(error_msg)

        except Exception as e:
            self.logger.error(f"Error sending error notification", exc=e)
            return False

    async def send_test_message(self) -> bool:
        """Send a test message to verify WhatsApp integration."""
        try:
            test_message = """✅ *AI News Agent Test*

This is a test message to verify WhatsApp integration.

If you received this message, the WhatsApp service is working correctly!

📰 Your daily news digests will appear here.

---
*Test Message*"""

            success = await self.send_message(test_message)

            if success:
                self.logger.info("Test message sent successfully")
            else:
                self.logger.error("Failed to send test message")

            return success

        except Exception as e:
            self.logger.error(f"Error sending test message", exc=e)
            return False

    async def send_delivery_confirmation(self, delivery_type: str, article_count: int) -> bool:
        """Send confirmation of successful news delivery."""
        try:
            timestamp = asyncio.get_event_loop().run_in_executor(
                None, lambda: __import__('datetime').datetime.now().strftime("%I:%M %p IST")
            )

            confirmation_msg = f"""✅ *News Delivery Confirmed*

*Delivery:* {delivery_type.title()}
*Time:* {timestamp}
*Articles:* {article_count} summarized

Your news digest has been delivered successfully!

---
*AI News Agent*"""

            return await self.send_message(confirmation_msg)

        except Exception as e:
            self.logger.error(f"Error sending delivery confirmation", exc=e)
            return False

    def validate_phone_numbers(self) -> dict:
        """Validate Twilio phone number configuration."""
        try:
            validation = {
                "twilio_number_valid": False,
                "recipient_number_valid": False,
                "errors": []
            }

            if not settings.TWILIO_PHONE_NUMBER.startswith('+'):
                validation["errors"].append("Twilio phone number must start with +")

            if not settings.WHATSAPP_RECIPIENT_NUMBER.startswith('+'):
                validation["errors"].append("Recipient phone number must start with +")

            import re
            phone_pattern = r'^\+[1-9]\d{1,14}$'

            if not re.match(phone_pattern, settings.TWILIO_PHONE_NUMBER):
                validation["errors"].append("Twilio phone number format is invalid")

            if not re.match(phone_pattern, settings.WHATSAPP_RECIPIENT_NUMBER):
                validation["errors"].append("Recipient phone number format is invalid")

            if not validation["errors"]:
                validation["twilio_number_valid"] = True
                validation["recipient_number_valid"] = True

            return validation

        except Exception as e:
            self.logger.error(f"Error validating phone numbers", exc=e)
            return {
                "twilio_number_valid": False,
                "recipient_number_valid": False,
                "errors": [str(e)]
            }
