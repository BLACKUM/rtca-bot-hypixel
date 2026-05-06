import discord
from discord.ui import View


class AuthorView(View):
    author_id: int | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        from core.config import config
        user_id = interaction.user.id
        if user_id in config.owner_ids:
            return True
        if self.author_id is not None and user_id == self.author_id:
            return True
        return False
