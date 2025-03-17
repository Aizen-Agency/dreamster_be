import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from app.config import Config

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.api_key = Config.SENDGRID_API_KEY
        self.sender_email = Config.SENDER_EMAIL
        self.sender_name = Config.SENDER_NAME

    def send_email(self, recipient_email, subject, body):
        """
        Send an email to a specific recipient using Twilio SendGrid
        
        Args:
            recipient_email (str): The email address of the recipient
            subject (str): The subject of the email
            body (str): The body content of the email
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Create a SendGrid message object
            message = Mail(
                from_email=(self.sender_email, self.sender_name),
                to_emails=recipient_email,
                subject=subject,
                plain_text_content=body
            )
            
            # Send the email using SendGrid API
            sg = SendGridAPIClient(self.api_key)
            response = sg.send(message)
            
            # Check if the email was sent successfully
            if 200 <= response.status_code < 300:
                logger.info(f"Email sent successfully to {recipient_email} (Status: {response.status_code})")
                return True
            else:
                logger.error(f"Failed to send email to {recipient_email}: Status code {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send email to {recipient_email}: {str(e)}")
            return False 