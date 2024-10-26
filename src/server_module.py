from src.classes import ConnectedClient
import src.localization as localization

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
			self.vk.send_message_to_admin(message=localization.get("error")+f' {e}', addr=connected_client.address)
		finally:
			self.isConnected = False
			connected_client.close()
			# self.vk.send_message_to_admin(message="Соединение с сервером прервано.", addr=connected_client.address)
			# self.vk.send_message_to_subscribers(message='Соединение с майнкрафт сервером было прервано.')
			self.vk.send_message_to_admin(message=localization.get("minecraft_connection_lost"), addr=connected_client.address)
			self.vk.send_message_to_subscribers(message=localization.get("minecraft_connection_lost"))
	
	def announce_event(self, message: str):
		
		split_message = message.split()
		message_type = split_message[0]
		message = ''
		
		if message_type == 'joined':  # pattern: "joined nickname 8"
			nickname = split_message[1]
			players_count = int(split_message[2])
			message = (localization.get("minecraft_player_joined")
			           .format(nickname=nickname, server_players_count=players_count, server_max_players_count='20'))
		elif message_type == "disconnected":
			nickname = split_message[1]
			players_count = int(split_message[2])
			message = (localization.get("minecraft_player_disconnected")
			           .format(nickname=nickname, server_players_count=players_count, server_max_players_count='20'))
		elif message_type == 'started':
			message = localization.get("minecraft_server_started")
		elif message_type == 'stopped':
			message = localization.get("minecraft_server_stopped")
		
		if message != '':
			self.vk.send_message_to_subscribers(message=message)
	
	def process_response(self, response: str):
		response_type = response.split(maxsplit=1)[0]
		# "players_list ShaniZ,Hue Die,Player1"
		content = ''
		if response_type == 'players_list':
			if len(response.split()) > 1:
				playerNames = response.split(maxsplit=1)[1].split(',')
				content = localization.get("whoPlaying_list")+'\n'
				for nickname in playerNames:
					content += '- ' + nickname + '\n'
				content = content[:-1]  # убираем в конце '\n' (\n - это один символ.)
			else:
				content = localization.get("whoPlaying_none")
		
		for peer_id, data in self.awaiting_response[response_type]:
			self.vk.reply_message(peer_id=peer_id, message=content, data=data)
		
		self.awaiting_response[response_type].clear()
	
	def execute_server_command(self, command: str, peer_id: int, data: dict):
		if command == 'get_players' and peer_id:
			if self.connected_client is None: return
			self.connected_client.send('get_players')
			self.awaiting_response['players_list'].append((peer_id, data))

