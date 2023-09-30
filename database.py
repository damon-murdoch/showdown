from prisma import Prisma
import re


def normalise_string(text):
    # Convert the string to lowercase
    text = text.lower()

    # Remove any spaces from the string
    text = text.replace(" ", "")

    # Use a regular expression to remove non-ASCII characters
    text = re.sub(r"[^\x00-\x7F]+", "", text)

    # Return the formatted text
    return text


async def get_user(prisma: Prisma, account_name):
    # Connect to database
    await prisma.connect()

    # Get the normalised version of the account name
    name = normalise_string(account_name)

    # Check for opponent play record
    user = await prisma.user.find_first(where={"username": name})

    # User not found
    if not user:
        # Create a new user for the account name
        user = await prisma.user.create(data={"username": name})

    # Disconnect from database
    await prisma.disconnect()

    # Return record
    return user


async def get_user_format(prisma: Prisma, user, battle_format):
    # Connect to database
    await prisma.connect()

    # Find the user's format data
    format = await prisma.format.find_first(
        where={"username": user.username, "format": battle_format}
    )

    # Format data not found
    if not format:
        # Create new format data for the account name
        format = await prisma.format.create(
            data={"username": user.username, "format": battle_format}
        )

    # Disconnect from database
    await prisma.disconnect()

    # Return the format
    return format


async def update_winner(prisma: Prisma, user, battle_format):
    # Check for winner record
    record = await get_user_format(prisma, user, battle_format)

    # Connect to database
    await prisma.connect()

    # Increment the current win streak
    winStreak = record.winStreak + 1

    # Get current max win streak
    maxWinStreak = record.maxWinStreak

    # Win streak is greater than max win streak
    if winStreak > maxWinStreak:
        # Update the max win streak
        maxWinStreak = winStreak

    # Update the winner record
    await prisma.format.update(
        where={"id": record.id},
        data={
            "wins": record.wins + 1,
            "winStreak": winStreak,
            "maxWinStreak": maxWinStreak,
        },
    )

    # Disconnect from database
    await prisma.disconnect()

    # Return win streak
    return winStreak


async def update_loser(prisma: Prisma, user, battle_format):
    # Check for loser record
    record = await get_user_format(prisma, user, battle_format)

    # Connect to database
    await prisma.connect()

    # Update the loser record
    await prisma.format.update(
        where={"id": record.id},
        data={
            # Add one to the loss count
            "losses": record.losses + 1,
            # Reset the win streak
            "winStreak": 0,
        },
    )

    # Disconnect from database
    await prisma.disconnect()

    # Win streak broken
    return 0
