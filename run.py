#!/usr/bin/env python2

import ConfigParser
import io

def parse_config_file(filename):
    with io.open(filename, encoding='UTF-8') as f:
        kv = (line.split(u'=', 1) for line in f if line.strip())
        cfg = dict((k.strip(), v.strip()) for k, v in kv)
    return cfg

def initialize_logging(filename=None):
    # Needs to be done before creating the logger
    import logging, logging.config

    if filename:
        try:
            logging.config.fileConfig(filename)
        except:
            logging.basicConfig(level=logging.WARNING)
            logging.getLogger('pingbot').exception(u'Unable to open logging config file')
    else:
        logging.basicConfig(level=logging.WARNING)

def main():
    cfg_filename = 'pingbot.cfg'

    initialize_logging(cfg_filename)

    cfg = ConfigParser.RawConfigParser()
    cfg.read('pingbot.cfg')
    try:
        email = cfg.get(u'user', u'email')
    except ConfigParser.NoOptionError:
        email = raw_input('Email: ')
    try:
        password = cfg.get(u'user', u'password')
    except ConfigParser.NoOptionError:
        getpass.getpass('Password: ')
    try:
        room_id = cfg.get(u'room', u'id')
    except ConfigParser.NoOptionError:
        room_id = 37817
    try:
        leave_room_on_close = cfg.getboolean(u'user', u'leave_on_close')
    except ConfigParser.NoOptionError:
        leave_room_on_close = True

    import pingbot

    pingbot.update_moderators()
    pingbot.listen_to_room(email, password, room_id, leave_room_on_close=leave_room_on_close)

if __name__ == '__main__':
    main()
