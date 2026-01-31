from aiohttp import web
from discord.ext import commands
from core.logger import log_info, log_error
import os

class API(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.app = web.Application()
        self.app.router.add_get('/', self.index)
        self.app.router.add_get('/v1/profile', self.handle_profile)
        self.app.router.add_post('/v1/rng', self.handle_rng)
        self.app.router.add_post('/v1/daily', self.handle_daily)
        
        self.runner = None
        self.site = None
        
        self.host = os.getenv('API_HOST', '0.0.0.0')
        self.port = int(os.getenv('API_PORT', '8080'))

    async def handle_profile(self, request):
        try:
            player = request.query.get('player')
            
            if not player:
                 return web.json_response({'error': 'Missing player parameter'}, status=400)

            log_info(f"[API] Received profile request for: {player}")
            
            from services.api import get_uuid, get_dungeon_stats
            
            uuid = await get_uuid(player)
            if not uuid:
                return web.json_response({'error': 'Player not found'}, status=404)
                
            stats = await get_dungeon_stats(uuid)
            
            if stats:
                return web.json_response({'status': 'success', 'player': player, 'data': stats})
            else:
                 return web.json_response({'error': 'Could not fetch stats'}, status=502)

        except Exception as e:
            log_error(f"[API] Error processing profile request: {e}")
            return web.json_response({'error': str(e)}, status=500)

    async def handle_daily(self, request):
        try:
            data = await request.json()
            player = data.get('player')
            
            if not player:
                 return web.json_response({'error': 'Missing player field'}, status=400)

            log_info(f"[API] Received daily update request for: {player}")
            
            user_id = self.bot.daily_manager.get_user_id_by_ign(player)
            if not user_id:
                return web.json_response({'error': 'Player not tracked'}, status=404)
                
            uuid = self.bot.daily_manager.data["users"][user_id]["uuid"]
            
            from services.api import get_dungeon_xp
            xp_data = await get_dungeon_xp(uuid)
            
            if xp_data:
                await self.bot.daily_manager.update_user_data(user_id, xp_data, save=True)
                log_info(f"[API] Updated daily stats for {player}")
                return web.json_response({'status': 'updated', 'player': player})
            else:
                 return web.json_response({'error': 'Hypixel API failure'}, status=502)

        except Exception as e:
            log_error(f"[API] Error processing daily update: {e}")
            return web.json_response({'error': str(e)}, status=500)

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
