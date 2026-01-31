from aiohttp import web
from discord.ext import commands
from core.logger import log_info, log_error
import os

class API(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.app = web.Application()
        self.app.router.add_get('/', self.index)
        self.app.router.add_post('/v1/rng', self.handle_rng)
        
        self.runner = None
        self.site = None
        
        self.host = os.getenv('API_HOST', '0.0.0.0')
        self.port = int(os.getenv('API_PORT', '8080'))

    async def cog_load(self):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()
        log_info(f"API server started on http://{self.host}:{self.port}")

    async def cog_unload(self):
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        log_info("API server stopped.")

    async def index(self, request):
        return web.json_response({
            'status': 'online', 
            'bot': str(self.bot.user),
            'version': '1.0.0'
        })

    async def handle_rng(self, request):
        try:
            data = await request.json()
            if not data.get('item') or not data.get('player'):
                 return web.json_response({'error': 'Missing fields'}, status=400)

            log_info(f"[API] Received RNG drop: {data}")

            return web.json_response({'status': 'received', 'processed': True})
        except Exception as e:
            log_error(f"[API] Error processing RNG drop: {e}")
            return web.json_response({'error': str(e)}, status=500)

async def setup(bot):
    await bot.add_cog(API(bot))
