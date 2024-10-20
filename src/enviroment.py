from dotenv import load_dotenv
from os import getenv

load_dotenv()
SECRET = getenv("SECRET")
TOKEN = getenv("TOKEN")
ADMIN_ID = int(getenv("ADMIN"))
SERVERPORT = int(getenv("SERVERPORT"))