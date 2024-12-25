import threading
import socket
import time

from flask import Flask, request

from src.classes import Subscribers, ConnectedClient
from src.configuration import SERVER_PORT, HOST_IP, URL_RULE, VK_PORT, LANGUAGE, SECRET
from src.vk_module import VK
from src.server_module import Connection
import src.configuration as configuration
import src.localization as localization
import src.database as database

app = Flask(__name__)

subscribers: Subscribers
connection: Connection
vk: VK


@app.route(URL_RULE, methods=['POST'])
def callback():
	data = request.json
	if data is None or "type" not in data: return 'ok'
	if data['type'] == "confirmation": return '0bee3904'
	if "secret" not in data: return 'ok'
	if data['secret'] != SECRET: return 'ok'

	ret = 'ok'

	if data["type"] == "message_reply":
		database.save_message(data["object"]['peer_id'], data["object"]['id'], data["object"]['conversation_message_id'], data["object"]['date'], data["object"]["text"])
	elif data["type"] == "message_new":
		ret = vk.handle_input(connection, data)
	
	return ret


def start_connection(host: str, port: int):
	def connect(address, client: ConnectedClient = None):
		connection_socket: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		while True or time.sleep(10):
			try:
				connection_socket.connect(address)
				break
			except BaseException:
				pass

		if not client:
			client = ConnectedClient(client_socket=connection_socket, client_address=address, reconnect_func=reconnect)
		else:
			client.__init__(client_socket=connection_socket, client_address=address, reconnect_func=reconnect)

		vk.send_message_to_admin(localization.get("connection_established"))
		connection.server_connection_handler(client)

	def reconnect(address, client: ConnectedClient = None):
		print('RECONNECTING', address)
		connect(address, client=client)

	vk.send_message_to_admin(localization.get("python_server_started"))

	connect((host, port))


def command_input():
	while True:
		try:
			entered = input().lower()
		except UnicodeDecodeError:
			continue
		except KeyboardInterrupt:
			return

		if '=' in entered:
			entered = entered.split('=')
			if len(entered) != 2:
				print("You should write command as {configVariable}={value}")
				continue

			entered = list(map(str.strip, entered))
			variable = entered[0]
			value = entered[1]

			if variable == 'debugging':  # prints output into console instead of sending it to VK
				if value not in ('true', 'false'):
					print('This parameter only supports boolean values! (true or false)')
					continue

				if value == 'true':
					value = True
				else:
					value = False

				configuration.DEBUGGING = value
				configuration.save_parameter("debugging", value)
				print(f"Done and saved! debugging = {value}")
			elif variable == "delete_messages_interval_minutes":
				if not value.isdecimal():
					print("The value must be a number")
					continue

				value = int(value)
				configuration.DELETE_MESSAGES_INTERVAL_MINUTES = value
				configuration.save_parameter("delete_messages_interval_minutes", value)
				print(f"Done and saved! delete_messages_interval_minutes = {value} min.")
			else:
				print(f"You can't change this variable here. Change it in config.json. You entered: var={variable}, value={value}")
		elif entered == 'reload': # reload ru_RU
			if len(entered.split()) == 1:
				localization.load()
			else:
				localization.load(entered.split()[1])
		elif len(entered.split()) >= 2 and ' '.join(entered.split()[0:2]) == 'delete messages':
			delete_delay = 0
			if len(entered.split()) == 3:
				delete_delay = int(entered.split()[2])
			vk.delete_old_messages(delete_delay)
		else:
			print("you wrote:"+entered)


def deleting_messages():
	while True:
		if vk.vk_api is None:
			time.sleep(1)
			continue
		vk.delete_old_messages()
		time.sleep(configuration.DELETE_MESSAGES_INTERVAL_MINUTES * 60 / 10 + 1)


if __name__ == "__main__":
	localization.load(LANGUAGE)
	database.init()

	subscribers = Subscribers()
	subscribers.load_subscribers()
	vk = VK(subscribers)
	connection = Connection(vk, subscribers.subscribers)

	# Запускаем сервер в отдельном потоке
	connection_thread = threading.Thread(name="ServerThread", target=start_connection, args=(HOST_IP, SERVER_PORT))
	connection_thread.daemon = True
	connection_thread.start()
	
	# Запускаем ввод консольных команд в отдельном потоке
	input_thread = threading.Thread(name="InputThread", target=command_input)
	input_thread.daemon = True
	input_thread.start()

	# Запускаем периодическое удаление сообщений в отдельном потоке
	if configuration.DELETE_MESSAGES:
		deleting_messages_thread = threading.Thread(name="DeleteMessagesThread", target=deleting_messages)
		deleting_messages_thread.daemon = True
		deleting_messages_thread.start()

	# Запускаем Flask приложение
	app.run(host='0.0.0.0', port=VK_PORT)
