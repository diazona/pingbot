#!/usr/bin/env python2

import ConfigParser
import io
import sys

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
    try:
        cfg_filename = sys.argv[1]
    except IndexError:
        cfg_filename = 'pingbot.cfg'

    initialize_logging(cfg_filename)

    cfg = ConfigParser.RawConfigParser()
    cfg.read(cfg_filename)

    try:
        room_id = cfg.get(u'room', u'id')
    except ConfigParser.NoOptionError:
        room_id = 'terminal'
    try:
        leave_room_on_close = cfg.getboolean(u'user', u'leave_on_close')
    except ConfigParser.NoOptionError:
        leave_room_on_close = True

    import pingbot

    try:
        pingbot.update_moderators(cfg.get(u'moderators', u'filename'))
    except ConfigParser.NoOptionError:
        pingbot.update_moderators()

    if room_id in ('0', 'terminal'):
        pingbot.listen_to_terminal_room(leave_room_on_close=leave_room_on_close)
    else:
        try:
            email = cfg.get(u'user', u'email')
        except ConfigParser.NoOptionError:
            email = raw_input('Email: ')
        try:
            password = cfg.get(u'user', u'password')
        except ConfigParser.NoOptionError:
            getpass.getpass('Password: ')

        pingbot.listen_to_chat_room(email, password, room_id, leave_room_on_close=leave_room_on_close)

if __name__ == '__main__':
    main()
