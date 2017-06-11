import io
import json
import logging

logger = logging.getLogger('pingbot.moderators')

moderators = dict()

def update(filename='moderators.json'):
    global moderators

    with io.open(filename, encoding='UTF-8') as f:
        logger.debug('Opened moderator info file {}'.format(filename))
        mod_info = json.load(f)

    logger.info('Loaded moderator info file')
    # Use a 'moderators' section so that we can combine the mod info with other
    # config information in the same file, in the future, if desired
    moderators.clear()
    moderators.update(mod_info['moderators'])
    logger.debug('Loaded mod info: {}'.format(
        ', '.join(
            '{} ({})'.format(site, len(mods)) for site, mods in moderators.items()
        )
    ))
