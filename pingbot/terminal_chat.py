import io
import logging
import json
import random
import re
import sys
import threading
import time
import ChatExchange.chatexchange as ce

logger = logging.getLogger('pingbot.terminal_chat')

def format_message(message):
    return (u'[auto]\n{}' if u'\n' in message else u'[auto] {}').format(message)

PING_FORMAT = u'@{}'
SUPERPING_FORMAT = u'@@{}'

def code_quote(s):
    return u'`{}`'.format(s.replace(u'`', u''))

class TerminalMessage(object):
    def __init__(self, message_id, content):
        self.id = message_id
        self.content = content
        self.content_source = content

# Analogous to chatexchange.event.MessagePosted
class TerminalReadEvent(object):
    type_id = 1 # matches MessagePosted.type_id
    def __init__(self, message_id, content):
        self.content = content
        self.message = TerminalMessage(message_id, content)

class RoomProxy(object):
    '''A RoomProxy for a simple terminal-based chat room. This implements
    a basic minimum of functionality: it reads lines from stdin and interprets
    them as posted messages, and allows sending messages which will appear on
    stdout. It also includes dummy implementations of the methods that check for
    current or pingable users, but it doesn't have a concept of room membership;
    instead it acts as if nobody is ever in the chat room.'''
    def __init__(self, leave_room_on_close=True, silent=False):
        self.leave_room_on_close = leave_room_on_close
        self.silent = silent
        self.active = True
        self._callbacks = []
        logger.info(u'Joined fake terminal room')
        self.send(u'Ping bot is now active')
        self._input_thread = threading.Thread(target=self._read)
        self._input_thread.daemon = True

    def _read(self):
        for line_id, line in enumerate(iter(sys.stdin.readline, b'')):
            logger.debug(u'Read input line {}: {}'.format(line_id, line.rstrip('\n')))
            if self.active:
                self._invoke_callbacks(TerminalReadEvent(line_id, line))
            else:
                # In case room is closed from another thread
                break
        # In case we run out of input before being closed
        self.active = False

    def _invoke_callbacks(self, event):
        for c in self._callbacks:
            c(event, None)

    def watch(self, event_callback):
        if not self.active:
            return
        self._callbacks.append(event_callback)
        if not self._input_thread.is_alive():
            logger.debug(u'Starting reading thread')
            self._input_thread.start()

    def watch_polling(self, event_callback, interval):
        self.watch(event_callback)

    def send(self, message, reply_target=None):
        if self.silent:
            logger.debug(u'Not sending message due to silent mode')
            return
        message = format_message(message)
        if reply_target:
            logger.debug(u'Replying with message: {}'.format(repr(message)))
            print 'reply:', message
        else:
            logger.debug(u'Sending message: {}'.format(repr(message)))
            print message

    def close(self):
        self.active = False
        self._callbacks = []
        try:
            self.send(u'Ping bot is leaving')
        except:
            logger.exception(u'Error leaving fake terminal room')
        logger.debug(u'Closing RoomProxy')
        if self.leave_room_on_close:
            logger.info(u'Leaving fake terminal room')
        else:
            logger.info(u'Not leaving fake terminal room')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.close()

    def __iter__(self):
        if self.active:
            return iter(self._room.new_messages())

    def get_ping_string(self, user_id, quote=False):
        return self.get_ping_strings([user_id], quote)[0]

    def get_ping_strings(self, user_ids, quote=False):
        superping_format = code_quote(SUPERPING_FORMAT) if quote else SUPERPING_FORMAT
        return [superping_format.format(i) for i in user_ids]

    def get_current_user_ids(self, user_ids=None):
        return []

    def get_absent_user_ids(self, user_ids):
        return user_ids

    def get_pingable_user_ids(self, user_ids=None):
        return []
