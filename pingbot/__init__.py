import io
import logging
import random
import re
import time

from ChatExchange.chatexchange.events import MessagePosted

from pingbot.moderators import moderators, update as update_moderators

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

    def __init__(self, room):
        '''Constructs a message dispatcher.

        ``room_info`` should be an object that can provide information about
        present and pingable user IDs as well as send messages. It should implement
        the interfaces of `pingbot.chat.RoomObserver` and
        `pingbot.chat.RoomParticipant`.'''
        self._room = room

    def on_event(self, event, client):
        logger.debug(u'Received event: {}'.format(repr(event)))
        if not event.type_id == MessagePosted.type_id: # I would like to get rid of this dependence on MessagePosted
            return
        self.dispatch(event.content, event.message)

    def dispatch(self, content, message):
        logger.debug(u'Dispatching message: {}'.format(content))
        try:
            def reply(m):
                self._room.send(m, message)
            poster_id = message.owner.id
            try:
                content = content.strip()
                if content == u'help me ping':
                    reply(HELP)
                    return
                m = WHOIS.match(content)
                if m:
                    reply(self.whois(m.group(1), poster_id))
                    return
                m = ANYPING.match(content)
                if m:
                    m = ANYPING.match(message.content_source)
                    reply(self.ping_one(m.group(1), poster_id, m.group(2)))
                    return
                m = HEREPING.match(content)
                if m:
                    m = HEREPING.match(message.content_source)
                    reply(self.ping_present(m.group(1), poster_id, m.group(2)))
                    return
                m = ALLPING.match(content)
                if m:
                    m = ALLPING.match(message.content_source)
                    reply(self.ping_all(m.group(1), poster_id, m.group(2)))
                    return
            except:
                logger.exception(u'Error dispatching message')
                reply(u'Something went wrong, sorry!')
        except:
            logger.exception(u'Error sending reply')
            self._room.send(u'Something went _really_ wrong, sorry!')

    def whois(self, sitename, poster_id):
        '''Gives a list of mods of the given site.'''
        try:
            site_mod_info = moderators[sitename]
        except KeyError:
            return self.NO_INFO.format(sitename)

        site_mod_info.sort(key=lambda m: m['name'].lower())
        site_mod_ids = set(m['id'] for m in site_mod_info)
        if poster_id in site_mod_ids:
            # don't remove from the original list in the moderators dict
            site_mod_info = [m for m in site_mod_info if m['id'] != poster_id]
            site_mod_ids.remove(poster_id)
            count_format = '{} other'.format(len(site_mod_info))
        else:
            count_format = '{}'.format(len(site_mod_info))

        present, pingable, absent = self._room.classify_user_ids(site_mod_ids)
        if present:
            return u'I know of {} moderators on {}.stackexchange.com. Currently in this room: {}. Not currently in this room: {} (ping with {}).'.format(
                count_format,
                sitename,
                u', '.join(m['name'] for m in site_mod_info if m['id'] in present),
                u', '.join(m['name'] for m in site_mod_info if m['id'] not in present),
                u' '.join(self._room.ping_strings([m['id'] for m in site_mod_info if m['id'] not in present], quote=True))
            )
        else:
            return u'I know of {} moderators on {}.stackexchange.com: {}. None are currently in this room. Ping with {}.'.format(
                count_format,
                sitename,
                u', '.join(m['name'] for m in site_mod_info),
                u' '.join(self._room.ping_strings([m['id'] for m in site_mod_info], quote=True))
            )

    def ping_one(self, sitename, poster_id, message=None):
        '''Sends a ping to one mod from the chosen site.'''
        try:
            site_mod_info = moderators[sitename]
        except KeyError:
            return self.NO_INFO.format(sitename)

        site_mod_ids = set(m['id'] for m in site_mod_info if m['id'] != poster_id)

        present, pingable, absent = self._room.classify_user_ids(site_mod_ids)

        mod_ping = self._room.ping_string(random.choice(list(present or pingable or absent)))
        if message:
            return u'{}: {}'.format(mod_ping, message)
        else:
            return u'Pinging one moderator: {}'.format(mod_ping)

    def ping_present(self, sitename, poster_id, message=None):
        '''Sends a ping to all currently present mods from the chosen site.'''
        try:
            site_mod_info = moderators[sitename]
        except KeyError:
            return self.NO_INFO.format(sitename)

        site_mod_ids = set(m['id'] for m in site_mod_info)
        excluding_current = poster_id in site_mod_ids
        if excluding_current:
            site_mod_ids.remove(poster_id)

        present, pingable, absent = self._room.classify_user_ids(site_mod_ids)

        if present:
            mod_pings = u' '.join(self._room.ping_strings(present))
            if message:
                return u'{}: {}'.format(mod_pings, message)
            else:
                return u'Pinging {} moderator{}: {}'.format(len(present), u's' if len(present) != 1 else u'', mod_pings)
        else:
            return (u'No other' if excluding_current else u'No') + u' moderators of {0}.stackexchange.com are currently in this room. Use `{0} mod` to ping one.'.format(sitename)

    def ping_all(self, sitename, poster_id, message=None):
        '''Sends a ping to all mods from the chosen site.'''
        try:
            site_mod_info = moderators[sitename]
        except KeyError:
            return self.NO_INFO.format(sitename)

        site_mod_info.sort(key=lambda m: m['name'].lower())
        mod_pings = u' '.join(self._room.ping_strings(m['id'] for m in site_mod_info if m['id'] != poster_id))
        if message:
            return u'{}: {}'.format(mod_pings, message)
        else:
            return u'Pinging {} moderators: {}'.format(len(site_mod_info), mod_pings)

def _listen_to_room(room):
    try:
        dp = Dispatcher(room)
        room.watch(dp.on_event)
        while room.observer_active:
            # wait for an interruption
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info(u'Terminating due to KeyboardInterrupt')


def listen_to_chat_room(email, password, room_id, host='stackexchange.com', **kwargs):
    from pingbot.chat.stackexchange import ChatExchangeSession, Room as SERoom
    with ChatExchangeSession(email, password, host) as ce:
        with SERoom(ce, room_id, **kwargs) as room:
            _listen_to_room(room)

def listen_to_terminal_room(**kwargs):
    from pingbot.chat.terminal import Room as TerminalRoom
    with TerminalRoom(**kwargs) as room:
        _listen_to_room(room)
