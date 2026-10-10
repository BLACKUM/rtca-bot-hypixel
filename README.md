# rtca-bot-hypixel
Discord bot for calculating class average 50 in Hypixel SkyBlock and tracking RNG drops.

## Features

- **Class Average 50 Simulation**: calculation of how many runs are needed to reach class average 50.
- **RNG Drop Tracker**: Track your rare dungeon drops, calculate total profit, and view profit-per-run.
- **Recent Teammates**: See who you played with in the runs Hypixel currently reports for your profile.
- **Profile Linking**: Link your Discord account to your Hypixel IGN for seamless command usage.
- **Admin Panel**: Comprehensive dashboard for bot management, system operations, and configuration editing.

## Commands

### General
- `/rtca [ign] [floor]`: Run the simulation to calculate how many runs are needed to reach class average 50.
    - `ign`: Optional if account is linked.
    - `floor`: Dungeon floor to simulate (e.g., M7, F7). Default is M7.
- `/rng`: Open the RNG Drop Tracker interface.
    - View drops, set counts, and see profit estimates (needs linked account for profit calculation).
- `/dungeons [ign]`: View dungeon stats and class levels.
- `/recent [ign]`: View teammates from your recent runs.
- `/profile [ign]`: View profile stats and pick your default profile.
- `/link <ign>`: Link your Discord account to a Hypixel username.
- `/unlink`: Unlink your current account.

### Owner Only
- `/admin`: Opens the Administration Panel.
    - **Dungeons**: Manage default simulation settings.
    - **Data**: View linked and registered users.
    - **Config**: Edit bot configuration on the fly.
    - **System**: Update, Restart, Shutdown, Get Logs, and view Host Info.

## Installation

See [QUICKSTART.md](QUICKSTART.md) for detailed installation and setup instructions.

## Credits

- **adjectiven0un**: Inspiration and XP calculation logic from [adjectils](https://adjectils.com/dungeon.html).

## Powered By

- **Hypixel Data**: Official [Hypixel API](https://api.hypixel.net/) for SkyBlock profiles, linked Discord accounts and Bazaar prices.
- **Player Data**: Username to UUID lookup provided by the [Mojang API](https://api.mojang.com/).
- **Auction Data**: Lowest BIN averages provided by [Moulberry's Codes](https://moulberry.codes/).

- **rtca-bot-hypixel** is not affiliated or endorsed by Hypixel!

![ZoKPU0I](https://github.com/user-attachments/assets/fbd17103-215e-4c34-87de-f34828de9a1b)
