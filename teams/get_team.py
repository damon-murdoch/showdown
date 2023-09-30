import os
import random
import logging

from teams.team_converter import export_factory_to_packed, export_to_packed

from config import ShowdownConfig

logger = logging.getLogger(__name__)

TEAM_JSON_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "teams")


def get_team(format=None):
    logger.debug(f"Selecting team for format {format} ...")

    # Team Data (None by default)
    team: str | None = None

    # Files to process
    files = []

    # Paths to process
    paths = []

    # Get the full path to the teams file / folder
    root_path = os.path.join(TEAM_JSON_DIR)

    # Path is directory and format defined
    if os.path.isdir(root_path) and format:
        # Add format to path list
        root_path = os.path.join(root_path, format)

    # Add path to paths
    paths = [root_path]

    # While still paths to traverse
    while len(paths) > 0:
        # Pop the top path from the list
        path = paths.pop()

        # Format path is folder
        if os.path.isdir(path):
            # Get all of the items in the folder
            for item in os.listdir(path):
                # Add item to list
                paths.append(item)

        # Format path is factory file
        elif ShowdownConfig.factory_enabled and os.path.isfile(f"{path}.factory"):
            files.append(f"{path}.factory")

        # Format path is team file
        elif ShowdownConfig.team_enabled and os.path.isfile(f"{path}.team"):
            files.append(f"{path}.team")

        # Otherwise, ignore - Invalid file

    # If at least one file found
    if len(files) > 0:
        # Choose a random file from the list
        file = random.choice(files)

        logger.debug(f"Reading data from file '{os.path.basename(file)}' ...")

        # Open the chosen file
        with open(file, "r") as f:
            team_json = f.read()

            ext = os.path.splitext(file)[1]

            # File is a team
            if ext == ".team":
                # Pack the team data
                team = export_to_packed(team_json)

            # File is a factory
            elif ext == ".factory":
                # Pack the team data
                team = export_factory_to_packed(team_json)

    # Else, 'None' will be returned

    # Return the team
    return team
