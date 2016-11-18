import io
import logging
import json
import random
import re
import time
import ChatExchange.chatexchange as ce

from . import RoomObserver as BaseRoomObserver, RoomParticipant as BaseRoomParticipant

logger = logging.getLogger('pingbot.chat.stackexchange')

def format_message(message):
    return ('[auto]\n{}' if '\n' in message else '[auto] {}').format(message)

class ChatExchangeSession(object):
    def __init__(self, email, password, host='stackexchange.com'):
        self.client = ce.client.Client(host, email, password)
        logger.debug('Logging in as {}'.format(email))
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.client.logout()

def code_quote(s):
    return '`{}`'.format(s.replace('`', ''))

ignored_messages = set()

class RoomObserver(BaseRoomObserver):
    def __init__(self, chatexchange_session, room_id, leave_room_on_close=True, ping_format='@{}', superping_format='@@{}'):
        self._observer_active = False
        self._user_last_activity = {}
        self._room = None
        self.session = chatexchange_session
        self.room_id = room_id
        self.leave_room_on_close = leave_room_on_close
        self.ping_format = str(ping_format)
        self.superping_format = str(superping_format)
        self._room = self.session.client.get_room(self.room_id)
        self._room.join()
        self.watch(self._user_status_callback)
        self._observer_active = True
        logger.info('Joined room {}'.format(room_id))

    def _user_status_callback(self, event, client):
        if event.type_id in (ce.events.UserEntered.type_id, ce.events.UserLeft.type_id):
            self._user_last_activity[event.user.id] = event.time_stamp
        elif event.type_id == ce.events.MessagePosted.type_id:
            src = event.message.content_source
            try:
                ignored_messages.remove(src)
            except KeyError:
                pass
            else:
                self._user_last_activity[event.user.id] = event.time_stamp

    def user_last_activity(self, user_id):
        return self._user_last_activity.get(user_id, 0)

    def watch(self, event_callback):
        if self._observer_active:
            self._room.watch(event_callback)

    def watch_polling(self, event_callback, interval):
        if self._observer_active:
            self._room.watch_polling(event_callback, interval)

    def watch_socket(self, event_callback):
        if self._observer_active:
            self._room.watch_socket(event_callback)

    def close(self):
        # If multiple threads try to leave the same room, this guard makes it
        # unlikely that more than one of them will actually run close(). If the
        # timing works out so that does happen, it's not really a problem; the
        # SE system should just ignore the duplicate leave request.
        if not self._observer_active:
            return
        self._observer_active = False
        logger.debug('Closing RoomObserver')
        try:
            if self.leave_room_on_close:
                logger.info('Leaving room {}'.format(self.room_id))
                self._room.leave()
            else:
                logger.info('Not leaving room {}'.format(self.room_id))
        finally:
            self._room = None

    def __iter__(self):
        # Note that multiple independent iterators will each see a copy of each
        # of the room's events.
        return iter(self._room.new_events())

    def ping_string(self, user_id, quote=False):
        return self.ping_strings([user_id], quote)[0]

    def ping_strings(self, user_ids, quote=False):
        ping_format = code_quote(self.ping_format) if quote else self.ping_format
        superping_format = code_quote(self.superping_format) if quote else self.superping_format
        pingable_users = dict(list(zip(self._room.get_pingable_user_ids(), self._room.get_pingable_user_names())))
        return [(ping_format.format(pingable_users[i].replace(' ', '')) if i in pingable_users else superping_format.format(i)) for i in user_ids]

    @property
    def present_user_ids(self):
        return set(self._room.get_current_user_ids())

    @property
    def pingable_user_ids(self):
        return set(self._room.get_pingable_user_ids())

    @property
    def observer_active(self):
        return self._observer_active

class RoomParticipant(RoomObserver, BaseRoomParticipant):
    def __init__(self, chatexchange_session, room_id, leave_room_on_close=True, announce=True, ping_format='@{}', superping_format='@@{}'):
        RoomObserver.__init__(self, chatexchange_session, room_id, leave_room_on_close, ping_format, superping_format)
        self.announce = announce
        self._participant_active = True
        if self.announce:
            self._send('Ping bot is now active')

    def send(self, message, reply_target=None):
        if not self._participant_active:
            logger.info('Dropping message due to inactive status: {}'.format(repr(message)))
            return
        self._send(message, reply_target)

    def _send(self, message, reply_target=None):
        message = format_message(message)
        rmessage = repr(message)
        ignored_messages.add(rmessage)
        if reply_target:
            logger.debug('Replying with message: {}'.format(rmessage))
            reply_target.reply(message)
        else:
            logger.debug('Sending message: {}'.format(rmessage))
            self._room.send_message(message)

    def close(self):
        logger.debug('Closing RoomParticipant')
        self._participant_active = False
        if self.announce:
            try:
                self._send('Ping bot is leaving')
                # hopefully a delay helps allow the ChatExchange client to clear
                # its queue and send the last message
                time.sleep(0.5)
            except:
                logger.exception('Error sending goodbye message')
        super(RoomParticipant, self).close()

    @property
    def participant_active(self):
        return self._participant_active
