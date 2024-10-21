from dotenv import load_dotenv
from json import load, dump
from os import getenv

with open("config.json") as f:
	data: dict 	= load(f)

load_dotenv()

ADMIN_ID 	= data["adminID"]
SERVER_PORT = data["serverSetting"]["port"]
HOST_IP 	= data["serverSetting"]["host"]
URL_RULE 	= data["vkConnection"]["url_rule"]
VK_PORT 	= data["vkConnection"]["port"]
DEBUGGING	= data["debugging"]

SECRET 		= getenv("SECRET")
TOKEN 		= getenv("TOKEN")

del data

def save_parameter(parameter: str, value):
	with open("config.json") as file:
		config = load(file)
	
	keys = parameter.split('.')
	current = config
	
	for key in keys[:-1]:
		if key not in current:
			print(f"Parameter {key} does not exist in {parameter}!")
			return
		current = current[key]
	
	current[keys[-1]] = value
	
	with open("config.json", "w") as file:
		dump(config, file, indent=2)
	