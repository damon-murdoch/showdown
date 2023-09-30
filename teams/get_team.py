import os
import random
import logging
import requests
from bs4 import BeautifulSoup

from teams.team_converter import export_factory_to_packed, export_to_packed

from config import ShowdownConfig

logger = logging.getLogger(__name__)

TEAM_JSON_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "teams")


def get_user_team(url):
    # Team Data (None by default)
    team: str | None = None

    # Example Url: https://pokepast.es/b48ac6bb84fccc8f

    # Url HAS to start with this
    if url.startswith("https://pokepast.es/"):
        # Get content from the url
        response = requests.get(url)

        # If success status code
        if response.status_code == 200:
            # Get content parser
            parser = BeautifulSoup(response.text, "html.parser")

            # Get all of the articles (pokemon)
            articles = parser.find_all("article")

            # List of sets
            sets = []

            # Loop over all of the articles
            for article in articles:
                # Get the text from the article and trim the whitespace
                set = article.text.trim()

                # Add set to the list
                sets.append(set)

            # Join the sets, placing spaces between each
            # Double spacing to ensure newline between sets
            paste = "\n\n".join(sets)

            # If there are more than six sets
            if len(sets) > 6:
                # Generate a normal team from the sets
                team = export_to_packed(paste)
            else:  # There are less than six sets
                # Generate a factory team from the sets
                team = export_factory_to_packed(paste)

        else:  # Else, failure success code
            logger.debug(f"Bad status code: {response.status_code} ...")
    else:  # Else, none will be returned
        logger.debug(f"Bad url provided: {url} ...")

    # Return the team
    return team


def get_team(format, method=None, team_link=None):
    logger.debug(f"Selecting team for format {format} ...")

    # Team Data (None by default)
    team: str | None = None

    # Selection method is user, and team link provided
    if method == "user" and team_link:
        team = get_user_team(team_link)
    else:  # Any other selection method / no team
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

            # Factory method is selected (or no specific method), factory is enabled in the config and the file is a .factory file
            elif (
                (not method or method == "factory")
                and ShowdownConfig.factory_enabled
                and os.path.isfile(f"{path}.factory")
            ):
                # Add the factory to the factories list
                files.append(f"{path}.factory")

            # Team method is selected (or no specific method), team is enabled in the config and the file is a .team file
            elif (
                (not method or method == "team")
                and ShowdownConfig.team_enabled
                and os.path.isfile(f"{path}.team")
            ):
                # Add the file to the files list
                files.append(f"{path}.team")

            # Otherwise, file is ignored

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
