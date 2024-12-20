from gcsa.google_calendar import GoogleCalendar
from dotenv import load_dotenv
import os

load_dotenv()
cal = GoogleCalendar(os.getenv("EMAIL_ID", ""))

for event in cal:
    print(event)
