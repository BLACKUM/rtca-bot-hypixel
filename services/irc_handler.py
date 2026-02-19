import aiohttp
from aiohttp import web
import json
import asyncio
from core.logger import log_info, log_error
from core.config import config, IRC_WEBHOOK_URL, IRC_CHANNEL_ID
import discord
import time

class IrcHandler:
    def __init__(self, bot):
        self.bot = bot
        self.connections = {}
        self.history = {}
        self.webhook_session = None
        self.history_limit = 100

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

        provided_key = request.query.get("key", "")
        from services.security import check_developer_key
        is_admin = check_developer_key(provided_key)
        
        self.connections[ws] = {"is_admin": is_admin}
        log_info(f"New IRC connection established. Admin: {is_admin}. Total: {len(self.connections)}")

        await ws.send_str(json.dumps({
            "type": "auth",
            "is_admin": is_admin
        }))

        for channel, messages in self.history.items():
            if channel == "admin" and not is_admin:
                continue
            await ws.send_str(json.dumps({
                "type": "history",
                "channel": channel,
                "messages": messages
            }))

        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    await self.process_mod_message(ws, data)
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    log_error(f"IRC WebSocket connection closed with exception {ws.exception()}")
        finally:
            if ws in self.connections:
                del self.connections[ws]
            log_info(f"IRC connection closed. Total: {len(self.connections)}")

        return ws

    async def process_mod_message(self, ws, data):
        user = data.get("user", "Unknown")
        uuid = data.get("uuid", "")
        message = data.get("message", "")
        channel = data.get("channel", "general")
        timestamp = data.get("timestamp", int(time.time() * 1000))

        if channel == "admin" and not self.connections.get(ws, {}).get("is_admin", False):
            log_error(f"Unauthorized admin channel message from {user}")
            return

        from core.config import IRC_WEBHOOK_URL, ADMIN_WEBHOOK_URL
        
        target_webhook_url = IRC_WEBHOOK_URL
        if channel == "admin":
            target_webhook_url = ADMIN_WEBHOOK_URL

        if not message or not target_webhook_url:
            return

        avatar_url = f"https://mc-heads.net/avatar/{uuid}" if uuid else None

        try:
            webhook = discord.Webhook.from_url(target_webhook_url, session=self.webhook_session)
            await webhook.send(
                content=message,
                username=user,
                avatar_url=avatar_url
            )
            
            await self.broadcast_to_mods(user, message, channel, exclude_ws=ws, timestamp=timestamp)
        except Exception as e:
            log_error(f"Failed to send IRC message to Discord: {e}")

    async def broadcast_to_mods(self, user, message, channel="general", exclude_ws=None, timestamp=None):
        if timestamp is None:
            timestamp = int(time.time() * 1000)

        if channel not in self.history:
            self.history[channel] = []
        
        self.history[channel].append({"user": user, "message": message, "timestamp": timestamp})
        if len(self.history[channel]) > self.history_limit:
            self.history[channel].pop(0)

        if not self.connections:
            return

        payload = json.dumps({
            "type": "chat",
            "user": user,
            "message": message,
            "channel": channel,
            "timestamp": timestamp
        })

        tasks = []
        for ws, info in self.connections.items():
            if ws == exclude_ws:
                continue
            if channel == "admin" and not info.get("is_admin", False):
                continue
            tasks.append(ws.send_str(payload))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def on_discord_message(self, message):
        if message.author.bot:
            return
        
        from core.secrets import IRC_CHANNEL_ID, ANNOUNCEMENTS_CHANNEL_ID, ADMIN_CHANNEL_ID
        
        channel_map = {
            IRC_CHANNEL_ID: "general",
            ANNOUNCEMENTS_CHANNEL_ID: "announcements",
            ADMIN_CHANNEL_ID: "admin"
        }
        
        if message.channel.id not in channel_map:
            return

        irc_channel = channel_map[message.channel.id]
        content = message.clean_content
        user = message.author.display_name
        timestamp = int(message.created_at.timestamp() * 1000)
        
        await self.broadcast_to_mods(user, content, irc_channel, timestamp=timestamp)

irc_handler = None

def init_irc_handler(bot):
    global irc_handler
    irc_handler = IrcHandler(bot)
    return irc_handler

def get_irc_handler():
    return irc_handler
