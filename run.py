#!/usr/bin/env python2

import io

def parse_config_file(filename):
    with io.open(filename, encoding='UTF-8') as f:
        kv = (line.split(u'=', 1) for line in f if line.strip())
        cfg = dict((k.strip(), v.strip()) for k, v in kv)
    return cfg

def initialize_logging():
    # Needs to be done before creating the logger
    import logging, logging.config

    try:
        logging.config.fileConfig('pingbot-logging.cfg')
        logger = logging.getLogger('pingbot')
    except:
        logging.basicConfig(level=logging.WARNING)
        logger.exception(u'Unable to open logging config file')

def main():
    initialize_logging()

    cfg = parse_config_file('pingbot.cfg')
    email = cfg.get(u'email') or raw_input('Email: ')
    password = cfg.get(u'password') or getpass.getpass('Password: ')
    room_id = cfg.get(u'room_id', 37817)
    leave_room_on_close = cfg.get(u'leave_on_close', u'true') in (u'true', u'True', u'1', u'yes')

    import pingbot

    pingbot.update_moderators()
    pingbot.listen_to_room(email, password, room_id, leave_room_on_close=leave_room_on_close)

if __name__ == '__main__':
    main()
