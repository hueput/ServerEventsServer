from vk_api import VkApi
from random import randint

from src.classes import Subscribers
from src.server_module import Connection
from src.configuration import SECRET, ADMIN_ID, TOKEN
import src.configuration as configuration
import src.localization as localization
import src.database as database

class VK:
	def __init__(self, subscribers: Subscribers):
		self.last_message_time = {}
		self.subscribers = subscribers
		
		self.vk_session = VkApi(token=TOKEN, api_version='5.199')
		self.vk_api = self.vk_session.get_api()
	
	def send_message(self, peer_id: int, message: str):
		if message == '':
			return

		if configuration.DEBUGGING is True:
			print(f"Message to {peer_id}: {message}")
			return

		response = 0
		try:
			response = self.vk_api.messages.send(
				peer_ids=str(peer_id),
				message=message,
				random_id=randint(1, 2 ** 31 - 1)
			)[0]
		except BaseException as e:
			print(e)

		if configuration.DELETE_MESSAGES is True and response != 0:
			try:
				message_id = response["message_id"]
				cmid = response["conversation_message_id"]
				database.save_message(peer_id, message_id, cmid, text=message)
			except BaseException as e:
				print(response)
				print(e)
	
	def send_message_to_admin(self, message: str, addr: tuple[str, tuple] = None):
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
		if data['secret'] != SECRET: return 'ok'
		if data is None or 'type' not in data: return 'ok'
		
		if data['type'] == 'message_new' and 'text' in data['object'] and 'peer_id' in data['object']:
			self._handle_new_message(data, connection)
		return 'ok'

	def _delete_messages(self, peer_id, message_ids: list):
		try:
			if peer_id >= 2000000001:
				response = self.vk_api.messages.delete(
					peer_id=peer_id,
					cmids=','.join(list(map(str, message_ids))),
					delete_for_all="1"
				)
			else:
				response = self.vk_api.messages.delete(
					peer_id=peer_id,
					message_ids=','.join(list(map(str, message_ids))),
					delete_for_all="1"
				)

			if 'error' in response:
				print('Error while deleting messages:', response['error'], sep='\n')

		except BaseException as e:
			print(e)

	def delete_old_messages(self, older_than = configuration.DELETE_MESSAGES_INTERVAL_MINUTES):
		peer_id_message_ids: dict[int: list[int]] = database.get_expired_messages(older_than)
		for peer_id, message_ids in peer_id_message_ids.items():
			self._delete_messages(peer_id, message_ids)
	
	def _handle_new_message(self, data: dict, connection: Connection):
		from_id: int = data['object']['from_id']
		peer_id: int = data['object']['peer_id']
		message_text: str = data['object']['text'].lower()
		
		reply_text = ''
		
		if from_id == ADMIN_ID or from_id == peer_id:  # Включение логирования в чате возможно только владельцем или в личном чате.
			if message_text == 'включить логирование':
				self.subscribers.add_subscriber(peer_id)
				reply_text = localization.get("logging_enabled")
			elif message_text == 'выключить логирование' and self.subscribers.is_subscriber(peer_id):
				self.subscribers.remove_subscriber(peer_id)
				reply_text = localization.get("logging_disabled")
		
		if peer_id == ADMIN_ID: # TODO: добавить в "бот" вывод local_chat_id чата и удалять с помощью "удали {local_chat_id}"
			if message_text == 'удали' and len(data["object"]["fwd_messages"])>0:
				cmids = []
				for message in data["object"]["fwd_messages"]:
					cmids.append(message["conversation_message_id"])
				self._delete_messages(2000000002, cmids)
		
		if message_text == 'кто играет':
			if connection is not None:
				connection.execute_server_command('get_players', peer_id, data)
			else:
				reply_text = localization.get("whoPlaying_no_connection")
		elif message_text == 'бот':
			"""
			[{}] Подключение ✅ / ❌  {} = local_chat_id
			Сообщения удаляются через: {} мин.  {} = delete_messages_delay
			"""
			connection_state = '✅'
			if connection.isConnected is False:
				connection_state = '❌'
			
			reply_text = localization.get("bot_state").format(connection_state=connection_state)
			if configuration.DELETE_MESSAGES is True:
				reply_text += '\n'+localization.get("delete_messages_delay").format(delete_messages_delay=configuration.DELETE_MESSAGES_INTERVAL_MINUTES)

		if reply_text != '':
			self.reply_message(peer_id=peer_id, message=reply_text, data=data)

