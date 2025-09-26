# avosoft_engine/utils/email_notifier.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()

def send_gmail_alert(subject, body, to_email=None):
    """
    Send email notification using Gmail SMTP
    """
    # Configuration - SET THESE VALUES!
    GMAIL_USER = os.getenv("GMAIL_USER") # Your Gmail address
    GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")  # Gmail app password
    DEFAULT_TO = os.getenv("DEFAULT_TO")  # Where to send alerts

    to_email = to_email or DEFAULT_TO
    
    try:
        # Create message
        msg = MIMEMultipart()
        msg['Subject'] = f"[Avosoft] {subject}"
        msg['From'] = GMAIL_USER
        msg['To'] = to_email
        
        # Add body
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, to_email, msg.as_string())
        
        print(f"Email alert sent: {subject}")
        return True
        
    except Exception as e:
        print(f"Failed to send email alert: {e}")
        return False

# Test function
def test_email():
    """Test the email functionality"""
    success = send_gmail_alert(
        "Test Email", 
        "This is a test email from Avosoft data generator."
    )
    if success:
        print("✅ Email test successful!")
    else:
        print("❌ Email test failed!")
