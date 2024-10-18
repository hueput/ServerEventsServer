import threading
import socket
import random
import vk_api

from os import getenv
from typing import Union
from dotenv import load_dotenv
from flask import Flask, request

class ConnectedClient:
	client_socket: socket.socket
	client_address: tuple
	isOpened = False

	def __init__(self, client_socket: socket.socket, client_address: tuple):
		self.client_socket = client_socket
		self.client_address = client_address
		self.isOpened = True

	def close(self):
		if self.client_socket:
			self.client_socket.close()
			self.isOpened = False

	def send(self, message: str):
		if self.client_socket and self.isOpened:
			self.client_socket.sendall( (message + "\n").encode('utf-8') )

load_dotenv()
SECRET = getenv("SECRET")
TOKEN = getenv("TOKEN")
ADMIN_ID = int(getenv("ADMIN"))
SERVERPORT = int(getenv("SERVERPORT"))

app = Flask(__name__)
vk_session = vk_api.VkApi(token=TOKEN)
vk = vk_session.get_api()

subscribers_file_path = 'listening_peers'
subscribers = []
connected_client: ConnectedClient # (addr, socket)
last_message_time = {}  # peer_id : время последнего сообщения (чтобы не отвечать на сообщения прошлого)
stop_event = threading.Event()

event_types = ('joined', 'disconnected', 'started', 'stopped')
response_types = ('players_list',)

awaiting_response = {response: [] for response in response_types} # [response] : (peer_id, data)

# Функция для рекурсивного вывода словаря
def print_nested_dict(d, indent=0):
	for key, value in d.items():
		print(' ' * indent + str(key) + ':', end=' ')
		if isinstance(value, dict):
			print()  # Переход на новую строку для вложенного словаря
			print_nested_dict(value, indent + 4)  # Увеличиваем отступ для вложенного словаря
		else:
			print(value)

def load_subscribers():
	global subscribers, subscribers_file_path
	try:
		with open(subscribers_file_path, 'r') as file:
			subscribers = [int(line.strip()) for line in file.readlines()]
		print('Подписавшиеся успешно загружены!')
	except FileNotFoundError:
		print(f"Файл {subscribers_file_path} не найден.")
	except Exception as e:
		print(f"Ошибка при загрузке подписчиков: {e}")

def add_subscriber(peer_id: int):
	global subscribers_file_path, subscribers
	if peer_id not in subscribers:
		subscribers.append(peer_id)
		try:
			with open(subscribers_file_path, 'a') as file:
				file.write(f"{peer_id}\n")
		except Exception as e:
			print(f"Ошибка при добавлении подписчика: {e}")

def remove_subscriber(peer_id:int):
	global subscribers_file_path, subscribers
	if peer_id in subscribers:
		subscribers.remove(peer_id)

	"""Удаляет идентификатор из файла, если он существует."""
	with open(subscribers_file_path, 'r') as file:
		lines = file.readlines()

	# Удаляем идентификатор, если он существует
	lines = [iden.strip() for iden in lines if iden.strip() != str(peer_id)]

	# Записываем обратно в файл
	with open(subscribers_file_path, 'w') as file:
		for iden in lines:
			file.write(f"{iden}\n")

def is_subscriber(peer_id: int):
	with open(subscribers_file_path, 'r') as file:
		lines = file.readlines()
	return peer_id in [int(line.strip()) for line in lines]



def send_message(peer_id:int, message:str):
	# print(message)
	vk.messages.send(
		peer_id=peer_id,
		message=message,
		random_id=random.randint(1, 2**31 - 1)
	)

def send_message_to_admin(message:str, addr: Union[str, tuple]=None):
	send_message(
		peer_id=ADMIN_ID,
		message=message + (f'\n{addr}' if addr else ''),
	)

def reply_message(peer_id: int, message: str, data):
	# Проверка, что ранее в этот чат не было ответа

	if peer_id not in last_message_time:
		last_message_time[peer_id] = data['object']['date']

	if last_message_time[peer_id] <= data['object']['date']:
		send_message(peer_id=peer_id, message=message)
		last_message_time[peer_id] = data['object']['date']

def send_message_to_subscribers(message: str):
	# print(subscribers)
	for peer_id in subscribers:
		send_message(peer_id, message)


