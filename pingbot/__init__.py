import io
import logging
import random
import re
import time

from ChatExchange.chatexchange.events import MessagePosted

from .moderators import moderators, update as update_moderators
from .stackexchange_chat import ChatExchangeSession, RoomProxy as SERoomProxy
from .terminal_chat import RoomProxy as TerminalRoomProxy

logger = logging.getLogger('pingbot')

HELP = '''"whois [sitename] mods" works as in TL.
"[sitename] mod" or "any [sitename] mod" pings a single mod of the site, one who is in the room if possible.
"[sitename] mods" pings all mods of the site currently in the room, or if none are present, does nothing.
"all [sitename] mods" pings all mods of the site, period.
Pings can optionally be followed by a colon and a message.'''

WHOIS = re.compile(ur'whois (\w+) mods$')
ANYPING = re.compile(ur'(?:any )?(\w+) mod(?::\s*(.+))?$')
HEREPING = re.compile(ur'(\w+) mods(?::\s*(.+))?$')
ALLPING = re.compile(ur'all (\w+) mods(?::\s*(.+))?$')

class Dispatcher(object):
    NO_INFO = u'No moderator info for site {}.stackexchange.com.'

    def __init__(self, send, room_info):
        '''Constructs a message dispatcher.

        ``send`` should be a callable that takes one required argument, a string
        (`str` or `unicode`), and one optional argument, a
        `chatexchange.messages.Message` object to reply to.

        ``room_info`` should be an object that can provide information about
        present and pingable user IDs, such as a
        `pingbot.stackexchange_chat.RoomProxy` object.

        The dispatcher can be connected to a `chatexchange.rooms.Room` by
        calling e.g. `room.watch(dispatcher.on_event)`.'''
        self._send = send
        self._room = room_info

    def on_event(self, event, client):
        logger.debug(u'Received event: {}'.format(repr(event)))
        if not event.type_id == MessagePosted.type_id: # I would like to get rid of this dependence on MessagePosted
            return
        self.dispatch(event.content, event.message)

    def dispatch(self, content, message):
        logger.debug(u'Dispatching message: {}'.format(content))
        try:
            def reply(m):
                self._send(m, message)
            try:
                content = content.strip()
                if content == u'help me ping':
                    reply(HELP)
                    return
                m = WHOIS.match(content)
                if m:
                    reply(self.whois(m.group(1)))
                    return
                m = ANYPING.match(content)
                if m:
                    m = ANYPING.match(message.content_source)
                    reply(self.ping_one(m.group(1), m.group(2)))
                    return
                m = HEREPING.match(content)
                if m:
                    m = HEREPING.match(message.content_source)
                    reply(self.ping_present(m.group(1), m.group(2)))
                    return
                m = ALLPING.match(content)
                if m:
                    m = ALLPING.match(message.content_source)
                    reply(self.ping_all(m.group(1), m.group(2)))
                    return
            except:
                logger.exception(u'Error dispatching message')
                reply(u'Something went wrong, sorry!')
        except:
            logger.exception(u'Error sending reply')
            self._room.send(u'Something went _really_ wrong, sorry!')

    def whois(self, sitename):
        '''Gives a list of mods of the given site.'''
        try:
            site_mod_info = moderators[sitename]
        except KeyError:
            return self.NO_INFO.format(sitename)

        site_mod_info.sort(key=lambda m: m['name'].lower())
        current_site_mod_ids = set(m['id'] for m in site_mod_info) & set(self._room.get_current_user_ids())

        if current_site_mod_ids:
            return u'I know of {} moderators on {}.stackexchange.com. Currently in this room: {}. Not currently in this room: {} (ping with {}).'.format(
                len(site_mod_info),
                sitename,
                u', '.join(m['name'] for m in site_mod_info if m['id'] in current_site_mod_ids),
                u', '.join(m['name'] for m in site_mod_info if m['id'] not in current_site_mod_ids),
                u' '.join(self._room.get_ping_strings([m['id'] for m in site_mod_info if m['id'] not in current_site_mod_ids], quote=True))
            )
        else:
            return u'I know of {} moderators on {}.stackexchange.com: {}. None are currently in this room. Ping with {}.'.format(
                len(site_mod_info),
                sitename,
                u', '.join(m['name'] for m in site_mod_info),
                u' '.join(self._room.get_ping_strings([m['id'] for m in site_mod_info], quote=True))
            )

    def ping_one(self, sitename, message=None):
        '''Sends a ping to one mod from the chosen site.'''
        try:
            site_mod_info = moderators[sitename]
        except KeyError:
            return self.NO_INFO.format(sitename)

        site_mod_ids = set(m['id'] for m in site_mod_info)
        current_mod_ids = set(self._room.get_current_user_ids())
        current_site_mod_ids = site_mod_ids & current_mod_ids

        mod_ping = self._room.get_ping_string(random.choice(list(current_site_mod_ids or site_mod_ids)))
        if message:
            return u'{}: {}'.format(mod_ping, message)
        else:
            return u'Pinging one moderator: {}'.format(mod_ping)

    def ping_present(self, sitename, message=None):
        '''Sends a ping to all currently present mods from the chosen site.'''
        try:
            site_mod_info = moderators[sitename]
        except KeyError:
            return self.NO_INFO.format(sitename)

        site_mod_ids = set(m['id'] for m in site_mod_info)
        current_mod_ids = set(self._room.get_current_user_ids())
        current_site_mod_ids = site_mod_ids & current_mod_ids
        mod_pings = u' '.join(self._room.get_ping_strings(current_site_mod_ids))
        if message:
            return u'{}: {}'.format(mod_pings, message)
        else:
            return u'Pinging {} moderator{}: {}'.format(len(current_site_mod_ids), u's' if len(current_site_mod_ids) != 1 else u'', mod_pings)

    def ping_all(self, sitename, message=None):
        '''Sends a ping to all mods from the chosen site.'''
        try:
            site_mod_info = moderators[sitename]
        except KeyError:
            return self.NO_INFO.format(sitename)

        site_mod_info.sort(key=lambda m: m['name'])
        mod_pings = u' '.join(self._room.get_ping_strings(m['id'] for m in site_mod_info))
        if message:
            return u'{}: {}'.format(mod_pings, message)
        else:
            return u'Pinging {} moderators: {}'.format(len(site_mod_info), mod_pings)

def _listen_to_room(room):
    try:
        dp = Dispatcher(room.send, room)
        room.watch(dp.on_event)
        while room.active:
            # wait for an interruption
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info(u'Terminating due to KeyboardInterrupt')


def listen_to_chat_room(email, password, room_id, host='stackexchange.com', **kwargs):
    with ChatExchangeSession(email, password, host) as ce:
        with SERoomProxy(ce, room_id, **kwargs) as room:
            _listen_to_room(room)

def listen_to_terminal_room(**kwargs):
    with TerminalRoomProxy(**kwargs) as room:
        _listen_to_room(room)
