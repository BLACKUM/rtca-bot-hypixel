# rtca-bot-hypixel
Discord bot for calculating class average 50 in Hypixel SkyBlock, tracking RNG drops, and monitoring daily XP gains.

## Features

- **Class Average 50 Simulation**: calculation of how many runs are needed to reach class average 50.
- **RNG Drop Tracker**: Track your rare dungeon drops, calculate total profit, and view profit-per-run.
- **XP Leaderboards**: Daily and Monthly leaderboards for Catacombs XP gains among tracked users.
- **Profile Linking**: Link your Discord account to your Hypixel IGN for seamless command usage.

## Commands

### General
- `/rtca [ign] [floor]`: Run the simulation to calculate how many runs are needed to reach class average 50.
    - `ign`: Optional if account is linked.
    - `floor`: Dungeon floor to simulate (e.g., M7, F7). Default is M7.
- `/rng`: Open the RNG Drop Tracker interface.
    - View drops, set counts, and see profit estimates (needs linked account for profit calculation).
- `/daily`: View functionality for daily stats.
    - **Leaderboard**: Top users by XP gained today.
    - **Monthly**: Top users by XP gained this month.
    - **Personal**: Your own detailed daily/monthly stats (includes class increments).
- `/link <ign>`: Link your Discord account to a Hypixel username.
- `/unlink`: Unlink your current account.

### Owner Only
- `/setdefault`: Change default simulation bonuses (e.g., Mayor, global boosts).
- `/rngdefault <user>`: Set a default target user for the `/rng` command (for debugging/admin).
- `/adddaily <user> <ign>`: Manually add a user to the daily leaderboard tracking.

## Installation

See [QUICKSTART.md](QUICKSTART.md) for detailed installation and setup instructions.

## Credits
XP calculation logic and api stolen from [adjectils](https://adjectils.com/dungeon.html) by [adjectiven0un](https://github.com/adjectiven0un)

![ZoKPU0I](https://github.com/user-attachments/assets/fbd17103-215e-4c34-87de-f34828de9a1b)
