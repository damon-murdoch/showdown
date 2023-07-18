import random 
from data import pokemon_dex
from config import ShowdownConfig
from showdown.engine.helpers import normalize_name

def json_to_packed(json_team):
    def from_json(j):
        return "{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{},{},{},{},{},{}".format(
            j['name'],
            j.get('species', ""),
            j['item'],
            j['ability'],
            ",".join(j['moves']),
            j.get('nature', ''),
            ','.join(str(x) for x in j['evs'].values()),
            j.get('gender', ''),
            ','.join(str(x) for x in j.get('ivs', {}).values()),
            j.get('shiny', ''),
            j.get('level', ''),
            j.get('happiness', ''),
            j.get('pokeball', ''),
            j.get('hiddenpowertype', ''),
            j.get('gigantamax', ''),
            j.get('dynamaxlevel', ''),
            j.get('tera_type', ''),
        )

    packed_team_string = "]".join(
        (from_json(p) for p in json_team)
    )
    return packed_team_string


def single_pokemon_export_to_dict(pkmn_export_string):
    def get_species(s):
        if '(' in s and ')' in s:
            species = s[s.find("(")+1:s.find(")")]
            return species
        return None

    pkmn_dict = {
        "name": "",
        "species": "",
        "level": "",
        "tera_type": "",
        "gender": "",
        "item": "",
        "ability": "",
        "moves": [],
        "nature": "",
        "evs": {
            "hp": "",
            "atk": "",
            "def": "",
            "spa": "",
            "spd": "",
            "spe": "",
        },
    }
    pkmn_info = pkmn_export_string.split('\n')
    name = pkmn_info[0].split('@')[0]
    if "(M)" in name:
        pkmn_dict["gender"] = "M"
        name = name.replace('(M)', '')
    if "(F)" in name:
        pkmn_dict["gender"] = "F"
        name = name.replace('(F)', '')
    species = get_species(name)
    if species:
        name = normalize_name(species)

        pkmn_dict["species"] = name
        pkmn_dict["name"] = name
    else:
        name = normalize_name(name.strip())

        pkmn_dict["species"] = name
        pkmn_dict["name"] = name
    if '@' in pkmn_info[0]:

        # Get the item(s) from the line
        item = pkmn_info[0].split('@')[1]

        # Multiple items
        if '/' in item:
            items = item.split('/')
            item = random.choice(items)

        pkmn_dict["item"] = normalize_name(item)

    for line in map(str.strip, pkmn_info[1:]):
        if line.startswith('Ability: '):
            pkmn_dict["ability"] = normalize_name(line.split('Ability: ')[-1])
        elif line.startswith('Tera Type: '):
            pkmn_dict["tera_type"] = normalize_name(line.split('Tera Type: ')[-1])
        elif line.startswith('Level: '):
            pkmn_dict["level"] = normalize_name(line.split('Level: ')[-1])
        elif line.startswith('EVs: '):
            evs = line.split('EVs: ')[-1]
            for ev in evs.split('/'):
                ev = ev.strip()
                amount = normalize_name(ev.split(' ')[0])
                stat = normalize_name(ev.split(' ')[1])
                pkmn_dict['evs'][stat] = amount
        elif line.endswith('Nature'):
            pkmn_dict["nature"] = normalize_name(line.split('Nature')[0])
        elif line.startswith('-'):
            if '/' in line:
                moves = line[1:].split('/')
                move = random.choice(moves)
            else:
                move = line

            pkmn_dict["moves"].append(normalize_name(move))
    return pkmn_dict

def get_team_dict(export_string):
    
    team_dict = list()

    # If the file contains comments
    if '#' in export_string:

        export_array = []

        # Remove all lines starting with '#'
        for line in export_string.split('\n'): 
            if not line.startswith('#'): 
                export_array.append(line)

        export_string = "\n".join(export_array)

    team_members = export_string.split('\n\n')
    for pkmn in filter(None, team_members):
        pkmn_dict = single_pokemon_export_to_dict(pkmn)
        team_dict.append(pkmn_dict)

    return team_dict

def export_to_packed(export_string):

    team_dict = get_team_dict(export_string)

    return json_to_packed(team_dict)

def export_factory_to_packed(export_string): 

    # Number of megas
    megas = 0

    # Number of z crystal holders
    z_holders = 0

    # List of items
    items = list()
    species = list()
    team_dict = list()

    factory_dict = get_team_dict(export_string)

    # Shuffle the sets array
    random.shuffle(factory_dict)

    # While there are less than six members of the team, 
    # AND there are items left in the factory list
    while len(team_dict) < 6 and len(factory_dict) > 0:

        # TODO: Move all of this code to a worker function lol

        # Pokemon is a mega
        mega = False

        # Pokemon is a z holder
        z_holder = False

        # Pop the top set from the list
        set = factory_dict.pop()

        # Strip any formes from the name
        set_species = set["species"].split('-')[0]

        # Get the pokedex entry for the species
        dex = pokemon_dex[set_species]

        # Base species is defined
        if "baseSpecies" in dex:
            # Get the base species from the pokedex
            set_species = dex["baseSpecies"].lower()

        # Skip if species clause and species is already present
        if ShowdownConfig.species_clause and set_species in species:
            continue # Skip

        # Skip if item clause and item is already present
        if ShowdownConfig.item_clause and set["item"] in items:
            continue # Skip

        # If the pokemon is holding a mega stone
        if set["item"] != "eviolite" and set["item"].endswith("ite"):
            if megas < ShowdownConfig.max_megas: 
                mega = True # Pokemon is a mega
            else: 
                continue # Skip

        # Else if the pokemon is holding a z crystal
        elif set["item"].endswith("ium Z"):
            if z_holders < ShowdownConfig.max_z_holders:
                z_holder = True # Pokemon is a z holder
            else: 
                continue # Skip

        # If mega, increment counter
        if mega: megas += 1

        # If z holder, increment counter
        if z_holder: z_holders += 1

        species.append(set_species)
        items.append(set["item"])
        team_dict.append(set)

    # TODO: Add check here to ensure there is the minimum number of mons for the format

    return json_to_packed(team_dict)