import asyncio
from prisma import Prisma
import json
import logging
import traceback
from datetime import datetime
from copy import deepcopy

import constants
from config import ShowdownConfig, init_logging

from teams import get_team
from showdown.run_battle import pokemon_battle
from showdown.websocket_client import PSWebsocketClient

from data import all_move_json
from data import pokedex
from data.mods.apply_mods import apply_mods


logger = logging.getLogger(__name__)


def check_dictionaries_are_unmodified(original_pokedex, original_move_json):
    # The bot should not modify the data dictionaries
    # This is a "just-in-case" check to make sure and will stop the bot if it mutates either of them
    if original_move_json != all_move_json:
        logger.critical("Move JSON changed!\nDumping modified version to `modified_moves.json`")
        with open("modified_moves.json", 'w') as f:
            json.dump(all_move_json, f, indent=4)
        exit(1)
    else:
        logger.debug("Move JSON unmodified!")

    if original_pokedex != pokedex:
        logger.critical(
            "Pokedex JSON changed!\nDumping modified version to `modified_pokedex.json`"
        )
        with open("modified_pokedex.json", 'w') as f:
            json.dump(pokedex, f, indent=4)
        exit(1)
    else:
        logger.debug("Pokedex JSON unmodified!")


async def showdown():

    ShowdownConfig.configure()

    init_logging(
        ShowdownConfig.log_level,
        ShowdownConfig.log_to_file
    )

    # Prisma DB Placeholder
    prisma = None

    # If prisma is enabled
    if ShowdownConfig.prisma_enabled:

        # Create the prisma client
        prisma = Prisma()

    ps_websocket_client = await PSWebsocketClient.create(
        ShowdownConfig.username,
        ShowdownConfig.password,
        ShowdownConfig.websocket_uri
    )
    await ps_websocket_client.login()

    # Custom avatar is defined
    if ShowdownConfig.avatar: 
        # Set the account avatar to the custom avatar
        await ps_websocket_client.send_message('', [f"/avatar {ShowdownConfig.avatar}"])

    battles_run = 0

    while True:
        if ShowdownConfig.log_to_file:
            ShowdownConfig.log_handler.do_rollover(datetime.now().strftime("%Y-%m-%dT%H:%M:%S.log"))
        
        # Team Data (None by default)
        team: str | None = None

        # Accept challenge mode
        if ShowdownConfig.bot_mode == constants.ACCEPT_CHALLENGE:
            await ps_websocket_client.accept_challenge(
                ShowdownConfig.allowed_modes,
                ShowdownConfig.room_name
            )

        else: # Any other mode

            # Apply mods for chosen mode
            ShowdownConfig.apply_mods()

            # Get the team to battle with
            team = get_team(ShowdownConfig.pokemon_mode)

            if ShowdownConfig.bot_mode == constants.CHALLENGE_USER:
                await ps_websocket_client.challenge_user(
                    ShowdownConfig.user_to_challenge,
                    ShowdownConfig.pokemon_mode,
                    team
                )

            elif ShowdownConfig.bot_mode == constants.SEARCH_LADDER:
                await ps_websocket_client.search_for_match(
                    ShowdownConfig.pokemon_mode, 
                    team
                )

            else:
                raise ValueError("Invalid Bot Mode: {}".format(ShowdownConfig.bot_mode))

        await pokemon_battle(ps_websocket_client, ShowdownConfig.pokemon_mode, prisma)

        # Verify dictionaries are not changed
        check_dictionaries_are_unmodified(
            ShowdownConfig.verify_pokedex, 
            ShowdownConfig.verify_all_move_json
        )

        battles_run += 1
        
        # Limited run count is not zero, and the number of battles exceeds the limit
        if ShowdownConfig.run_count and battles_run >= ShowdownConfig.run_count:
            break


if __name__ == "__main__":
    try:
        asyncio.run(showdown())
    except Exception as e:
        logger.error(traceback.format_exc())
        raise
