import os
import django
import time
from datetime import datetime
import telegram
import asyncio

# --- 1. Set up Django Environment ---
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'health_project.settings')
django.setup()
# --- End of Setup ---

# --- 2. Import your models (AFTER setup) ---
from core.models import Prescription, Patient
from django.conf import settings # Import Settings to get token

# --- 3. Bot Configuration ---
# Get the token from settings.py
BOT_TOKEN = settings.TELEGRAM_BOT_TOKEN

# --- 4. NEW ASYNC FUNCTION ---
async def send_async_message(chat_id, message):
    """Sends a message asynchronously."""
    try:
        bot = telegram.Bot(token=BOT_TOKEN)
        await bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
        print(f"Successfully sent message to {chat_id}")
    except Exception as e:
        print(f"Error sending message to {chat_id}: {e}")

# --- 5. UPDATED SYNC FUNCTION ---
def send_telegram_message(chat_id, message):
    """Sync wrapper to call the async send function."""
    try:
        asyncio.run(send_async_message(chat_id, message))
    except Exception as e:
        print(f"Error running asyncio: {e}")

def check_reminders():
    """Checks the database for reminders and sends them."""
    
    # Get the current time, but just the hour and minute
    now = datetime.now().time()
    
    print(f"[{now.strftime('%H:%M:%S')}] Checking for reminders...")

    # Find prescriptions matching the current hour and minute
    prescriptions_to_send = Prescription.objects.filter(
        reminder_time__hour=now.hour,
        reminder_time__minute=now.minute
    )

    if not prescriptions_to_send.exists():
        return

    for pres in prescriptions_to_send:
        patient = pres.patient
        
        # Check if the patient has a chat_id set
        if patient.telegram_chat_id:
            message = (
                f"🔔 **Medicine Reminder!** 🔔\n\n"
                f"Hello {patient.user.first_name},\n\n"
                f"It's time to take your medicine:\n"
                f"- **{pres.medicine_name}** ({pres.dose})"
            )
            
            send_telegram_message(patient.telegram_chat_id, message)
        else:
            print(f"Patient {patient.user.username} has a reminder but no chat_id.")

# --- 4. The Main Loop ---
if __name__ == "__main__":
    print("--- Starting Telegram Reminder Bot ---")
    print(f"Using Token: {BOT_TOKEN[:5]}... (Hidden)")
    print("This script will check for reminders every 60 seconds.")
    print("Press CTRL+C to stop.")
    
    while True:
        check_reminders()
        # Wait for 60 seconds before checking again
        time.sleep(60)