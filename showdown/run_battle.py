import importlib
import json
import asyncio
import concurrent.futures
from copy import deepcopy
import logging

import database

import data
from data.helpers import get_standard_battle_sets
import constants
from config import ShowdownConfig
from showdown.engine.evaluate import Scoring
from showdown.battle import Pokemon
from showdown.battle import LastUsedMove
from showdown.battle_modifier import async_update_battle

from showdown.websocket_client import PSWebsocketClient

logger = logging.getLogger(__name__)


def battle_is_finished(battle_tag, msg):
    return (
        msg.startswith(">{}".format(battle_tag))
        and (constants.WIN_STRING in msg or constants.TIE_STRING in msg)
        and constants.CHAT_STRING not in msg
    )


async def async_pick_move(battle):
    battle_copy = deepcopy(battle)
    if battle_copy.request_json:
        battle_copy.user.from_json(battle_copy.request_json)

    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        best_move = await loop.run_in_executor(pool, battle_copy.find_best_move)
    choice = best_move[0]
    if constants.SWITCH_STRING in choice:
        battle.user.last_used_move = LastUsedMove(
            battle.user.active.name, "switch {}".format(choice.split()[-1]), battle.turn
        )
    else:
        battle.user.last_used_move = LastUsedMove(
            battle.user.active.name, choice.split()[2], battle.turn
        )
    return best_move


async def handle_team_preview(battle, ps_websocket_client):
    battle_copy = deepcopy(battle)
    battle_copy.user.active = Pokemon.get_dummy()
    battle_copy.opponent.active = Pokemon.get_dummy()

    best_move = await async_pick_move(battle_copy)
    size_of_team = len(battle.user.reserve) + 1
    team_list_indexes = list(range(1, size_of_team))
    choice_digit = int(best_move[0].split()[-1])

    team_list_indexes.remove(choice_digit)
    message = [
        "/team {}{}|{}".format(
            choice_digit, "".join(str(x) for x in team_list_indexes), battle.rqid
        )
    ]

    await ps_websocket_client.send_message(battle.battle_tag, message)


async def get_battle_tag_and_opponent(ps_websocket_client: PSWebsocketClient):
    while True:
        msg = await ps_websocket_client.receive_message()
        split_msg = msg.split("|")
        first_msg = split_msg[0]
        if "battle" in first_msg:
            battle_tag = first_msg.replace(">", "").strip()
            user_name = split_msg[-1].replace("☆", "").strip()
            opponent_name = (
                split_msg[4].replace(user_name, "").replace("vs.", "").strip()
            )
            return battle_tag, opponent_name


async def initialize_battle_with_tag(
    ps_websocket_client: PSWebsocketClient, set_request_json=True
):
    battle_module = importlib.import_module(
        "showdown.battle_bots.{}.main".format(ShowdownConfig.battle_bot_module)
    )

    battle_tag, opponent_name = await get_battle_tag_and_opponent(ps_websocket_client)
    while True:
        msg = await ps_websocket_client.receive_message()
        split_msg = msg.split("|")
        if split_msg[1].strip() == "request" and split_msg[2].strip():
            user_json = json.loads(split_msg[2].strip("'"))
            user_id = user_json[constants.SIDE][constants.ID]
            opponent_id = constants.ID_LOOKUP[user_id]
            battle = battle_module.BattleBot(battle_tag)
            battle.opponent.name = opponent_id
            battle.opponent.account_name = opponent_name

            if set_request_json:
                battle.request_json = user_json

            return battle, opponent_id, user_json


async def read_messages_until_first_pokemon_is_seen(
    ps_websocket_client, battle, opponent_id, user_json
):
    # keep reading messages until the opponent's first pokemon is seen
    # this is run when starting non team-preview battles
    while True:
        msg = await ps_websocket_client.receive_message()
        if constants.START_STRING in msg:
            split_msg = msg.split(constants.START_STRING)[-1].split("\n")
            for line in split_msg:
                if opponent_id in line and constants.SWITCH_STRING in line:
                    battle.start_non_team_preview_battle(user_json, line)

                elif battle.started:
                    await async_update_battle(battle, line)

            # first move needs to be picked here
            best_move = await async_pick_move(battle)
            await ps_websocket_client.send_message(battle.battle_tag, best_move)

            return


async def start_random_battle(
    ps_websocket_client: PSWebsocketClient, pokemon_battle_type
):
    battle, opponent_id, user_json = await initialize_battle_with_tag(
        ps_websocket_client
    )
    battle.battle_type = constants.RANDOM_BATTLE
    battle.generation = pokemon_battle_type[:4]

    await read_messages_until_first_pokemon_is_seen(
        ps_websocket_client, battle, opponent_id, user_json
    )

    return battle


