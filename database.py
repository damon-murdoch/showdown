from prisma import Prisma


async def get_player(prisma: Prisma, account_name):
    # Connect to database
    await prisma.connect()

    # Check for opponent play record
    record = await prisma.records.find_first(where={"name": account_name})

    # Disconnect from database
    await prisma.disconnect()

    # Return record
    return record


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
