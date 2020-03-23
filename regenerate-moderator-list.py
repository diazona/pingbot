try:
    import stackexchange
except ImportError:
    print('This script requires Py-StackExchange')
    raise

import io
import json
import shutil

# An incomplete mapping of site codes that might be used for pinging to their
# corresponding domain names
SITE_CODE_MAPPINGS = {
    'so': 'stackoverflow.com',
    'su': 'superuser.com',
    'sf': 'serverfault.com',
    'askubuntu': 'askubuntu.com'
}

def site_domain_from_key(key):
    try:
        return SITE_CODE_MAPPINGS[key]
    except KeyError:
        return '{}.stackexchange.com'.format(key)

def update_moderator_list(filename):
    with io.open(filename, encoding='UTF-8') as f:
        mod_info = json.load(f)

    mod_info['moderators'] = {
        site_key: [
            {
                'name': mod.display_name,
                'id': ([i['id'] for i in site_info if i['name'] == mod.display_name] or [-1])[0]
            }
            for mod in stackexchange.Site(
                site_domain_from_key(site_key)
            ).moderators() # not moderators_elected(), because I want appointed mods too
            if not mod.is_employee and mod.id > 0 # exclude Community
        ]
        for site_key, site_info in mod_info['moderators'].items()
    }

    shutil.copy2(filename, filename + '.backup')
    with io.open(filename, mode='w', encoding='UTF-8') as f:
        json.dump(mod_info, f, indent=4, sort_keys=True)

def main():
    import sys
    try:
        filename = sys.argv[1]
    except IndexError:
        filename = 'moderators.json'
    update_moderator_list(filename)

if __name__ == '__main__':
    main()