async def start_standard_battle(
    ps_websocket_client: PSWebsocketClient, pokemon_battle_type
):
    battle, opponent_id, user_json = await initialize_battle_with_tag(
        ps_websocket_client, set_request_json=False
    )
    battle.battle_type = constants.STANDARD_BATTLE
    battle.generation = pokemon_battle_type[:4]

    if battle.generation in constants.NO_TEAM_PREVIEW_GENS:
        await read_messages_until_first_pokemon_is_seen(
            ps_websocket_client, battle, opponent_id, user_json
        )
    else:
        msg = ""
        while constants.START_TEAM_PREVIEW not in msg:
            msg = await ps_websocket_client.receive_message()

        preview_string_lines = msg.split(constants.START_TEAM_PREVIEW)[-1].split("\n")

        opponent_pokemon = []
        for line in preview_string_lines:
            if not line:
                continue

            split_line = line.split("|")
            if (
                split_line[1] == constants.TEAM_PREVIEW_POKE
                and split_line[2].strip() == opponent_id
            ):
                opponent_pokemon.append(split_line[3])

        battle.initialize_team_preview(user_json, opponent_pokemon, pokemon_battle_type)
        battle.during_team_preview()

        smogon_usage_data = get_standard_battle_sets(
            pokemon_battle_type,
            pokemon_names=set(
                p.name for p in battle.opponent.reserve + battle.user.reserve
            ),
        )
        data.pokemon_sets = smogon_usage_data
        for pkmn, values in smogon_usage_data.items():
            data.effectiveness[pkmn] = values["effectiveness"]

        await handle_team_preview(battle, ps_websocket_client)

    return battle


async def start_battle(ps_websocket_client, battle_format, prisma):
    # Only random battles - CC1v1 / Battle Factory has team preview
    if "random" in battle_format:
        Scoring.POKEMON_ALIVE_STATIC = (
            30  # random battle benefits from a lower static score for an alive pkmn
        )
        battle = await start_random_battle(ps_websocket_client, battle_format)
    else:
        battle = await start_standard_battle(ps_websocket_client, battle_format)

    # Prisma defined
    if ShowdownConfig.show_win_streak:
        # Default win streak
        win_streak = 0

        # Get the battle opponent data
        opponent = battle.opponent

        # Get the name for the opponent
        account_name = opponent.account_name

        # Get the user from the database (or create it)
        user = await database.get_user(prisma, account_name)

        # Get the user data for the given format from the database
        format = await database.get_user_format(prisma, user, battle_format)

        # Record found
        if format:
            # Set win streak to record win streak
            win_streak = format.winStreak

            await ps_websocket_client.send_message(
                battle.battle_tag, [f"Win streak for {account_name}: {win_streak}"]
            )

        # Otherwise, do not display

    await ps_websocket_client.send_message(
        battle.battle_tag, ShowdownConfig.pre_battle_msg
    )

    if ShowdownConfig.start_timer:
        await ps_websocket_client.send_message(battle.battle_tag, ["/timer on"])

    return battle


async def pokemon_battle(ps_websocket_client, battle_format, prisma):
    # Start the pokemon battle
    battle = await start_battle(ps_websocket_client, battle_format, prisma)

    # Infinite Loop
    while True:
        # Get the message from the showdown web socket
        msg = await ps_websocket_client.receive_message()

        # If the battle has ended
        if battle_is_finished(battle.battle_tag, msg):
            # Default: No winner
            winner_name = None

            # If this is the winning message
            if constants.WIN_STRING in msg:
                # Get the winner from the message
                winner_name = msg.split(constants.WIN_STRING)[-1].split("\n")[0].strip()
            else:  # No winner
                winner_name = None

            logger.debug("Winner: {}".format(winner_name))

            # Get the battle opponent data
            opponent = battle.opponent

            loser_name = None

            # Bot won the game
            if winner_name == ShowdownConfig.username:
                # Set loser to the opponent
                loser_name = opponent.account_name

            # Opponent won the game
            elif winner_name == opponent.account_name:
                # Set loser to the bot's name
                loser_name = ShowdownConfig.username

            # Winner is found
            if winner_name:
                # Get the user with the winner's name from the database
                winner = await database.get_user(prisma, winner_name)

                # Update the winner's data for the battle format
                winner_streak = await database.update_winner(
                    prisma, winner, battle_format
                )

                # Win streak messages are enabled
                if (
                    winner_name == opponent.account_name
                    and ShowdownConfig.show_win_streak
                ):
                    await ps_websocket_client.send_message(
                        battle.battle_tag,
                        [f"Current win streak for {winner_name}: {winner_streak}"],
                    )

            # Loser is found
            if loser_name:
                # Get the user with the winner's name from the database
                loser = await database.get_user(prisma, loser_name)

                # Update the loser's data for the battle format
                loser_streak = await database.update_loser(prisma, loser, battle_format)

                # Win streak messages are enabled
                if (
                    loser_name == opponent.account_name
                    and ShowdownConfig.show_win_streak
                ):
                    await ps_websocket_client.send_message(
                        battle.battle_tag,
                        [f"Current win streak for {loser_name}: {loser_streak}"],
                    )

            # Send the post-battle message to the channel
            await ps_websocket_client.send_message(
                battle.battle_tag, ShowdownConfig.post_battle_msg
            )

            # Leave the battle room
            await ps_websocket_client.leave_battle(
                battle.battle_tag, save_replay=ShowdownConfig.save_replay
            )

            # Return the battle winner
            return winner_name
        else:  # Battle has not ended
            # Check if a battle action is required
            action_required = await async_update_battle(battle, msg)

            # Action is required, and wait it set to false
            if action_required and not battle.wait:
                # Pick the best move for the battle
                best_move = await async_pick_move(battle)

                # Send the selected move websocket to the client
                await ps_websocket_client.send_message(battle.battle_tag, best_move)
