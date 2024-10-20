import threading
import socket

from flask import Flask, request

from src.classes import Subscribers, ConnectedClient
from src.enviroment import SERVERPORT
from src.vk_module import VK
from src.server_module import Connection


app = Flask(__name__)

Subscribers: Subscribers
connection: Connection
vk: VK

@app.route('/callback', methods=['POST'])
def callback():
	data = request.json
	return vk.handle_input(connection, data)
	
def start_server(host='localhost', port=12345):
	# Создаем сокет
	server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	server_socket.bind((host, port))
	server_socket.listen(1)
	vk.send_message_to_admin("Сервер запущен. Ожидание соединений...")
	
	while True:
		# Принимаем входящее соединение
		client_socket, addr = server_socket.accept()
		vk.send_message_to_admin(message="Соединение с майнкрафт сервером было успешно установлено.", addr=addr)
		vk.send_message_to_subscribers(message="Соединение с майнкрафт сервером было успешно установлено.")
		connection.server_connection_handler(ConnectedClient(client_socket, addr))


if __name__ == "__main__":
	subscribers = Subscribers()
	subscribers.load_subscribers()
	vk = VK(subscribers)
	connection = Connection(vk, subscribers.subscribers)

	# Запускаем сервер в отдельном потоке
	server_thread = threading.Thread(name="ServerThread", target=start_server, args=('localhost', SERVERPORT))
	server_thread.daemon = True
	server_thread.start()

	# Запускаем Flask приложение
	app.run(host='0.0.0.0', port=80)
