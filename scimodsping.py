#!/usr/bin/env python2

import io
import logging, logging.config
import json
import random
import re
import time
import ChatExchange.chatexchange as ce

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

PING_FORMAT = u'`@{}`'
SUPERPING_FORMAT = u'`@@{}`'

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

    def send(self, message):
        self._room.send_message(format_message(message))

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
                reply_msg = format_message(m)
                logger.debug(u'Replying with message: {}'.format(repr(reply_msg)))
                message.reply(reply_msg)
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
            return u'I know of {} moderators on {}.stackexchange.com. Currently in this room: {}. Not currently in this room: {} (superping with {}).'.format(
                len(site_mod_info),
                sitename,
                u', '.join(m['name'] for m in site_mod_info if m['id'] in current_site_mod_ids),
                u', '.join(m['name'] for m in site_mod_info if m['id'] not in current_site_mod_ids),
                code_quote(u' '.join(self._room.get_ping_strings([m['id'] for m in site_mod_info if m['id'] not in current_site_mod_ids])))
            )
        else:
            return u'I know of {} moderators on {}.stackexchange.com: {}. None are currently in this room. Superping with {}.'.format(
                len(site_mod_info),
                sitename,
                u', '.join(m['name'] for m in site_mod_info),
                code_quote(u' '.join(self._room.get_ping_strings(m['id'] for m in site_mod_info)))
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

moderators = dict()

def update_moderators():
    global moderators

    with io.open('moderators.json', encoding='UTF-8') as f:
        logger.debug(u'Opened moderator info file')
        mod_info = json.load(f)

    logger.info(u'Loaded moderator info file')
    # Use a 'moderators' section so that we can combine the mod info with other
    # config information in the same file, in the future, if desired
    moderators = mod_info['moderators']

def listen_to_room(email, password, room_id, host='stackexchange.com', leave_room_on_close=True):
    try:
        with ChatExchangeSession(email, password, host) as ce:
            with RoomProxy(ce, room_id, leave_room_on_close) as room:
                dispatcher = Dispatcher(room)
                for message in room:
                    dispatcher.dispatch(message)
    except KeyboardInterrupt:
        logger.info(u'Terminating due to KeyboardInterrupt')

def parse_config_file(filename):
    with io.open(filename, encoding='UTF-8') as f:
        kv = (line.split(u'=', 1) for line in f if line.strip())
        cfg = dict((k.strip(), v.strip()) for k, v in kv)
    return cfg

def initialize_logging():
    global logger

    try:
        # Needs to be done before creating the logger
        logging.config.fileConfig('scimodsping-logging.cfg')
        logger = logging.getLogger('scimodsping')
    except:
        logging.basicConfig(level=logging.WARNING)
        logger = logging.getLogger('scimodsping')
        logger.exception(u'Unable to open logging config file')

def main():
    initialize_logging()

    logger.info(u'Starting scimodsping SE chat bot')

    cfg = parse_config_file('scimodsping.cfg')
    email = cfg.get(u'email') or raw_input('Email: ')
    password = cfg.get(u'password') or getpass.getpass('Password: ')
    room_id = cfg.get(u'room_id', 37817)
    leave_room_on_close = cfg.get(u'leave_on_close', u'true') in (u'true', u'True', u'1', u'yes')

    update_moderators()

    listen_to_room(email, password, room_id, leave_room_on_close=leave_room_on_close)

if __name__ == '__main__':
    main()
