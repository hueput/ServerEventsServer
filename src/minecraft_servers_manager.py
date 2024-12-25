import asyncio

import src.localization as localization

class MinecraftServersManager:
	def __init__(self, vk):
		self.minecraft_servers: list[tuple[MinecraftServer, str]] = []
		self.vk = vk

	def announce_event(self):
		pass

	def add_minecraft_server(self, reader, writer):
		server_name = str(len(self.minecraft_servers)+1)
		minecraft_server = MinecraftServer(server_name, reader, writer, self)
		self.minecraft_servers.append((minecraft_server, server_name))
		asyncio.run(minecraft_server.input_traffic())

	def remove_minecraft_server(self, server_name):
		pass

class MinecraftServer:
	event_types = ('joined', 'disconnected', 'started', 'stopped')
	response_types = ('players_list',)

	def __init__(self, server_name, reader, writer, manager: MinecraftServersManager):
		self.reader = reader
		self.writer = writer
		self.vk = manager.vk
		self.server_name = server_name

	async def input_traffic(self):
		try:
			# Обрабатываем данные от клиента
			while True:
				data = await self.reader.read(1024)
				if not data:
					break

				message = data.decode('utf-8').strip()  # Декодируем полученные данные и удаляем лишнее

				message_type = message.split(' ', 1)[0]
				if message_type == 'ping':
					self.writer.write(b'pong')
				elif message_type in self.event_types:
					self.announce_event(message)
				elif message_type in self.response_types:
					self.process_response(message)

		except Exception as e:
			self.vk.send_message_to_admin(message=localization.get("error") + f' {e}')
		finally:
			self.writer.close()
			await self.writer.drain()
			self.vk.send_message_to_admin(message=localization.get("minecraft_connection_lost"))
			# self.vk.send_message_to_subscribers(message=localization.get("minecraft_connection_lost"))

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
				content = localization.get("whoPlaying_list") + '\n'
				for nickname in playerNames:
					content += '- ' + nickname + '\n'
				content = content[:-1]  # убираем в конце '\n' (\n - это один символ.)
			else:
				content = localization.get("whoPlaying_none")

		for peer_id, data in self.awaiting_response[response_type]:
			self.vk.reply_message(peer_id=peer_id, message=content, data=data)

		self.awaiting_response[response_type].clear()
