from .load_team import load_team
from .load_factory import load_factory

import constants
from config import ShowdownConfig

def get_team(battle_format: str | None = None):

    # Team Data (None by default)
    team: str | None = None

    # If the team mode is set to 'factory team'
    if ShowdownConfig.team_mode == constants.FACTORY_TEAM:

        # Generate a team using the factory sets
        team = load_factory(ShowdownConfig.factory, battle_format)

    # Mode is set to 'sample team'
    elif ShowdownConfig.team_mode == constants.SAMPLE_TEAM:

        # Use one of the provided teams
        team = load_team(ShowdownConfig.team, battle_format)

    else: 
        raise ValueError("Invalid Team Mode: {}".format(ShowdownConfig.team_mode))
    
    # Return the team
    return team