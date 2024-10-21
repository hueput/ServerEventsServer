from typing import Union
from vk_api import VkApi
from random import randint

from src.classes import Subscribers
from src.server_module import Connection
from src.configuration import SECRET, ADMIN_ID, TOKEN
import src.configuration as configuration

class VK:
	def __init__(self, subscribers: Subscribers):
		self.last_message_time = {}
		self.subscribers = subscribers
		
		self.vk_session = VkApi(token=TOKEN)
		self.vk_api = self.vk_session.get_api()
	
	def send_message(self, peer_id: int, message: str):
		if configuration.DEBUGGING is True:
			print(f"Message to {peer_id}: {message}")
			return

		self.vk_api.messages.send(
			peer_id=peer_id,
			message=message,
			random_id=randint(1, 2 ** 31 - 1)
		)
	
	def send_message_to_admin(self, message: str, addr: Union[str, tuple] = None):
		if configuration.DEBUGGING is True:
			print(f"Message to ADMIN: {message}")
			return

		self.send_message(
			peer_id=ADMIN_ID,
			message=message + (f'\n{addr}' if addr is not None else '')
		)
	
	def reply_message(self, peer_id: int, message: str, data):
		# Проверка, что ранее в этот чат не было ответа, если уже был.
		
		if peer_id not in self.last_message_time:
			self.last_message_time[peer_id] = data['object']['date']
		
		if self.last_message_time[peer_id] <= data['object']['date']:
			self.send_message(peer_id=peer_id, message=message)
			self.last_message_time[peer_id] = data['object']['date']
	
	def send_message_to_subscribers(self, message: str):
		if configuration.DEBUGGING is True:
			print(f"Message to SUBSCRIBERS: {message}")
			return

		for peer_id in self.subscribers.subscribers:
			self.send_message(peer_id, message)
	
	def handle_input(self, connection: Connection, data: dict):
		if data['type'] == "confirmation": return '0bb32910'
		if data['secret'] != SECRET: return 'ok'
		if data is None or 'type' not in data: return 'ok'
		
		if data['type'] == 'message_new' and 'text' in data['object'] and 'peer_id' in data['object']:
			self._handle_new_message(data, connection)
		
		return 'ok'
	
	def _handle_new_message(self, data: dict, connection: Connection):
		from_id: int = data['object']['from_id']
		peer_id: int = data['object']['peer_id']
		message_text: str = data['object']['text']
		
		reply_text = ''
		
		if from_id == ADMIN_ID or from_id == peer_id:  # Включение логирования в чате возможно только владельцем или в личном чате.
			if message_text.lower() == 'включить логирование':
				self.subscribers.add_subscriber(peer_id)
				reply_text = 'Логирование в данный чат включено.'
				if peer_id == from_id:
					reply_text += '\nЧтобы выключить, напишите \"Выключить логирование\"'
			elif message_text.lower() == 'выключить логирование' and self.subscribers.is_subscriber(peer_id):
				self.subscribers.remove_subscriber(peer_id)
				reply_text = 'Логирование в данный чат выключено.'
				if peer_id == from_id:
					reply_text += '\nЧтобы включить, напишите \"Включить логирование\"'
		
		if message_text.lower() == 'кто играет':
			if connection is not None:
				connection.execute_server_command('get_players', peer_id, data)
			else:
				reply_text = 'Подключения к серверу пока нет.'
		
		if reply_text != '':
			self.reply_message(peer_id=peer_id, message=reply_text, data=data)

