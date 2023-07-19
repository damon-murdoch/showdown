import asyncio
import constants
import websockets
import requests
import json
import time

import logging
from config import ShowdownConfig

from teams import get_team
logger = logging.getLogger(__name__)

from data.mods.apply_mods import apply_mods


class LoginError(Exception):
    pass


class SaveReplayError(Exception):
    pass


class PSWebsocketClient:

    websocket = None
    address = None
    login_uri = None
    username = None
    password = None
    last_message = None
    last_challenge_time = 0

    @classmethod
    async def create(cls, username, password, address):
        self = PSWebsocketClient()
        self.username = username
        self.password = password
        self.address = "ws://{}/showdown/websocket".format(address)
        self.websocket = await websockets.connect(self.address)
        self.login_uri = "https://play.pokemonshowdown.com/action.php"
        return self

    async def join_room(self, room_name):
        message = "/join {}".format(room_name)
        await self.send_message('', [message])
        logger.debug("Joined room '{}'".format(room_name))

    async def receive_message(self):
        message = await self.websocket.recv()
        logger.debug("Received message from websocket: {}".format(message))
        return message

    async def send_message(self, room, message_list):
        message = room + "|" + "|".join(message_list)
        logger.debug("Sending message to websocket: {}".format(message))
        await self.websocket.send(message)
        self.last_message = message

    async def get_id_and_challstr(self):
        while True:
            message = await self.receive_message()
            split_message = message.split('|')
            if split_message[1] == 'challstr':
                return split_message[2], split_message[3]

    async def login(self):
        logger.debug("Logging in...")
        client_id, challstr = await self.get_id_and_challstr()
        if self.password:
            response = requests.post(
                self.login_uri,
                data={
                    'act': 'login',
                    'name': self.username,
                    'pass': self.password,
                    'challstr': "|".join([client_id, challstr])
                }
            )

        else:
            response = requests.post(
                self.login_uri,
                data={
                    'act': 'getassertion',
                    'userid': self.username,
                    'challstr': '|'.join([client_id, challstr]),
                }
            )

        if response.status_code == 200:
            if self.password:
                response_json = json.loads(response.text[1:])

                if 'actionerror' in response_json: 
                    logger.error("Login Unsuccessful")
                    raise LoginError(response_json['actionerror'])

                assertion = response_json.get('assertion')
            else:
                assertion = response.text

            message = ["/trn " + self.username + ",0," + assertion]
            logger.debug("Successfully logged in")
            await self.send_message('', message)
        else:
            logger.error("Could not log-in\nDetails:\n{}".format(response.content))
            raise LoginError("Could not log-in")

    async def get_team(self, battle_format): 
        if battle_format in constants.RANDOM_FORMATS:
            return None
        else: 
            return get_team(ShowdownConfig.pokemon_mode)
            

    async def update_team(self, battle_format, team):
        if battle_format in constants.RANDOM_FORMATS:
            logger.info("Setting team to None because the pokemon mode is {}".format(battle_format))
            message = ["/utm None"]
        else:
            message = ["/utm {}".format(team)]
        await self.send_message('', message)

    async def challenge_user(self, user_to_challenge, battle_format, team):
        logger.debug("Challenging {}...".format(user_to_challenge))
        if time.time() - self.last_challenge_time < 10:
            logger.info("Sleeping for 10 seconds because last challenge was less than 10 seconds ago")
            await asyncio.sleep(10)
        await self.update_team(battle_format, team)
        message = ["/challenge {},{}".format(user_to_challenge, battle_format)]
        await self.send_message('', message)
        self.last_challenge_time = time.time()

    async def accept_challenge(self, allowed_formats, room_name):
        if room_name is not None:
            await self.join_room(room_name)

        logger.debug(f"Waiting for a {','.join(allowed_formats)} challenge ...")

        username = None

        team = None

        while username is None:
            msg = await self.receive_message()
            split_msg = msg.split('|')

            if (
                len(split_msg) == 9 and
                split_msg[1] == "pm" and
                split_msg[3].strip().replace("!", "").replace("‽", "") == self.username and
                split_msg[4].startswith("/challenge")
            ):
                # Temporary username
                _username = split_msg[2].strip()

                # Get the format the player was challenged to
                challenge_format = split_msg[5]

                # If the format is not in the list of allowed formats
                if challenge_format not in allowed_formats:
                    # Reject the challenge
                    await self.send_message('', [f"/reject {_username}"])
                    # Inform the player of the correct format
                    await self.send_message('', [f"/msg {_username},I am currently only accepting challenges in the following format(s):", f"'{','.join(allowed_formats)}'"])

                else: # Passes format check

                    # Get the team for the chalenge format
                    team = await self.get_team(challenge_format)

                    # If no team is returned, and the format is not a random metagame
                    if team == None and challenge_format not in constants.RANDOM_FORMATS:
                        # Reject the challenge
                        await self.send_message('', [f"/reject {_username}"])
                        # Inform the player of the correct format
                        await self.send_message('', [f"/msg {_username},No teams found for format '{challenge_format}', sorry! Please challenge me to something else!"])

                    else: # Random format / team found
                        username = _username

        # Update the team for the bot
        await self.update_team(challenge_format, team)

        # Apply the mods for the format
        apply_mods(challenge_format)

        message = ["/accept " + username]
        await self.send_message('', message)

        # Return the challenge format
        return challenge_format

    async def search_for_match(self, battle_format, team):
        logger.debug("Searching for ranked {} match".format(battle_format))
        await self.update_team(battle_format, team)
        message = ["/search {}".format(battle_format)]
        await self.send_message("", message)

    async def leave_battle(self, battle_tag, save_replay=False):
        if save_replay:
            await self.save_replay(battle_tag)

        message = ["/leave {}".format(battle_tag)]
        await self.send_message('', message)

        while True:
            msg = await self.receive_message()
            if battle_tag in msg and 'deinit' in msg:
                return

    async def save_replay(self, battle_tag):
        message = ["/savereplay"]
        await self.send_message(battle_tag, message)

        while True:
            msg = await self.receive_message()
            if msg.startswith("|queryresponse|savereplay|"):
                obj = json.loads(msg.replace("|queryresponse|savereplay|", ""))
                log = obj['log']
                identifier = obj['id']
                post_response = requests.post(
                    "https://play.pokemonshowdown.com/~~showdown/action.php?act=uploadreplay",
                    data={
                        "log": log,
                        "id": identifier
                    }
                )
                if post_response.status_code != 200:
                    raise SaveReplayError("POST to save replay did not return a 200: {}".format(post_response.content))
                break
