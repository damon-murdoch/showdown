import random
import os
from .team_converter import export_factory_to_packed

FACTORY_JSON_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "factory")

def load_factory(name: str):
    if name is None:
        return 'null'

    path = os.path.join(FACTORY_JSON_DIR, "{}".format(name))
    if os.path.isdir(path):
        factory_file_names = list()
        for f in os.listdir(path):
            full_path = os.path.join(path, f)
            if os.path.isfile(full_path) and not f.startswith('.'):
                factory_file_names.append(full_path)
        file_path = random.choice(factory_file_names)

    elif os.path.isfile(path):
        file_path = path
    else:
        raise ValueError("Path must be file or dir: {}".format(name))

    with open(file_path, 'r') as f:
        factory_json = f.read()

    return export_factory_to_packed(factory_json)
