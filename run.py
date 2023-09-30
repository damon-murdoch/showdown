import asyncio
from prisma import Prisma
import logging
import traceback
from datetime import datetime

from config import ShowdownConfig, init_logging

from showdown.run_battle import pokemon_battle
from showdown.websocket_client import PSWebsocketClient

logger = logging.getLogger(__name__)


async def showdown():
    # Configure the showdown bot
    ShowdownConfig.configure()

    # Configure logging
    init_logging(ShowdownConfig.log_level, ShowdownConfig.log_to_file)

    # Database placeholder
    prisma = None

    # If prisma is enabled
    if ShowdownConfig.prisma_enabled:
        # Create the prisma client
        prisma = Prisma()

    # Create the showdown web socket client
    ps_websocket_client = await PSWebsocketClient.create(
        ShowdownConfig.username, ShowdownConfig.password, ShowdownConfig.websocket_uri
    )

    # Log into the web socket client
    await ps_websocket_client.login()

    # Custom avatar is defined
    if ShowdownConfig.avatar:
        # Set the account avatar to the custom avatar
        await ps_websocket_client.send_message("", [f"/avatar {ShowdownConfig.avatar}"])

    # Infinite loop
    while True:
        # If showdown file logging is enabled
        if ShowdownConfig.log_to_file:
            # Log rollover to the file
            ShowdownConfig.log_handler.do_rollover(
                datetime.now().strftime("%Y-%m-%dT%H:%M:%S.log")
            )

        # Wait for a challenge in one of the allowed gamemodes
        battle_format = await ps_websocket_client.accept_challenge(
            ShowdownConfig.allowed_modes, ShowdownConfig.room_name
        )

        # Handle the battle in the format which has been challenged
        await pokemon_battle(ps_websocket_client, battle_format, prisma)


# If this is the main process
if __name__ == "__main__":
    try:
        # Run the showdown script
        asyncio.run(showdown())

    # An error occured
    except Exception as e:
        # Write the error to the logging function
        logger.error(traceback.format_exc())

        # Exit the script
        exit(1)
