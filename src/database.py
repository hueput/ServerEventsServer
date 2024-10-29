import time
import sqlite3

import src.configuration as configuration


def init():
    with sqlite3.connect(configuration.DB_NAME) as connection:
        cursor = connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "sent_messages" (
                    "id"	INTEGER NOT NULL,
                    "peer_id"	INTEGER NOT NULL,
                    "message_id"	INTEGER NOT NULL,
                    "conversation_message_id"	INTEGER NOT NULL,
                    "date"	INTEGER NOT NULL,
                    "text"	TEXT NOT NULL,
                    PRIMARY KEY("id" AUTOINCREMENT),
                    UNIQUE("peer_id","message_id","conversation_message_id")
                );
        """)
        connection.commit()

def save_message(peer_id: int, message_id: int=0, conversation_message_id: int=0, date: int=None, text: str=""):
    if message_id == 0 and conversation_message_id == 0:
        return
    if date is None:
        date = int(time.time())

    with sqlite3.connect(configuration.DB_NAME) as connection:
        cursor = connection.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO sent_messages (peer_id, message_id, conversation_message_id, date, text)
            VALUES (?, ?, ?, ?, ?);
        """, (peer_id, message_id, conversation_message_id, date, text))

def get_expired_messages(after_minutes: int=configuration.DELETE_MESSAGES_INTERVAL_MINUTES) -> dict[int, list[int]]:
    # для peer_id >= 2000000001 возвращаются cmids

    with sqlite3.connect(configuration.DB_NAME) as connection:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT id, peer_id, message_id, conversation_message_id FROM sent_messages
            WHERE date < ?
        """, (int(time.time()) - after_minutes * 60,))
        answer = cursor.fetchall()

        ids = [message[0] for message in answer]
        if len(ids) > 0:
            cursor.execute(f"""
                DELETE FROM sent_messages
                WHERE id IN ({', '.join(["?"] * len(ids))})
            """, ids)

    res = dict() # {0: [0,0]}

    for _, peer_id, message_id, cmid in answer:
        if peer_id not in res:
            res[peer_id] = []

        if peer_id >= 2000000001:
            res[peer_id].append(cmid)
        else:
            res[peer_id].append(message_id)

    return res