@app.route('/callback', methods=['POST'])
def callback():
	data = request.json

	if data['type'] == "confirmation": return '0bb32910'
	if data['secret'] != SECRET: return 'ok'
	if data is None or 'type' not in data: return 'ok'

	# print_nested_dict(data)

	if data['type'] == 'message_new' and 'text' in data['object'] and 'peer_id' in data['object']:

		from_id: int = data['object']['from_id']
		peer_id: int = data['object']['peer_id']
		message_text: str = data['object']['text']

		if from_id == ADMIN_ID or from_id == peer_id:  # Включение логирования в чате возможно только от имени администратора или в личном чате.
			if message_text.lower() == 'включить логирование':
				if not is_subscriber(peer_id):
					add_subscriber(peer_id)
					reply_message(
						peer_id=peer_id,
						message='Логирование в данный чат включено.' + ('\n Чтобы выключить, напишите \"Выключить логирование\"'
							if peer_id == from_id else ""),
						data=data
					)
				elif is_subscriber(peer_id):
					reply_message(
						peer_id=peer_id,
						message='Логирование в данный чат уже включено.' + ('\n Чтобы выключить, напишите \"Выключить логирование\"'
							if peer_id == from_id else ""),
						data=data
					)
			elif message_text.lower() == 'выключить логирование' and is_subscriber(peer_id):
				remove_subscriber(peer_id)
				reply_message(
					peer_id=peer_id,
					message='Логирование в данный чат выключено.' + ('\n Чтобы снова включить, напишите \"Включить логирование\"'
					if peer_id == from_id else ""),
					data=data
				)

		if message_text.lower() == 'кто играет':
			server_command_execute('get_players', peer_id, data)

	return 'ok'


def start_server(host='localhost', port=12345):
	global connected_client
	# Создаем сокет
	server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	server_socket.bind((host, port))
	server_socket.listen(1)
	send_message_to_admin(f"Сервер запущен. Ожидание соединений...")

	while True:
		# Принимаем входящее соединение
		client_socket, addr = server_socket.accept()
		send_message_to_admin(f"Соединение с майнкрафт сервером было успешно установлено.", addr=addr)
		send_message_to_subscribers("Соединение с майнкрафт сервером было успешно установлено.")

		connected_client = ConnectedClient(client_socket, addr)

		server_connection_handler()

def server_connection_handler():
	global connected_client
	try:
		# Обрабатываем данные от клиента
		while True:
			data = connected_client.client_socket.recv(1024)  # Читаем данные размером до 1024 байт
			if not data:
				break  # Если данные не получены, выходим из цикла

			message = data.decode('utf-8').strip() # Декодируем полученные данные и удаляем лишнее

			message_type = message.split(' ', 1)[0]
			if message_type == 'ping':
				connected_client.send('pong')
			elif message_type in event_types:
				announce_event(message)
			elif message_type in response_types:
				process_response(message)

	except Exception as e:
		send_message_to_admin(message=f"Ошибка: {e}", addr=connected_client.client_address)
	finally:
		connected_client.close()
		send_message_to_admin(message="Соединение с сервером прервано.", addr=connected_client.client_address)
		send_message_to_subscribers(message='Соединение с майнкрафт сервером было прервано.')

def announce_event(message: str):
	def get_player_form(count):
		if 11 >= count >= 20: return 'игроков'
		elif count % 10 == 1: return 'игрок'
		elif 2 <= count % 10 <= 4: return 'игрока'
		elif 5 <= count % 10 <= 9 or count % 10 == 0: return 'игроков'

	response = {
		'joined': lambda nick, count: f'Игрок {nick} зашёл на сервер!\nТеперь на сервере {count} {get_player_form(count)}.',
		'disconnected': lambda nick, count: f'Игрок {nick} вышел с сервера.\nТеперь на сервере {count} {get_player_form(count)}.',
		'started': lambda: 'Майнкрафт сервер успешно запущен! :)',
		'stopped': lambda: 'Майнкрафт сервер выключен. =('
	}

	split_message = message.split()
	message_type = split_message[0]
	message = ''

	if message_type == 'joined' or message_type == 'disconnected': # "joined nickname 8"
		nickname = split_message[1]
		playersCount = int(split_message[2])
		message = response[message_type](nickname, playersCount)
	elif message_type == 'started':
		message = response[message_type]()
	elif message_type == 'stopped':
		message = response[message_type]()

	if message != '':
		send_message_to_subscribers(message)

def process_response(response: str):
	response_type = response.split(maxsplit=1)[0]
	# "players_list ShaniZ,Hue Die,Player1"
	content = ''
	if response_type == 'players_list' and len(response.split()) > 1:
		playerNames = response.split(maxsplit=1)[1].split(',')
		content = 'На сервере сейчас играют:\n'
		for nickname in playerNames:
			content += '- '+nickname+'\n'
		content = content[:-1] # убираем в конце '\n' (\n - это один символ.)
	else:
		content = 'Пока что на сервере никого нет.'

	for peer_id, data in awaiting_response[response_type]:
		reply_message(
			peer_id=peer_id,
			message=content,
			data=data
		)

	awaiting_response[response_type].clear()

def server_command_execute(command: str, peer_id: int, data: dict):
	global connected_client
	if command == 'get_players' and peer_id:
		if connected_client is None: return
		connected_client.send('get_players')
		awaiting_response['players_list'].append((peer_id, data))

if __name__ == "__main__":
	load_subscribers()

	# Запускаем сервер в отдельном потоке
	server_thread = threading.Thread(target=start_server, args=('localhost', SERVERPORT))
	server_thread.daemon = True
	server_thread.start()

	# Запускаем Flask приложение
	app.run(host='0.0.0.0', port=80)


