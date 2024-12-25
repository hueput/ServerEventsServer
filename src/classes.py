from socket import socket


class ConnectedClient:
	socket: socket
	address: tuple
	isOpened = False
	
	def __init__(self, client_socket: socket, client_address: tuple, reconnect_func=None):
		self.socket = client_socket
		self.address = client_address
		self.reconnect_func = reconnect_func
		self.isOpened = True
	
	def close(self):
		if self.socket:
			self.socket.close()
			self.isOpened = False

		if self.reconnect_func:
			self.reconnect_func(self.address, client=self)
	
	def send(self, message: str):
		if self.socket and self.isOpened:
			self.socket.sendall((message + "\n").encode('utf-8'))


class Subscribers:
	subscribers_file_path = ''
	subscribers = []
	
	def __init__(self, path: str = 'listening_peers'):
		self.subscribers_file_path = path
	
	def load_subscribers(self):
		try:
			with open(self.subscribers_file_path, 'r') as file:
				self.subscribers = [int(line.strip()) for line in file.readlines()]
			print('Подписавшиеся успешно загружены!')
		except FileNotFoundError:
			print(f"Файл {self.subscribers_file_path} не найден. Создаю новый файл.")
			with open(self.subscribers_file_path, 'w') as file:
				self.subscribers = []  # Инициализируем пустой список подписчиков
		except Exception as e:
			print(f"Ошибка при загрузке подписчиков: {e}")
	
	def add_subscriber(self, peer_id: int):
		if peer_id not in self.subscribers:
			self.subscribers.append(peer_id)
			try:
				with open(self.subscribers_file_path, 'a') as file:
					file.write(f"{peer_id}\n")
			except Exception as e:
				print(f"Ошибка при добавлении подписчика: {e}")
	
	def remove_subscriber(self, peer_id: int):
		if peer_id in self.subscribers:
			self.subscribers.remove(peer_id)
		
		"""Удаляет идентификатор из файла, если он существует."""
		with open(self.subscribers_file_path, 'r') as file:
			lines = file.readlines()
		
		# Удаляем идентификатор, если он существует
		lines = [iden.strip() for iden in lines if iden.strip() != str(peer_id)]
		
		# Записываем обратно в файл
		with open(self.subscribers_file_path, 'w') as file:
			for iden in lines:
				file.write(f"{iden}\n")
	
	def is_subscriber(self, peer_id: int):
		with open(self.subscribers_file_path, 'r') as file:
			lines = file.readlines()
		return peer_id in [int(line.strip()) for line in lines]
