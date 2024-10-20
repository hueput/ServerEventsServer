import threading
import socket

from flask import Flask, request

from src.classes import Subscribers, ConnectedClient
from src.enviroment import SERVER_PORT, HOST_IP, URL_RULE, VK_PORT
from src.vk_module import VK
from src.server_module import Connection


app = Flask(__name__)

subscribers: Subscribers
connection: Connection
vk: VK


@app.route(URL_RULE, methods=['POST'])
def callback():
	data = request.json
	return vk.handle_input(connection, data)


def start_server(host: str, port: int):
	# Создаем сокет
	server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	try:
		server_socket.bind((host, port))
	except OSError as e:
		raise OSError(f"Error occurred while binding port {port}. The server cannot start. Change the port or close programs that use this port.\n{e}")
	
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
	server_thread = threading.Thread(name="ServerThread", target=start_server, args=(HOST_IP, SERVER_PORT))
	server_thread.daemon = True
	server_thread.start()

	# Запускаем Flask приложение
	app.run(host='0.0.0.0', port=VK_PORT)
