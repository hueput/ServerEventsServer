from dotenv import load_dotenv
from json import load
from os import getenv

with open("config.json") as f:
	data: dict 	= load(f)

load_dotenv()

ADMIN_ID 	= data["adminID"]
SERVER_PORT = data["serverSetting"]["port"]
HOST_IP 	= data["serverSetting"]["host"]
URL_RULE 	= data["vkConnection"]["url_rule"]
VK_PORT 	= data["vkConnection"]["port"]

SECRET 		= getenv("SECRET")
TOKEN 		= getenv("TOKEN")

data.clear()
