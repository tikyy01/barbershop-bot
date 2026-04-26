import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
PHONE_NUMBER = os.getenv("PHONE_NUMBER")
BARBERSHOP_NAME = os.getenv("BARBERSHOP_NAME")
