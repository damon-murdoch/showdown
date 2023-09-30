import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from typing import Union

from environs import Env

import constants

env = Env()
env.read_env(path="env", recurse=False)


class CustomFormatter(logging.Formatter):
    def format(self, record):
        record.module = "[{}]".format(record.module)
        record.levelname = "[{}]".format(record.levelname)
        return "{} {}".format(record.levelname.ljust(10), record.msg)


class CustomRotatingFileHandler(RotatingFileHandler):
    def __init__(self, file_name, **kwargs):
        self.base_dir = "logs"
        if not os.path.exists(self.base_dir):
            os.mkdir(self.base_dir)

        super().__init__("{}/{}".format(self.base_dir, file_name), **kwargs)

    def do_rollover(self, new_file_name):
        self.baseFilename = "{}/{}".format(self.base_dir, new_file_name)
        self.doRollover()


def init_logging(level, log_to_file):
    websockets_logger = logging.getLogger("websockets")
    websockets_logger.setLevel(logging.INFO)
    requests_logger = logging.getLogger("urllib3")
    requests_logger.setLevel(logging.INFO)

    # Gets the root logger to set handlers/formatters
    logger = logging.getLogger()
    logger.setLevel(level)
    if log_to_file:
        log_handler = CustomRotatingFileHandler("init.log")
    else:
        log_handler = logging.StreamHandler(sys.stdout)

    ShowdownConfig.log_handler = log_handler
    log_handler.setFormatter(CustomFormatter())
    logger.addHandler(log_handler)


class _ShowdownConfig:
    battle_bot_module: str
    websocket_uri: str

    room_name: str
    username: str
    password: str
    avatar: str

    post_battle_msg: str
    pre_battle_msg: str

    damage_calc_type: str
    pokemon_mode: str
    save_replay: bool
    start_timer: str

    max_z_holders: int
    max_megas: int

    species_clause: bool
    item_clause: bool

    show_win_streak: bool
    prisma_enabled: bool

    allowed_modes: list
    allow_doubles: bool
    allow_random: bool

    log_to_file: bool
    log_level: str
    log_handler: Union[CustomRotatingFileHandler, logging.StreamHandler]

    factory_enabled: bool
    team_enabled: bool

    def configure(self):
        # General Bot Settings
        self.battle_bot_module = env("BATTLE_BOT")
        self.websocket_uri = env("WEBSOCKET_URI")

        # Showdown Login Settings
        self.room_name = env("ROOM_NAME", None)
        self.username = env("PS_USERNAME")
        self.password = env("PS_PASSWORD")
        self.avatar = env("PS_AVATAR")

        # Showdown Battle Messages
        self.post_battle_msg = env.list("POST_BATTLE_MSG", ["ggwp"])
        self.pre_battle_msg = env.list("PRE_BATTLE_MSG", ["glhf"])

        # Other Showdown Settings
        self.damage_calc_type = env("DAMAGE_CALC_TYPE", "average")
        self.pokemon_mode = env("POKEMON_MODE")
        self.save_replay = env.bool("SAVE_REPLAY", False)
        self.start_timer = env.bool("START_TIMER", False)

        # Log Settings
        self.log_to_file = env.bool("LOG_TO_FILE", False)
        self.log_level = env("LOG_LEVEL", "DEBUG")

        # Team / Factory Battles Enabled
        self.team_enabled = env.bool("TEAM_ENABLED", True)
        self.factory_enabled = env.bool("FACTORY_ENABLED", True)

        # Factory Settings
        self.max_megas = env.int("MAX_MEGAS", 1)
        self.max_z_holders = env.int("MAX_Z_HOLDERS", 2)
        self.item_clause = env.bool("ITEM_CLAUSE", True)
        self.species_clause = env.bool("SPECIES_CLAUSE", True)

        # Prisma Settings
        self.show_win_streak = env.bool("SHOW_WIN_STREAK", False)

        # For use in accept_challenge mode only
        self.allowed_modes = env.list("ALLOWED_MODES", [env("POKEMON_MODE")])
        self.allow_doubles = env.bool("ALLOW_DOUBLES", False)
        self.allow_random = env.bool("ALLOW_RANDOM", False)

        # Validate Config Data
        self.validate_config()

    def validate_config(self):
        # Add singles random formats
        if self.allow_random:
            self.allowed_modes += constants.RANDOM_SINGLES_FORMATS

        # Add doubles random formats
        if self.allow_doubles:
            self.allowed_modes += constants.RANDOM_DOUBLES_FORMATS

        # Remove duplicates and sort alphabetically
        self.allowed_modes = list(set(self.allowed_modes))


ShowdownConfig = _ShowdownConfig()
