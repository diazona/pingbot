import io
import logging
import random
import re

from .moderators import moderators, update as update_moderators
from .stackexchange_chat import ChatExchangeSession, RoomProxy, format_message

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
        self._room = room

    def dispatch(self, message):
        logger.debug(u'Dispatching message: {}'.format(message))
        try:
            def reply(m):
                self._room.send(m, reply_target=message)
            try:
                content = message.content.strip()
                if content == u'help me ping':
                    reply(HELP)
                    return
                m = WHOIS.match(content)
                if m:
                    reply(self.whois(m.group(1)))
                    return
                m = ANYPING.match(content)
                if m:
                    reply(self.ping_one(m.group(1), m.group(2)))
                    return
                m = HEREPING.match(content)
                if m:
                    reply(self.ping_present(m.group(1), m.group(2)))
                    return
                m = ALLPING.match(content)
                if m:
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

def listen_to_room(email, password, room_id, host='stackexchange.com', leave_room_on_close=True):
    try:
        with ChatExchangeSession(email, password, host) as ce:
            with RoomProxy(ce, room_id, leave_room_on_close) as room:
                dispatcher = Dispatcher(room)
                for message in room:
                    dispatcher.dispatch(message)
    except KeyboardInterrupt:
        logger.info(u'Terminating due to KeyboardInterrupt')
