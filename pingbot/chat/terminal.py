import collections
import io
import logging
import json
import Queue
import random
import re
import sys
import threading
import time
import ChatExchange.chatexchange as ce

from pingbot.chat.stackexchange import format_message, code_quote
from pingbot.moderators import moderators
from . import RoomObserver as BaseRoomObserver, RoomParticipant as BaseRoomParticipant

logger = logging.getLogger('pingbot.chat.terminal')

class TerminalMessage(object):
    def __init__(self, user_id, message_id, content):
        self.id = message_id
        self.owner = DummyUser(user_id)
        self.content = content
        self.content_source = content

# Analogous to chatexchange.event.MessagePosted
class TerminalReadEvent(object):
    type_id = 1 # matches MessagePosted.type_id
    def __init__(self, user_id, message_id, content):
        self.content = content
        self.message = TerminalMessage(user_id, message_id, content)

DummyUser = collections.namedtuple('DummyUser', ['id'])

# Adapted from chatexchange.rooms.FilteredEventIterator
class TerminalEventIterable(object):
    def __init__(self, room):
        self._queue = Queue.Queue()
        room.watch(self._on_event)

    def __iter__(self):
        while True:
            yield self._queue.get()

    def _on_event(self, event, client):
        self._queue.put(event)

class Room(BaseRoomObserver, BaseRoomParticipant):
    '''A RoomObserver for a simple terminal-based chat room. This implements
    a basic minimum of functionality: it reads lines from stdin and interprets
    them as posted messages. It also includes dummy implementations of the methods
    that check for current or pingable users, but its sense of who is in the room
    and who is pingable is a static list, set on initialization.'''
    def __init__(self, leave_room_on_close=True, ping_format=u'@{}', superping_format=u'@@{}', user_id=0, present_user_ids=frozenset(), pingable_user_ids=frozenset()):
        self.leave_room_on_close = leave_room_on_close
        self.ping_format = unicode(ping_format)
        self.superping_format = unicode(superping_format)
        self.user_id = user_id
        self._present_user_ids = set(present_user_ids)
        self._pingable_user_ids = set(pingable_user_ids)
        self._callbacks = []
        self._input_thread = threading.Thread(target=self._read)
        self._input_thread.daemon = True
        self._observer_active = True
        logger.info(u'Joined fake terminal room')
        self.send(u'Ping bot is now active')

    def _read(self):
        try:
            for line_id, line in enumerate(iter(sys.stdin.readline, b'')):
                logger.debug(u'Read input line {}: {}'.format(line_id, line.rstrip('\n')))
                if self._observer_active:
                    self._invoke_callbacks(TerminalReadEvent(self.user_id, line_id, line))
                else:
                    # In case room is closed from another thread
                    break
        finally:
            # In case we run out of input before being closed
            self._observer_active = False

    def _invoke_callbacks(self, event):
        for c in self._callbacks:
            c(event, None)

    def watch(self, event_callback):
        if not self._observer_active:
            return
        self._callbacks.append(event_callback)
        if not self._input_thread.is_alive():
            logger.debug(u'Starting reading thread')
            self._input_thread.start()

    def send(self, message, reply_target=None):
        message = format_message(message)
        if reply_target:
            logger.debug(u'Replying with message: {}'.format(repr(message)))
            print 'reply:', message
        else:
            logger.debug(u'Sending message: {}'.format(repr(message)))
            print message

    def close(self):
        self._observer_active = False
        try:
            self.send(u'Ping bot is leaving')
        except:
            logger.exception(u'Error leaving fake terminal room')
        logger.debug(u'Closing RoomObserver')
        if self.leave_room_on_close:
            logger.info(u'Leaving fake terminal room')
        else:
            logger.info(u'Not leaving fake terminal room')

    def __iter__(self):
        return iter(TerminalEventIterable(self))

    def ping_string(self, user_id, quote=False):
        return self.ping_strings([user_id], quote)[0]

    def ping_strings(self, user_ids, quote=False):
        master_name_mapping = {m['id']: m['name'] for site_mods in moderators.itervalues() for m in site_mods}
        ping_format = code_quote(self.ping_format) if quote else self.ping_format
        superping_format = code_quote(self.superping_format) if quote else self.superping_format
        pingable_users = {i: master_name_mapping.get(i, u'user{}'.format(i)) for i in self.pingable_user_ids}
        return [(ping_format.format(pingable_users[i].replace(u' ', u'')) if i in pingable_users else superping_format.format(i)) for i in user_ids]

    @property
    def pingable_user_ids(self):
        return self._pingable_user_ids

    @property
    def present_user_ids(self):
        return self._present_user_ids

    @property
    def observer_active(self):
        return self._observer_active

    @property
    def participant_active(self):
        return True
