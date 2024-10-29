from dotenv import load_dotenv
from os import getenv
import json

with open("config.json") as f:
	data: dict = json.load(f)

load_dotenv()

ADMIN_ID	: int	= data["admin_ID"]
SERVER_PORT	: int	= data["server_setting"]["port"]
HOST_IP		: str	= data["server_setting"]["host"]
URL_RULE	: str	= data["vk_connection"]["url_rule"]
VK_PORT		: int	= data["vk_connection"]["port"]
DEBUGGING	: bool	= data["debugging"]
LANGUAGE	: str	= data["language"]
DB_NAME		: str	= data["database_name"]

DELETE_MESSAGES: bool = data["delete_messages"]
DELETE_MESSAGES_INTERVAL_MINUTES: int = data["delete_messages_interval_minutes"]

SECRET	: str      = getenv("SECRET")
TOKEN	: str      = getenv("TOKEN")


def save_parameter(parameter: str, value):
	with open("config.json") as file:
		config = json.load(file)
	
	keys = parameter.split('.')
	current = config
	
	for key in keys[:-1]:
		if key not in current:
			print(f"Parameter {key} does not exist in {parameter}!")
			return
		current = current[key]
	
	current[keys[-1]] = value
	
	with open("config.json", "w") as file:
		json.dump(config, file, indent=2)
	