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


async def update_winner(prisma: Prisma, account_name):
    # Connect to database
    await prisma.connect()

    # Check for winner record
    winner_record = await prisma.records.find_first(where={"name": account_name})

    # Winner record found
    if winner_record:
        # Increment the current win streak
        winStreak = winner_record.winStreak + 1

        # Get current max win streak
        maxWinStreak = winner_record.maxWinStreak

        # Win streak is greater than max win streak
        if winStreak > maxWinStreak:
            # Update the max win streak
            maxWinStreak = winStreak

        await prisma.records.update(
            where={"name": account_name},
            data={
                "wins": winner_record.wins + 1,
                "winStreak": winStreak,
                "maxWinStreak": maxWinStreak,
            },
        )
    else:  # No winner record
        # Fresh win streak
        winStreak = 1

        await prisma.records.create(
            data={
                "name": account_name,
                # Set win count to 1
                "wins": winStreak,
                "winStreak": winStreak,
                "maxWinStreak": winStreak,
            }
        )

    # Disconnect from database
    await prisma.disconnect()

    # Return win streak
    return winStreak


async def update_loser(prisma: Prisma, account_name):
    # Connect to database
    await prisma.connect()

    # Check for loser record
    loser_record = await prisma.records.find_first(where={"name": account_name})

    # Loser record found
    if loser_record:
        await prisma.records.update(
            where={"name": account_name},
            data={
                # Add one to the loss count
                "losses": loser_record.losses + 1,
                # Reset the win streak
                "winStreak": 0,
            },
        )
    else:  # No loser record
        await prisma.records.create(
            data={
                "name": account_name,
                # Set loss count to 1
                "losses": 1,
            }
        )

    # Disconnect from database
    await prisma.disconnect()

    # Win streak broken
    return 0
