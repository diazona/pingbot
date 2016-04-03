#!/usr/bin/env python2

import logging
import re
import time
import ChatExchange.chatexchange as ce

logger = logging.getLogger('scimodsping')

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
    def listen(self, room_id):
        return RoomListener(self, room_id)

class RoomListener(object):
    def __init__(self, chatexchange_session, room_id):
        self.session = chatexchange_session
        self.room_id = room_id
        self._room = self.session.client.get_room(self.room_id)
        self._room.join()
        logger.info('Joined room {}'.format(room_id))
        self._room.send_message(format_message('Ping bot is now active'))

    def close(self):
        if self._room is None:
            return
        try:
            self._room.send_message(format_message('Ping bot is leaving'))
        except:
            pass
        try:
            self._room.leave()
        finally:
            self._room = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.close()

    def __iter__(self):
        return iter(self._room.new_messages())

    def get_current_user_ids(self):
        return self._room.get_current_user_ids()

    def get_pingable_user_ids(self):
        return self._room.get_pingable_user_ids()

HELP = '''"whois [sitename] mods" works as in TL.
"[sitename] mod" or "any [sitename] mod" pings a single mod of the site, one who is in the room if possible.
"[sitename] mods" pings all mods of the site currently in the room, or if none are present, does nothing.
"all [sitename] mods" pings all mods of the site, period.'''

WHOIS = re.compile(r'whois (\w+) mods$')
ANYPING = re.compile(r'(?:any )?(\w+) mod')
HEREPING = re.compile(r'(\w+) mods')
ALLPING = re.compile(r'all (\w+) mods')

class Dispatcher(object):
    def __init__(self, room):
        self._room = room

    def dispatch(self, message):
        logger.debug('Dispatching message: {}'.format(message))
        content = message.content.strip()
        reply = lambda m: message.reply(format_message(m))
        if content == 'help me ping':
            reply(HELP)
            return
        m = WHOIS.match(content)
        if m:
            reply(self.whois(m.group(1)))
            return
        m = ANYPING.match(content)
        if m:
            reply(self.ping_one(m.group(1)))
            return
        m = HEREPING.match(content)
        if m:
            reply(self.ping_present(m.group(1)))
            return
        m = ALLPING.match(content)
        if m:
            reply(self.ping_all(m.group(1)))
            return

    def whois(self, sitename):
        '''Gives a list of mods of the given site.'''
        return '[list of the moderators of {}.stackexchange.com]'.format(sitename)

    def ping_one(self, sitename):
        '''Sends a ping to one mod from the chosen site.'''
        return '[ping one moderator of {}.stackexchange.com]'.format(sitename)

    def ping_present(self, sitename):
        '''Sends a ping to all currently present mods from the chosen site.'''
        return '[ping all present moderators of {}.stackexchange.com]'.format(sitename)

    def ping_all(self, sitename):
        '''Sends a ping to all mods from the chosen site.'''
        return '[ping all the moderators of {}.stackexchange.com]'.format(sitename)

def listen_to_room(email, password, room_id, host='stackexchange.com'):
    try:
        with ChatExchangeSession(email, password, host) as ce:
            with RoomListener(ce, room_id) as room:
                dispatcher = Dispatcher(room)
                for message in room:
                    dispatcher.dispatch(message)
    except KeyboardInterrupt:
        log.info('Terminating due to KeyboardInterrupt')

def parse_config_file(filename):
    with open(filename) as f:
        kv = (line.split('=', 1) for line in f if line.strip())
        cfg = dict((k.strip(), v.strip()) for k, v in kv)
    return cfg

def main():
    cfg = parse_config_file('scimodsping.cfg')
    email = cfg.get('email') or raw_input("Email: ")
    password = cfg.get('password') or getpass.getpass("Password: ")
    room_id = cfg.get('room_id', 37817)

    listen_to_room(email, password, room_id)

if __name__ == '__main__':
    main()
