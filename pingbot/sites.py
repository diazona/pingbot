_indexed_site_aliases = {
    "math": ['mathematics'],
    "linguistics": [],
    "cstheory": ['tcs'],
    "cogsci": [],
    "philosophy": ['phil'],
    "hsm": [],
    "chemistry": ['chem'],
    "stats": ['statistics'],
    "cs": ['computerscience', 'compsci'],
    "mathoverflow": ['mo'],
    "matheducators": ['mathed'],
    "earthscience": ['earthsci'],
    "physics": ['phys'],
    "scicomp": [],
    "astronomy": ['astro'],
    "biology": ['bio'],
    "economics": ['econ']
}

_site_aliases = {alias: id for (id, aliases) in _indexed_site_aliases.items() for alias in aliases}

def canonical_site_id(site_id):
    return _site_aliases.get(site_id, site_id)

_site_names = {
    'mathoverflow': 'mathoverflow.net'
}

def site_name(site_id):
    return _site_names.get(site_id, '{}.stackexchange.com'.format(site_id))
