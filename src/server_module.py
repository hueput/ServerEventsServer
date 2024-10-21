from src.classes import ConnectedClient


event_types = ('joined', 'disconnected', 'started', 'stopped')
response_types = ('players_list',)


class Connection:
	def __init__(self, vk, subscribers: list[int]):
		self.connected_client = None
		self.isConnected = True
		self.vk = vk
		self.subscribers = subscribers
		self.awaiting_response = {response: [] for response in response_types} # [response] : (peer_id, data)
	
	def server_connection_handler(self, connected_client: ConnectedClient):
		self.connected_client = connected_client
		try:
			# Обрабатываем данные от клиента
			while True:
				data = connected_client.socket.recv(1024)  # Читаем данные размером до 1024 байт
				if not data:
					break  # Если данные не получены, выходим из цикла
				
				message = data.decode('utf-8').strip()  # Декодируем полученные данные и удаляем лишнее
				
				message_type = message.split(' ', 1)[0]
				if message_type == 'ping':
					connected_client.send('pong')
				elif message_type in event_types:
					self.announce_event(message)
				elif message_type in response_types:
					self.process_response(message)
		
		except Exception as e:
			self.vk.send_message_to_admin(message=f"Ошибка: {e}", addr=connected_client.address)
		finally:
			self.isConnected = False
			connected_client.close()
			self.vk.send_message_to_admin(message="Соединение с сервером прервано.", addr=connected_client.address)
			self.vk.send_message_to_subscribers(message='Соединение с майнкрафт сервером было прервано.')
	
	def announce_event(self, message: str):
		def get_player_form(count):
			if count % 10 == 1:
				return 'игрок'
			elif 2 <= count % 10 <= 4:
				return 'игрока'
			elif 11 >= count >= 20 or 5 <= count % 10 <= 9 or count % 10 == 0:
				return 'игроков'
		
		response = {
			'joined':		lambda nick, count: f'Игрок {nick} зашёл на сервер!\nТеперь на сервере {count} {get_player_form(count)}.',
			'disconnected':	lambda nick, count: f'Игрок {nick} вышел с сервера.\nТеперь на сервере {count} {get_player_form(count)}.',
			'started':		lambda: 'Майнкрафт сервер успешно запущен! :)',
			'stopped':		lambda: 'Майнкрафт сервер выключен. =('
		}
		
		split_message = message.split()
		message_type = split_message[0]
		message = ''
		
		if message_type == 'joined' or message_type == 'disconnected':  # паттерн: "joined nickname 8"
			nickname = split_message[1]
			playersCount = int(split_message[2])
			message = response[message_type](nickname, playersCount)
		elif message_type == 'started':
			message = response[message_type]()
		elif message_type == 'stopped':
			message = response[message_type]()
		
		if message != '':
			self.vk.send_message_to_subscribers(message=message)
	
	def process_response(self, response: str):
		response_type = response.split(maxsplit=1)[0]
		# "players_list ShaniZ,Hue Die,Player1"
		content = ''
		if response_type == 'players_list':
			if len(response.split()) > 1:
				playerNames = response.split(maxsplit=1)[1].split(',')
				content = 'На сервере сейчас играют:\n'
				for nickname in playerNames:
					content += '- ' + nickname + '\n'
				content = content[:-1]  # убираем в конце '\n' (\n - это один символ.)
			else:
				content = 'Пока что на сервере никого нет.'
		
		for peer_id, data in self.awaiting_response[response_type]:
			self.vk.reply_message(peer_id=peer_id, message=content, data=data)
		
		self.awaiting_response[response_type].clear()
	
	def execute_server_command(self, command: str, peer_id: int, data: dict):
		if command == 'get_players' and peer_id:
			if self.connected_client is None: return
			self.connected_client.send('get_players')
			self.awaiting_response['players_list'].append((peer_id, data))

