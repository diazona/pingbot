import io
import logging
import json
import random
import re
import time
import ChatExchange.chatexchange as ce

logger = logging.getLogger('pingbot.stackexchange_chat')

def format_message(message):
    return (u'[auto]\n{}' if u'\n' in message else u'[auto] {}').format(message)

class ChatExchangeSession(object):
    def __init__(self, email, password, host='stackexchange.com'):
        self.client = ce.client.Client(host, email, password)
        logger.debug(u'Logging in as {}'.format(email))
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.client.logout()
    def listen(self, room_id):
        return RoomListener(self, room_id)

PING_FORMAT = u'@{}'
SUPERPING_FORMAT = u'@@{}'

def code_quote(s):
    return u'`{}`'.format(s.replace(u'`', u''))

class RoomProxy(object):
    def __init__(self, chatexchange_session, room_id, leave_room_on_close=True):
        self.session = chatexchange_session
        self.room_id = room_id
        self.leave_room_on_close = leave_room_on_close
        self._room = self.session.client.get_room(self.room_id)
        self._room.join()
        logger.info(u'Joined room {}'.format(room_id))
        self.send(u'Ping bot is now active')

    def send(self, message, reply_target=None):
        message = format_message(message)
        if reply_target:
            logger.debug(u'Replying with message: {}'.format(repr(message)))
            reply_target.reply(message)
        else:
            logger.debug(u'Sending message: {}'.format(repr(message)))
            self._room.send_message(message)

    def close(self):
        logger.debug(u'Closing RoomProxy')
        if self._room is None:
            return
        try:
            try:
                self.send(u'Ping bot is leaving')
            except:
                logger.exception(u'Error leaving chat room')
            if self.leave_room_on_close:
                logger.info(u'Leaving chat room')
                self._room.leave()
            else:
                logger.info(u'Not leaving chat room')
                # hopefully a delay helps allow the ChatExchange client to clear
                # its queue and send the last message
                time.sleep(0.5)
        finally:
            self._room = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.close()

    def __iter__(self):
        return iter(self._room.new_messages())

    def get_ping_string(self, user_id, quote=False):
        return self.get_ping_strings([user_id], quote)[0]

    def get_ping_strings(self, user_ids, quote=False):
        ping_format = code_quote(PING_FORMAT) if quote else PING_FORMAT
        superping_format = code_quote(SUPERPING_FORMAT) if quote else SUPERPING_FORMAT
        pingable_users = dict(zip(self._room.get_pingable_user_ids(), self._room.get_pingable_user_names()))
        return [(ping_format.format(pingable_users[i].replace(u' ', u'')) if i in pingable_users else superping_format.format(i)) for i in user_ids]

    def get_current_user_ids(self, user_ids=None):
        current_user_ids = self._room.get_current_user_ids()
        if user_ids:
            current_user_ids = set(current_user_ids)
            if isinstance(user_ids, set):
                return user_ids & current_user_ids
            elif isinstance(user_ids, dict):
                return {i: user_ids[i] for i in user_ids if i in current_user_ids}
            else:
                return [i for i in user_ids if i in current_user_ids]
        else:
            return current_user_ids

    def get_absent_user_ids(self, user_ids):
        current_user_ids = self._room.get_current_user_ids()
        if user_ids:
            current_user_ids = set(current_user_ids)
            if isinstance(user_ids, set):
                return user_ids & current_user_ids
            elif isinstance(user_ids, dict):
                return {i: user_ids[i] for i in user_ids if i in current_user_ids}
            else:
                return [i for i in user_ids if i in current_user_ids]
        else:
            raise ValueError

    def get_pingable_user_ids(self, user_ids=None):
        pingable_user_ids = self._room.get_pingable_user_ids()
        if user_ids:
            pingable_user_ids = set(pingable_user_ids)
            if isinstance(user_ids, set):
                return user_ids & pingable_user_ids
            elif isinstance(user_ids, dict):
                return {i: user_ids[i] for i in user_ids if i in pingable_user_ids}
            else:
                return [i for i in user_ids if i in pingable_user_ids]
        else:
            return pingable_user_ids

