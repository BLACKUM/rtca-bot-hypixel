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
        self.app.router.add_get('/v1/rng', self.handle_rng_get)
        self.app.router.add_post('/v1/rng', self.handle_rng_post)
        self.app.router.add_post('/v1/daily', self.handle_daily)
        self.app.router.add_post('/v1/rtca', self.handle_rtca)
        self.app.router.add_get('/v1/leaderboard', self.handle_leaderboard)
        self.app.router.add_get('/v1/key', self.handle_key)
        
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

    async def handle_key(self, request):
        from services.security import get_current_key_string
        return web.json_response({
            'status': 'success',
            'key': get_current_key_string()
        })

    async def index(self, request):
        return web.json_response({
            'status': 'online', 
            'bot': str(self.bot.user),
            'version': '1.0.0'
        })

    async def handle_profile(self, request):
        try:
            profile_name = request.query.get('profile')
            
            log_info(f"[API] Received profile request for: {player} (Profile: {profile_name})")
            
            from services.api import get_uuid, get_bazaar_prices, get_dungeon_stats, get_recent_runs, get_profile_data
            
            uuid = await get_uuid(player)
            if not uuid:
                return web.json_response({'error': 'Player not found'}, status=404)
            profile_data = await get_profile_data(uuid)
            profiles_list = []
            
            target_found = False
            if profile_name and profile_data and "profiles" in profile_data:
                for p in profile_data["profiles"]:
                    if p.get("cute_name", "").lower() == profile_name.lower():
                        target_found = True
                        break

            if profile_data and "profiles" in profile_data:
                for p in profile_data["profiles"]:
                    is_selected = p.get("selected", False)
                    name = p.get("cute_name")
                    
                    if target_found:
                        is_selected = (name.lower() == profile_name.lower())

                    profiles_list.append({
                        "name": name,
                        "id": p.get("profile_id"),
                        "selected": is_selected
                    })

            stats = await get_dungeon_stats(uuid, profile_name=profile_name)
            recent_runs = await get_recent_runs(uuid, profile_name=profile_name)
            
            teammates = self.bot.recent_manager.get_teammates(uuid)
            
            daily_stats = None
            user_id = self.bot.daily_manager.get_user_id_by_ign(player)
            if user_id:
                daily_stats = self.bot.daily_manager.get_daily_stats(user_id)

            if stats:
                data = stats
                data['recent_runs'] = recent_runs if recent_runs else []
                data['teammates'] = teammates if teammates else []
                daily_stats = daily_stats if daily_stats else {}
                
                monthly_stats = None
                if user_id:
                    monthly_stats = self.bot.daily_manager.get_monthly_stats(user_id)
                
                data['daily_stats'] = daily_stats
                data['monthly_stats'] = monthly_stats if monthly_stats else {}
                data['profiles'] = profiles_list
                
                return web.json_response({'status': 'success', 'player': player, 'data': data})
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

    async def handle_rng_get(self, request):
        try:
            player = request.query.get('player')
            
            if not player:
                return web.json_response({'error': 'Missing player parameter'}, status=400)

            log_info(f"[API] Received RNG data request for: {player}")
            
            from services.api import get_uuid, get_all_prices, get_dungeon_runs
            from core.game_data import RNG_CATEGORIES, RNG_DROPS, DROP_IDS, CHEST_COSTS, GLOBAL_DROPS
            
            uuid = await get_uuid(player)
            if not uuid:
                return web.json_response({'error': 'Player not found'}, status=404)
            
            user_id = self.bot.daily_manager.get_user_id_by_ign(player)
            if not user_id:
                user_id = uuid
            
            user_stats = self.bot.rng_manager.get_user_stats(str(user_id))
            prices = await get_all_prices()
            run_counts = await get_dungeon_runs(uuid)
            
            return web.json_response({
                'status': 'success',
                'player': player,
                'data': {
                    'drops': user_stats,
                    'prices': prices,
                    'run_counts': run_counts,
                    'categories': RNG_CATEGORIES,
                    'items': RNG_DROPS,
                    'item_ids': DROP_IDS,
                    'chest_costs': CHEST_COSTS,
                    'global_drops': GLOBAL_DROPS
                }
            })

        except Exception as e:
            log_error(f"[API] Error processing RNG GET request: {e}")
            return web.json_response({'error': str(e)}, status=500)

    async def handle_rng_post(self, request):
        try:
            data = await request.json()
            player = data.get('player')
            action = data.get('action')
            category = data.get('category')
            item = data.get('item')
            
            if not player or not action or not category or not item:
                return web.json_response({'error': 'Missing required fields'}, status=400)

            log_info(f"[API] Received RNG update: {data}")
            
            from services.api import get_uuid
            
            uuid = await get_uuid(player)
            if not uuid:
                return web.json_response({'error': 'Player not found'}, status=404)
            
            user_id = self.bot.daily_manager.get_user_id_by_ign(player)
            if not user_id:
                user_id = uuid
            
            dev_key = request.headers.get('X-Developer-Key', '')
            encrypted_id = request.headers.get('X-Encrypted-Identity', '')
            
            from services.security import check_developer_key, verify_identity
            
            is_dev = check_developer_key(dev_key)
            is_verified_owner = verify_identity(encrypted_id, str(uuid))
            
            if not is_dev and not is_verified_owner:
                log_error(f"[API] Security check failed for {player} (UUID: {uuid})")
                return web.json_response({'error': 'Unauthorized: Invalid identity or key'}, status=403)

            if action == 'increment':
                new_count = await self.bot.rng_manager.update_drop(str(user_id), category, item, 1)
            elif action == 'decrement':
                new_count = await self.bot.rng_manager.update_drop(str(user_id), category, item, -1)
            elif action == 'set':
                count = data.get('count', 0)
                new_count = await self.bot.rng_manager.set_drop_count(str(user_id), category, item, count)
            else:
                return web.json_response({'error': 'Invalid action'}, status=400)

            return web.json_response({'status': 'success', 'item': item, 'count': new_count})
        except Exception as e:
            log_error(f"[API] Error processing RNG POST: {e}")
            return web.json_response({'error': str(e)}, status=500)

    async def handle_rtca(self, request):
        try:
            data = await request.json()
            player = data.get('player')
            floor_name = data.get('floor', 'M7')
            
            if not player:
                 return web.json_response({'error': 'Missing player field'}, status=400)

            log_info(f"[API] Received RTCA simulation request for: {player} ({floor_name})")
            
            from services.api import get_uuid, get_profile_data
            from core.game_data import FLOOR_XP_MAP
            from core.config import config
            from modules.dungeons import default_bonuses
            from services.xp_calculations import calculate_dungeon_xp_per_run
            from services.simulation_logic import simulate_async
            
            uuid = await get_uuid(player)
            if not uuid:
                return web.json_response({'error': 'Player not found'}, status=404)

            profile_data = await get_profile_data(uuid)
            if not profile_data:
                return web.json_response({'error': 'Profile data not found'}, status=404)
            
            profiles = profile_data.get("profiles")
            if not profiles:
                return web.json_response({'error': 'No profiles found'}, status=404)

            best_profile = next((p for p in profiles if p.get("selected")), profiles[0])
            member = best_profile.get("members", {}).get(uuid, {})
            dungeons = member.get("dungeons", {})
            player_classes = dungeons.get("player_classes", {})

            dungeon_classes = {
                cls: data.get("experience", 0)
                for cls, data in player_classes.items()
                if cls in ["archer", "berserk", "healer", "mage", "tank"]
            }

            if not dungeon_classes:
                 return web.json_response({'error': 'No dungeon classes found'}, status=404)

            player_data = member.get("player_data", {})
            perks = player_data.get("perks", {})
            class_boosts = {
                "archer": perks.get("toxophilite", 0) * 0.02,
                "berserk": perks.get("unbridled_rage", 0) * 0.02,
                "healer": perks.get("heart_of_gold", 0) * 0.02,
                "mage": perks.get("cold_efficiency", 0) * 0.02,
                "tank": perks.get("diamond_in_the_rough", 0) * 0.02,
            }

            base_floor = FLOOR_XP_MAP.get(floor_name.upper(), config.xp_per_run_default)
            
            request_bonuses = data.get('bonuses', {})
            
            def get_bonus(key, default):
                val = request_bonuses.get(key)
                if val is not None:
                    try:
                        return float(val)
                    except:
                        pass
                return default

            bonuses = {
                "ring": get_bonus("ring", default_bonuses["ring"]),
                "hecatomb": get_bonus("hecatomb", default_bonuses["hecatomb"]),
                "scarf_accessory": get_bonus("scarf_accessory", default_bonuses["scarf_accessory"]),
                "scarf_attribute": get_bonus("scarf_attribute", default_bonuses["scarf_attribute"]),
                "global": get_bonus("global", default_bonuses["global"]),
                "mayor": get_bonus("mayor", default_bonuses["mayor"]),
                "class_boosts": class_boosts
            }

            log_info(f"Simulating for {player} on {floor_name}")
            log_info(f"Dungeon Classes: {dungeon_classes}")
            log_info(f"Bonuses: {bonuses}")
            
            runs_total, results = await simulate_async(dungeon_classes, base_floor, bonuses)
            
            return web.json_response({
                'status': 'success', 
                'player': player, 
                'total_runs': runs_total,
                'results': results,
                'bonuses': bonuses
            })

        except Exception as e:
            log_error(f"[API] Error processing RTCA request: {e}")
            import traceback
            traceback.print_exc()
            return web.json_response({'error': str(e)}, status=500)

    async def handle_leaderboard(self, request):
        try:
            period = request.query.get('period', 'daily')
            metric = request.query.get('metric', 'xp')
            limit = int(request.query.get('limit', '10'))
            page = int(request.query.get('page', '1'))
            
            log_info(f"[API] Received leaderboard request: period={period}, metric={metric}, limit={limit}, page={page}")
            
            data = self.bot.daily_manager.get_leaderboard(period, metric)
            
            if data is None:
                 return web.json_response({'error': 'Failed to fetch leaderboard'}, status=500)
            
            total_entries = len(data)
            total_pages = (total_entries + limit - 1) // limit

            find_player = request.query.get('find_player')
            if find_player:
                find_player = find_player.lower()
                found_index = -1
                for i, entry in enumerate(data):
                    if entry['ign'].lower() == find_player:
                        found_index = i
                        break
                
                if found_index != -1:
                    page = (found_index // limit) + 1
                else:
                    return web.json_response({'error': 'Player not found on leaderboard'}, status=404)
            
            if page < 1: page = 1
            if page > total_pages and total_pages > 0: page = total_pages
            
            start = (page - 1) * limit
            end = start + limit
            
            limited_data = data[start:end]
            
            last_updated = self.bot.daily_manager.get_last_updated()
            
            return web.json_response({
                'status': 'success',
                'period': period,
                'metric': metric,
                'page': page,
                'total_pages': total_pages,
                'last_updated': last_updated,
                'data': limited_data
            })

        except Exception as e:
            log_error(f"[API] Error processing leaderboard request: {e}")
            return web.json_response({'error': str(e)}, status=500)

async def setup(bot):
    await bot.add_cog(API(bot))
