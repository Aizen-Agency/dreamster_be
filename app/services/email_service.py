import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from app.config import Config

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.smtp_host = Config.SMTP_HOST
        self.smtp_port = Config.SMTP_PORT
        self.smtp_user = Config.SMTP_USER
        self.smtp_password = Config.SMTP_PASSWORD
        self.from_email = Config.SENDER_EMAIL
        self.sender_name = Config.SENDER_NAME
        self.project_name = Config.PROJECT_NAME

    def send_email(self, recipient_email, subject, html_body, plain_body=None):
        """
        Send an email to a specific recipient using SMTP
        
        Args:
            recipient_email (str): The email address of the recipient
            subject (str): The subject of the email
            html_body (str): The HTML body content of the email
            plain_body (str): The plain text body content (optional)
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Create the email message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"{self.project_name} - {subject}"
            msg['From'] = f"{self.sender_name} <{self.from_email}>"
            msg['To'] = recipient_email

            # If plain_body is not provided, create a simple version from html_body
            if plain_body is None:
                # This is a very simple conversion and might not work well for complex HTML
                plain_body = html_body.replace('<p>', '').replace('</p>', '\n\n').replace('<strong>', '').replace('</strong>', '')

            # Create HTML content with wrapper
            html_content = f"""
            <html>
                <body style="font-family: Arial, sans-serif; margin: 0; padding: 20px;">
                    <div style="max-width: 600px; margin: 0 auto; background: white; padding: 20px; border-radius: 5px;">
                        <h1 style="color: #333;">{subject}</h1>
                        <div style="color: #666;">
                            {html_body}
                        </div>
                        <hr style="margin: 20px 0;">
                        <div style="color: #999; font-size: 12px;">
                            Sent from {self.project_name}
                        </div>
                    </div>
                </body>
            </html>
            """

            # Attach plain text version first (as fallback)
            msg.attach(MIMEText(plain_body, 'plain'))
            
            # Attach HTML content
            msg.attach(MIMEText(html_content, 'html'))

            # Create SMTP connection
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
                
                logger.info(f"Email sent successfully to {recipient_email}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to send email to {recipient_email}: {str(e)}")
            return False 