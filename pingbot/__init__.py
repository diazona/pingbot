import io
import logging
import math
import random
import re
import time

from ChatExchange.chatexchange.events import MessagePosted

from pingbot.moderators import moderators, update as update_moderators
from pingbot.sites import canonical_site_id, site_name as get_site_name

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
    NO_INFO = u'No moderator info for site {}.'

    def __init__(self, room, tl=None):
        '''Constructs a message dispatcher.

        ``room`` should be an object that can provide information about
        present and pingable user IDs as well as send messages. It should implement
        the interfaces of `pingbot.chat.RoomObserver` and
        `pingbot.chat.RoomParticipant`.

        ``tl`` should be a `RoomObserver` that can provide information about the
        Teachers' Lounge, if desired.'''
        self._room = room
        self._tl = tl

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

    def whois(self, site_id, poster_id):
        '''Gives a list of mods of the given site.'''
        try:
            site_id = canonical_site_id(site_id)
            site_name = get_site_name(site_id)
            site_mod_info = moderators[site_id]
        except KeyError:
            return self.NO_INFO.format(site_name)

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

        if self._tl:
            tl_present, tl_pingable, tl_absent = self._tl.classify_user_ids(site_mod_ids)
            recent = (pingable | tl_present | tl_pingable) - present
            others = (absent | tl_absent) - recent - present
        else:
            recent = pingable - present
            others = absent - recent - present

        if present:
            present_string = u'Currently in this room: {}.'.format(
                u', '.join(m['name'] for m in site_mod_info if m['id'] in present)
            )
        else:
            present_string = u'None are currently in this room.'

        if recent:
            recent_string = u'Recently active: {}.'.format(
                u', '.join(m['name'] for m in site_mod_info if m['id'] in recent)
            )
        else:
            recent_string = u'None are recently active.'

        absent_mod_list = u', '.join(u'{} ({})'.format(m['name'], self._room.ping_string(m['id'], quote=True)) for m in site_mod_info if m['id'] in others)

        if present or recent:
            info_string = u'I know of {} moderators on {}.'.format(count_format, site_name)
            if present and recent:
                absent_mod_leadin = u'Others:'
                return ' '.join([info_string, present_string, recent_string, absent_mod_leadin, absent_mod_list, u'.'])
            elif present:
                absent_mod_leadin = u'Not currently in this room:'
                return ' '.join([info_string, present_string, absent_mod_leadin, absent_mod_list, u'.'])
            elif recent:
                absent_mod_leadin = u'Not recently active:'
                return ' '.join([info_string, recent_string, absent_mod_leadin, absent_mod_list, u'.'])
        else:
            return u'I know of {} moderators on {}: {}. None are recently active.'.format(
                count_format,
                site_name,
                absent_mod_list
            )

    def ping_one(self, site_id, poster_id, message=None):
        '''Sends a ping to one mod from the chosen site.'''
        try:
            site_id = canonical_site_id(site_id)
            site_mod_info = moderators[site_id]
        except KeyError:
            return self.NO_INFO.format(site_name)

        site_mod_ids = set(m['id'] for m in site_mod_info if m['id'] != poster_id)

        present, pingable, absent = self._room.classify_user_ids(site_mod_ids)
        if self._tl:
            tl_present, tl_pingable, tl_absent = self._tl.classify_user_ids(site_mod_ids)
            mod_ping_set = present or tl_present or pingable or tl_pingable or absent
        else:
            mod_ping_set = present or pingable or absent

        now = time.time()

        def activity_metric(user_id):
            last_activity = self._room.user_last_activity(user_id)
            if self._tl:
                tl_last_activity = self._tl.user_last_activity(user_id)
                if tl_last_activity > last_activity:
                    last_activity = tl_last_activity
            inactive_time = (now - last_activity) / 60.
            # Optimize for users active around 5 minutes ago, using
            # (now - t) + (5 min)^2 / (now - t)
            # Use sqrt and round to avoid the effect of small differences in timing
            # a long time ago; for example, if two mods posted 5 minutes apart
            # 3 days ago, that difference shouldn't be significant.
            score = round(math.sqrt(inactive_time + 5. * 5. / inactive_time))
            # The random number here breaks ties in a way that doesn't depend on
            # any preexisting ordering of the ID list.
            shuffle_key = random.random()
            return (score, shuffle_key)

        mod_ping = self._room.ping_string(min(mod_ping_set, key=activity_metric))
        if message:
            return u'{}: {}'.format(mod_ping, message)
        else:
            return u'Pinging one moderator: {}'.format(mod_ping)

    def ping_present(self, site_id, poster_id, message=None):
        '''Sends a ping to all currently present mods from the chosen site.'''
        try:
            site_id = canonical_site_id(site_id)
            site_name = get_site_name(site_id)
            site_mod_info = moderators[site_id]
        except KeyError:
            return self.NO_INFO.format(site_name)

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
            return (u'No other' if excluding_current else u'No') + u' moderators of {} are currently in this room. Use `{} mod` to ping one.'.format(site_name, site_id)

    def ping_all(self, site_id, poster_id, message=None):
        '''Sends a ping to all mods from the chosen site.'''
        try:
            site_id = canonical_site_id(site_id)
            site_mod_info = moderators[site_id]
        except KeyError:
            return self.NO_INFO.format(site_name)

        site_mod_info.sort(key=lambda m: m['name'].lower())
        mod_pings = u' '.join(self._room.ping_strings(m['id'] for m in site_mod_info if m['id'] != poster_id))
        if message:
            return u'{}: {}'.format(mod_pings, message)
        else:
            return u'Pinging {} moderators: {}'.format(len(site_mod_info), mod_pings)

def _listen_to_room(room, tl=None):
    try:
        dp = Dispatcher(room, tl)
        room.watch(dp.on_event)
        while room.observer_active:
            # wait for an interruption
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info(u'Terminating due to KeyboardInterrupt')

from pingbot.chat import intersection

def listen_to_chat_room(email, password, room_id, watch_tl=False, host='stackexchange.com', **kwargs):
    from pingbot.chat.stackexchange import ChatExchangeSession, RoomObserver, RoomParticipant
    with ChatExchangeSession(email, password, host) as ce:
        if watch_tl:
            if host != 'stackexchange.com':
                raise ValueError('Can\'t connect to Teachers\' Lounge on host {}'.format(host))
            # Teachers' Lounge room ID is 4
            with RoomObserver(ce, 4, **kwargs) as tl:
                with RoomParticipant(ce, room_id, **kwargs) as room:
                    _listen_to_room(room, tl)
        else:
            with RoomParticipant(ce, room_id, **kwargs) as room:
                _listen_to_room(room)

def listen_to_terminal_room(watch_tl=False, **kwargs):
    from pingbot.chat.stackexchange import ChatExchangeSession, RoomObserver
    from pingbot.chat.terminal import Room as TerminalRoom
    if watch_tl:
        with ChatExchangeSession(kwargs['email'], kwargs['password'], 'stackexchange.com') as ce:
            # Teachers' Lounge room ID is 4
            se_kwargs = intersection(kwargs, ('chatexchange_session', 'room_id', 'leave_room_on_close', 'ping_format', 'superping_format'))
            term_kwargs = intersection(kwargs, ('leave_room_on_close', 'ping_format', 'superping_format', 'present_user_ids', 'pingable_user_ids'))
            with RoomObserver(ce, 4, **se_kwargs) as tl:
                with TerminalRoom(**term_kwargs) as room:
                    _listen_to_room(room, tl)
    else:
        with TerminalRoom(**kwargs) as room:
            _listen_to_room(room)
