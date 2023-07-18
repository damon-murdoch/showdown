import random 

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
        pkmn_dict["species"] = normalize_name(species)
        pkmn_dict["name"] = normalize_name(species)
    else:
        pkmn_dict["name"] = normalize_name(name.strip())
    if '@' in pkmn_info[0]:
        pkmn_dict["item"] = normalize_name(pkmn_info[0].split('@')[1])
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

    # List of items
    items = list()

    # List of species ids
    species = list()

    team_dict = list()

    factory_dict = get_team_dict(export_string)

    # Shuffle the sets array
    random.shuffle(factory_dict)

    # While there are less than six members of the team, 
    # AND there are items left in the factory list
    while len(team_dict) < 6 and len(factory_dict) > 0:

        print(len(team_dict), len(factory_dict))

        set = factory_dict.pop()

        # TODO: ONLY CHECK FOR FORMATS WITH SPECIES CLAUSE

        name = set["species"]

        if name == '': name = set["name"]

        if name in species:
            continue # Skip

        # TODO: ONLY CHECK FOR FORMATS WITH ITEM CLAUSE

        if set["item"] in items:
            continue # Skip

        species.append(name)
        items.append(set["item"])
        team_dict.append(set)

    # TODO: Add check here to ensure there is the minimum number of mons for the format

    return json_to_packed(team_dict)