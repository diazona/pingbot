import io
import json
import logging

logger = logging.getLogger('pingbot.moderators')

class ModeratorInfo:
    def __init__(self, filename):
        self.filename = filename
        self.moderators = {}

    def update(self):
        with io.open(self.filename, encoding='UTF-8') as f:
            logger.debug('Opened moderator info file {}'.format(self.filename))
            mod_info = json.load(f)

        logger.info('Loaded moderator info file')
        # Use a 'moderators' section so that we can combine the mod info with other
        # config information in the same file, in the future, if desired
        self.moderators.clear()
        self.moderators.update(mod_info['moderators'])
        logger.debug('Loaded mod info: {}'.format(
            ', '.join(
                '{} ({})'.format(site, len(mods)) for site, mods in self.moderators.items()
            )
        ))
