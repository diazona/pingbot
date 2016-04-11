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

    listen_kwargs = {}

    try:
        room_id = cfg.get(u'room', u'id')
    except ConfigParser.NoOptionError:
        room_id = 'terminal'
    else:
        if room_id in ('0', 'terminal'):
            room_id = 'terminal'
    try:
        listen_kwargs['leave_room_on_close'] = cfg.getboolean(u'user', u'leave_on_close')
    except ConfigParser.NoOptionError:
        listen_kwargs['leave_room_on_close'] = True

    try:
        listen_kwargs['ping_format'] = cfg.get(u'room_{}'.format(room_id), u'ping_format')
    except ConfigParser.NoOptionError:
        pass
    try:
        listen_kwargs['superping_format'] = cfg.get(u'room_{}'.format(room_id), u'superping_format')
    except ConfigParser.NoOptionError:
        pass

    try:
        listen_kwargs['watch_tl'] = cfg.getboolean(u'room', u'watch_tl')
    except ConfigParser.NoOptionError:
        pass

    if listen_kwargs['watch_tl'] or room_id != 'terminal':
        try:
            listen_kwargs['email'] = cfg.get(u'user', u'email')
        except ConfigParser.NoOptionError:
            listen_kwargs['email'] = raw_input('Email: ')
        try:
            listen_kwargs['password'] = cfg.get(u'user', u'password')
        except ConfigParser.NoOptionError:
            import getpass
            listen_kwargs['password'] = getpass.getpass('Password: ')

    import pingbot

    try:
        pingbot.update_moderators(cfg.get(u'moderators', u'filename'))
    except ConfigParser.NoOptionError:
        pingbot.update_moderators()

    if room_id == 'terminal':
        try:
            listen_kwargs['present_user_ids'] = set(int(s.strip()) for s in cfg.get(u'room_terminal', u'present_user_ids').split(','))
        except ConfigParser.NoOptionError:
            pass
        try:
            listen_kwargs['pingable_user_ids'] = set(int(s.strip()) for s in cfg.get(u'room_terminal', u'pingable_user_ids').split(','))
        except ConfigParser.NoOptionError:
            pass
        try:
            listen_kwargs['user_id'] = cfg.getint(u'room_terminal', u'user_id')
        except ConfigParser.NoOptionError:
            pass
        pingbot.listen_to_terminal_room(**listen_kwargs)
    else:
        pingbot.listen_to_chat_room(**listen_kwargs)

if __name__ == '__main__':
    main()
