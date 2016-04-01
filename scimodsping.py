#!/usr/bin/env python2

import logging
import re
import time
import ChatExchange.chatexchange as ce

logger = logging.getLogger('scimodsping')

def listen_to_room(email, password, room_id, host='stackexchange.com'):
    client = ce.client.Client(host, email, password)
    logger.debug('Logging in as {}'.format(email))

    room = client.get_room(room_id)
    room.join()
    logger.info('Joined room {}'.format(room_id))
    room.send_message('Ping bot is now active')

    room.watch(on_message)

    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass

    room.send_message('Ping bot is leaving')
    client.logout()

HELP = '''"whois [sitename] mods" works as in TL.
"[sitename] mod" or "any [sitename] mod" pings a single mod of the site, one who is in the room if possible.
"[sitename] mods" pings all mods of the site currently in the room, or if none are present, does nothing.
"all [sitename] mods" pings all mods of the site, period.'''

WHOIS = re.compile(r'whois (\w+) mods$')
ANYPING = re.compile(r'(?:any )?(\w+) mod')
HEREPING = re.compile(r'(\w+) mods')
ALLPING = re.compile(r'all (\w+) mods')

def on_message(message, client):
    if not isinstance(message, ce.events.MessagePosted):
        # Ignore non-message_posted events.
        logger.info('Ignoring event: {}'.format(repr(message)))
        return

    poster = message.user
    content = message.content.strip()
    reply = message.message.reply
    m = WHOIS.match(content)
    if m:
        reply(whois(m.group(1)))
        return
    m = ANYPING.match(content)
    if m:
        reply(ping_one(m.group(1)))
        return
    m = HEREPING.match(content)
    if m:
        reply(ping_present(m.group(1)))
        return
    m = ALLPING.match(content)
    if m:
        reply(ping_all(m.group(1)))
        return
    if content == 'help me ping':
        reply(HELP)
        return

def whois(sitename):
    '''Gives a list of mods of the given site.'''
    return '[list of the moderators of {}.stackexchange.com]'.format(sitename)

def ping_one(sitename):
    '''Sends a ping to one mod from the chosen site.'''
    return '[ping one moderator of {}.stackexchange.com]'.format(sitename)

def ping_present(sitename):
    '''Sends a ping to all currently present mods from the chosen site.'''
    return '[ping all present moderators of {}.stackexchange.com]'.format(sitename)

def ping_all(sitename):
    '''Sends a ping to all mods from the chosen site.'''
    return '[ping all the moderators of {}.stackexchange.com]'.format(sitename)

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
