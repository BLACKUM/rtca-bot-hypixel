import aiohttp
from aiohttp import web
import json
import asyncio
from core.logger import log_info, log_error
from core.config import config, IRC_WEBHOOK_URL
import discord

class IrcHandler:
    def __init__(self, bot):
        self.bot = bot
        self.connections = set()
        self.webhook_session = None

    async def initialize(self):
        self.webhook_session = aiohttp.ClientSession()
        log_info("IRC Handler initialized.")

    async def close(self):
        if self.webhook_session:
            await self.webhook_session.close()
        log_info("IRC Handler closed.")

    async def handle_websocket(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        self.connections.add(ws)
        log_info(f"New IRC connection established. Total: {len(self.connections)}")

        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    await self.process_mod_message(data)
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    log_error(f"IRC WebSocket connection closed with exception {ws.exception()}")
        finally:
            self.connections.remove(ws)
            log_info(f"IRC connection closed. Total: {len(self.connections)}")

        return ws

    async def process_mod_message(self, data):
        user = data.get("user", "Unknown")
        uuid = data.get("uuid", "")
        message = data.get("message", "")

        if not message or not IRC_WEBHOOK_URL:
            return

        avatar_url = f"https://mc-heads.net/avatar/{uuid}" if uuid else None

        try:
            webhook = discord.Webhook.from_url(IRC_WEBHOOK_URL, session=self.webhook_session)
            await webhook.send(
                content=message,
                username=user,
                avatar_url=avatar_url
            )
        except Exception as e:
            log_error(f"Failed to send IRC message to Discord: {e}")

    async def broadcast_to_mods(self, user, message):
        if not self.connections:
            return

        payload = json.dumps({
            "type": "chat",
            "user": user,
            "message": message
        })

        tasks = [ws.send_str(payload) for ws in self.connections]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def on_discord_message(self, message):
        if message.author.bot:
            return
        
        if message.channel.id != config.irc_channel_id:
            return

        content = message.clean_content
        user = message.author.display_name

        asyncio.create_task(self.broadcast_to_mods(user, content))

irc_handler = None

def init_irc_handler(bot):
    global irc_handler
    irc_handler = IrcHandler(bot)
    return irc_handler

def get_irc_handler():
    return irc_handler
