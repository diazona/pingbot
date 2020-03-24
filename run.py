#!/usr/bin/env python2

import configparser
import io
import requests
import sys
import time

def parse_config_file(filename):
    with io.open(filename, encoding='UTF-8') as f:
        kv = (line.split('=', 1) for line in f if line.strip())
        cfg = dict((k.strip(), v.strip()) for k, v in kv)
    return cfg

def initialize_logging(filename=None):
    # Needs to be done before creating the logger
    import logging, logging.config

    if filename:
        try:
            logging.config.fileConfig(filename, defaults={'handler_file' : {'encoding': 'UTF-8'}})
        except:
            logging.basicConfig(level=logging.WARNING)
            logging.getLogger('pingbot').exception('Unable to open logging config file')
    else:
        logging.basicConfig(level=logging.WARNING)

def retry_on_connection_error(func, *args, **kwargs):
    '''Call func(*args, **kwargs) and retry if it raises a ConnectionError'''
    import logging
    logger = logging.getLogger('pingbot.retry')
    wait_index = 0
    while True:
        try:
            start = time.clock()
            # if it returns normally, break out of the loop
            r = func(*args, **kwargs)
        except requests.ConnectionError:
            elapsed = time.clock() - start
            logging.info('Function ran for {} seconds'.format(elapsed))
            # A very simple heuristic: if elapsed time is more than five minutes,
            # assume the previous connection was stable for at least a while
            # and reset the waiting period (before the next attempt to reconnect)
            # back to its initial value
            if elapsed > 300:
                wait_index = 0
            # Otherwise, move up to the next waiting period.
            else:
                wait_index += 1
            # Now do the waiting. This is exponential backoff: the first time
            # after a reset, it waits 15 seconds, then 30 seconds, then 60 seconds,
            # then 120 seconds, etc.
            wait_interval = 15 * (2 ** wait_index)
            logger.exception('Connection broken; reconnecting in {} seconds'.format(wait_interval))
            time.sleep(wait_interval)
        except:
            elapsed = time.clock() - start
            logging.info('Function ran for {} seconds'.format(elapsed))
            logger.exception('Error in function')
            raise
        else:
            elapsed = time.clock() - start
            logging.info('Function ran for {} seconds'.format(elapsed))
            logger.debug('Function returned normally')
            return r

def main():
    try:
        cfg_filename = sys.argv[1]
    except IndexError:
        cfg_filename = 'pingbot.cfg'

    initialize_logging(cfg_filename)

    cfg = configparser.RawConfigParser()
    cfg.read(cfg_filename)

    listen_kwargs = {}

    try:
        room_id = cfg.get('room', 'id')
    except configparser.NoOptionError:
        room_id = 'terminal'
    else:
        if room_id in ('0', 'terminal'):
            room_id = 'terminal'
    try:
        listen_kwargs['leave_room_on_close'] = cfg.getboolean('user', 'leave_on_close')
    except configparser.NoOptionError:
        listen_kwargs['leave_room_on_close'] = True

    try:
        listen_kwargs['ping_format'] = cfg.get('room_{}'.format(room_id), 'ping_format')
    except configparser.NoOptionError:
        pass
    try:
        listen_kwargs['superping_format'] = cfg.get('room_{}'.format(room_id), 'superping_format')
    except configparser.NoOptionError:
        pass

    try:
        listen_kwargs['watch_tl'] = cfg.getboolean('room', 'watch_tl')
    except configparser.NoOptionError:
        pass

    if listen_kwargs['watch_tl'] or room_id != 'terminal':
        try:
            listen_kwargs['email'] = cfg.get('user', 'email')
        except configparser.NoOptionError:
            listen_kwargs['email'] = input('Email: ')
        try:
            listen_kwargs['password'] = cfg.get('user', 'password')
        except configparser.NoOptionError:
            import getpass
            listen_kwargs['password'] = getpass.getpass('Password: ')

    import pingbot

    try:
        listen_kwargs['mod_info'] = pingbot.ModeratorInfo(cfg.get('moderators', 'filename'))
    except configparser.NoOptionError:
        listen_kwargs['mod_info'] = pingbot.ModeratorInfo('moderators.json')
    listen_kwargs['mod_info'].update()

    if room_id == 'terminal':
        try:
            listen_kwargs['present_user_ids'] = set(int(s.strip()) for s in cfg.get('room_terminal', 'present_user_ids').split(','))
        except configparser.NoOptionError:
            pass
        try:
            listen_kwargs['pingable_user_ids'] = set(int(s.strip()) for s in cfg.get('room_terminal', 'pingable_user_ids').split(','))
        except configparser.NoOptionError:
            pass
        try:
            listen_kwargs['user_id'] = cfg.getint('room_terminal', 'user_id')
        except configparser.NoOptionError:
            pass
        listen = pingbot.listen_to_terminal_room

    else:
        listen_kwargs['room_id'] = room_id
        listen = pingbot.listen_to_chat_room

    retry_on_connection_error(listen, **listen_kwargs)


if __name__ == '__main__':
    main()
