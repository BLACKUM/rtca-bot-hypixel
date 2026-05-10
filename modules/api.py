from aiohttp import web
from discord.ext import commands
from core.logger import log_info, log_error
from services.rate_limiter import rate_limiter, solo_clear_limiter, solo_clear_uuid_limiter, get_client_ip
import os
import time as _time

class API(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.app = web.Application(middlewares=[rate_limiter.middleware])
        self.app.router.add_get('/', self.index)
        self.app.router.add_get('/v1/profile', self.handle_profile)
        self.app.router.add_get('/v1/rng', self.handle_rng_get)
        self.app.router.add_post('/v1/rng', self.handle_rng_post)
        self.app.router.add_post('/v1/daily', self.handle_daily)
        self.app.router.add_post('/v1/rtca', self.handle_rtca)
        self.app.router.add_get('/v1/leaderboard', self.handle_leaderboard)
        self.app.router.add_get('/v1/key', self.handle_key)
        self.app.router.add_get('/v1/party/list', self.handle_party_list)
        self.app.router.add_post('/v1/party/create', self.handle_party_create)
        self.app.router.add_post('/v1/party/unqueue', self.handle_party_unqueue)
        self.app.router.add_post('/v1/party/update', self.handle_party_update)
        self.app.router.add_get('/v1/names', self.handle_names)
        self.app.router.add_get('/v1/irc', self.handle_irc)
        self.app.router.add_post('/v1/solo_clear', self.handle_solo_clear)
        self.app.router.add_get('/v1/solo_leaderboard', self.handle_solo_leaderboard)
        self.app.router.add_post('/v1/auth/verify', self.handle_auth_verify)
        
        self.runner = None
        self.site = None
        
        self.host = os.getenv('API_HOST', '0.0.0.0')
        self.port = int(os.getenv('API_PORT', '8080'))

    async def cog_load(self):
        import logging
        logging.getLogger("aiohttp.server").setLevel(logging.ERROR)
        
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()
        log_info(f"API server started on http://{self.host}:{self.port}")

    async def cog_unload(self):
        try:
            if self.site:
                await self.site.stop()
            if self.runner:
                await self.runner.cleanup()
            log_info("API server stopped.")
        except Exception as e:
            log_error(f"Error during API shutdown: {e}")

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
            player = request.query.get('player')
            
            log_info(f"[API] Received profile request for: {player} (Profile: {profile_name})")
            
            from services.api import get_uuid, get_dungeon_stats, get_recent_runs, get_profile_data
            
            uuid = await get_uuid(player)
            if not uuid:
                return web.json_response({'error': 'Player not found'}, status=404)
            profile_data = await get_profile_data(uuid)
            profiles_list = []
            
            target_found = False
            if profile_name and profile_data and profile_data.get("profiles"):
                for p in profile_data["profiles"]:
                    if p.get("cute_name", "").lower() == profile_name.lower():
                        target_found = True
                        break

            if profile_data and profile_data.get("profiles"):
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
                async def fetch_profile_stats(p_entry):
                    p_name = p_entry['name']
                    if target_found and p_name.lower() == profile_name.lower() and stats:
                        p_data = stats.copy()
                        p_data['recent_runs'] = recent_runs if recent_runs else []
                        p_data['teammates'] = teammates if teammates else []
                        p_data['daily_stats'] = daily_stats if daily_stats else {}
                        p_data['monthly_stats'] = monthly_stats if monthly_stats else {}
                        p_data['profiles'] = [] 
                        return p_name, p_data
                    
                    p_stats = await get_dungeon_stats(uuid, profile_name=p_name)
                    p_recent = await get_recent_runs(uuid, profile_name=p_name)
                    
                    if p_stats:
                        p_data = p_stats
                        p_data['recent_runs'] = p_recent if p_recent else []
                        p_data['teammates'] = teammates if teammates else []
                        p_data['daily_stats'] = daily_stats if daily_stats else {}
                        p_data['monthly_stats'] = monthly_stats if monthly_stats else {}
                        p_data['profiles'] = []
                        return p_name, p_data
                    return p_name, None

                import asyncio
                tasks = [fetch_profile_stats(p) for p in profiles_list]
                results = await asyncio.gather(*tasks)
                
                stats_map = {name: s_data for name, s_data in results if s_data}
                
                for p in profiles_list:
                    if p['name'] in stats_map:
                        p['stats'] = stats_map[p['name']]

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
            action = data.get('action', 'increment')
            category = data.get('category')
            item = data.get('item')
            
            if not player or not item:
                return web.json_response({'error': 'Missing required fields (player, item)'}, status=400)

            if not category:
                from core.game_data import RNG_DROPS, GLOBAL_DROPS
                for cat, items in RNG_DROPS.items():
                    if item in items:
                        category = cat
                        break
                if not category and item in GLOBAL_DROPS:
                    category = "Global"
            
            if not category:
                category = "Unknown"

            log_info(f"[API] Received RNG update: player={player}, action={action}, category={category}, item={item}")
            
            from services.api import get_uuid
            
            uuid = await get_uuid(player)
            if not uuid:
                return web.json_response({'error': 'Player not found'}, status=404)
            
            user_id = self.bot.daily_manager.get_user_id_by_ign(player)
            if not user_id:
                user_id = uuid
            
            dev_key = request.headers.get('X-Developer-Key', '')
            encrypted_id = request.headers.get('X-Encrypted-Identity', '')
            mojang_server_id = data.get('mojang_server_id', '')
            
            from services.security import check_developer_key, verify_identity
            from services.mojang_auth import verify_session
            
            is_dev = check_developer_key(dev_key)
            is_verified_owner = verify_identity(encrypted_id, str(uuid))
            is_mojang_verified = False
            if mojang_server_id:
                is_mojang_verified = await verify_session(player, str(mojang_server_id), expected_uuid=str(uuid))
            
            auth_method = "developer_key" if is_dev else "mojang_identity" if is_verified_owner and is_mojang_verified else "none"
            request["auth_details"] = {
                "result": "allowed" if is_dev or (is_verified_owner and is_mojang_verified) else "denied",
                "reason": "ok" if is_dev or (is_verified_owner and is_mojang_verified) else (
                    "missing_or_invalid_mojang_session" if is_verified_owner else "invalid_encrypted_identity"
                ),
                "method": auth_method,
                "developer_key": is_dev,
                "encrypted_identity": is_verified_owner,
                "mojang_session": is_mojang_verified,
            }
            
            if not is_dev and not (is_verified_owner and is_mojang_verified):
                log_error(
                    f"[API] Security check failed for {player} (UUID: {uuid}). "
                    f"identity={is_verified_owner}, mojang={is_mojang_verified}"
                )
                return web.json_response(
                    {'error': 'Unauthorized: valid encrypted identity and Mojang session are required'},
                    status=403,
                )

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
            target_profile_name = data.get('profile')
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

            best_profile = None
            
            if target_profile_name:
                for p in profiles:
                    if p.get("cute_name", "").lower() == target_profile_name.lower():
                        best_profile = p
                        break
            
            if not best_profile:
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

    async def handle_party_list(self, request):
        try:
            floor = request.query.get('floor')
            from services.party_manager import party_manager
            parties = party_manager.get_parties(floor)
            return web.json_response({'status': 'success', 'parties': parties})
        except Exception as e:
            log_error(f"[API] Error in party list: {e}")
            return web.json_response({'error': str(e)}, status=500)

    async def handle_party_create(self, request):
        try:
            data = await request.json()
            player = data.get('player')
            floor = data.get('floor')
            note = data.get('note', '')
            reqs = data.get('reqs', {})
            max_size = data.get('max_size', 5)

            from services.api import get_uuid
            uuid = await get_uuid(player)
            if not uuid:
                return web.json_response({'error': 'Player not found'}, status=404)

            from services.party_manager import party_manager
            party = party_manager.add_party(player, uuid, floor, note, reqs, max_size)
            log_info(f"[API] Party created by {player} for {floor}")
            return web.json_response({'status': 'success', 'party': party})
        except Exception as e:
            log_error(f"[API] Error in party create: {e}")
            return web.json_response({'error': str(e)}, status=500)

    async def handle_party_unqueue(self, request):
        try:
            data = await request.json()
            player = data.get('player')

            from services.api import get_uuid
            uuid = await get_uuid(player)
            if not uuid:
                return web.json_response({'error': 'Player not found'}, status=404)

            from services.party_manager import party_manager
            success = party_manager.remove_party(uuid)
            return web.json_response({'status': 'success', 'removed': success})
        except Exception as e:
            log_error(f"[API] Error in party unqueue: {e}")
            return web.json_response({'error': str(e)}, status=500)

    async def handle_party_update(self, request):
        try:
            data = await request.json()
            player = data.get('player')
            member_count = data.get('member_count')

            from services.api import get_uuid
            uuid = await get_uuid(player)
            if not uuid:
                return web.json_response({'error': 'Player not found'}, status=404)

            from services.party_manager import party_manager
            success = party_manager.update_party(uuid, member_count)
            return web.json_response({'status': 'success', 'updated': success})
        except Exception as e:
            log_error(f"[API] Error in party update: {e}")
            return web.json_response({'error': str(e)}, status=500)

    async def handle_names(self, request):
        from services.name_manager import name_manager
        return web.json_response({
            'status': 'success',
            'names': name_manager.get_names()
        })

    async def handle_irc(self, request):
        from services.irc_handler import get_irc_handler
        handler = get_irc_handler()
        if not handler:
            return web.json_response({'error': 'IRC Handler not initialized'}, status=503)
        return await handler.handle_websocket(request)

    async def handle_auth_verify(self, request):
        try:
            data = await request.json()
            ign = str(data.get('ign', ''))
            server_id = str(data.get('server_id', ''))
            expected_uuid = data.get('uuid') or None

            if not ign or not server_id:
                return web.json_response({'error': 'Missing ign or server_id'}, status=400)

            from services.mojang_auth import verify_session
            ok = await verify_session(ign, server_id, expected_uuid=expected_uuid)
            log_info(f"[API] /v1/auth/verify for {ign}: {ok}")
            return web.json_response({'ok': ok})
        except Exception as e:
            log_error(f"[API] Error in /v1/auth/verify: {e}")
            return web.json_response({'error': str(e)}, status=500)

    async def handle_solo_clear(self, request):
        try:
            ip = get_client_ip(request)
            if ip != "127.0.0.1":
                allowed, retry_after = solo_clear_limiter.check(ip)
                if not allowed:
                    log_error(f"[API] solo_clear rate limit exceeded for IP: {ip} (retry in {retry_after}s)")
                    return web.json_response(
                        {
                            "error": "Too Many Requests",
                            "message": f"You can only submit 1 solo clear per minute. Try again in {retry_after} seconds.",
                            "retry_after": retry_after,
                        },
                        status=429,
                        headers={"Retry-After": str(retry_after)},
                    )

            data = await request.json()
            from services.solo_evidence import SoloClearEvidence, validate as validate_evidence
            evidence = SoloClearEvidence.from_request(data)

            player = evidence.player
            floor = evidence.floor
            time_str = evidence.time
            secrets = evidence.secrets
            puzzles = evidence.puzzles
            prince = evidence.prince
            mimic = evidence.mimic

            if not player or not floor or not time_str:
                return web.json_response({'error': 'Missing required fields (player, floor, time)'}, status=400)

            is_mojang_verified = False
            if evidence.mojang_server_id:
                from services.mojang_auth import verify_session
                is_mojang_verified = await verify_session(
                    player, evidence.mojang_server_id, expected_uuid=evidence.uuid or None
                )
                if not is_mojang_verified:
                    log_error(f"[API] Mojang session verification failed for {player}")

            from services.api import get_uuid
            uuid = await get_uuid(player)
            if not uuid:
                return web.json_response({'error': 'Player not found'}, status=404)

            if ip != "127.0.0.1":
                allowed, retry_after = solo_clear_uuid_limiter.check(str(uuid))
                if not allowed:
                    log_error(f"[API] solo_clear rate limit exceeded for UUID: {uuid} ({player}, retry in {retry_after}s)")
                    return web.json_response(
                        {
                            "error": "Too Many Requests",
                            "message": f"You can only submit 1 solo clear per minute per account. Try again in {retry_after} seconds.",
                            "retry_after": retry_after,
                        },
                        status=429,
                        headers={"Retry-After": str(retry_after)},
                    )

            dev_key = request.headers.get('X-Developer-Key', '')
            encrypted_id = request.headers.get('X-Encrypted-Identity', '')

            from services.security import check_developer_key, verify_identity
            is_dev = check_developer_key(dev_key)
            is_verified_owner = verify_identity(encrypted_id, str(uuid))

            full_auth = is_mojang_verified and is_verified_owner
            modern_client, missing_fields = evidence.is_modern_client()

            auto_verify = is_dev or (full_auth and modern_client)
            if is_dev:
                auth_reason = "developer_key"
                auth_method = "developer_key"
            elif full_auth and modern_client:
                auth_reason = "full_auth_modern_client"
                auth_method = "mojang_identity"
            elif full_auth:
                auth_reason = "missing_modern_evidence"
                auth_method = "mojang_identity"
            elif is_verified_owner:
                auth_reason = "missing_or_invalid_mojang_session"
                auth_method = "encrypted_identity"
            elif is_mojang_verified:
                auth_reason = "invalid_encrypted_identity"
                auth_method = "mojang_session"
            else:
                auth_reason = "no_valid_auth"
                auth_method = "none"
            request["auth_details"] = {
                "result": "auto_verified" if auto_verify else "manual_review",
                "reason": auth_reason,
                "method": auth_method,
                "developer_key": is_dev,
                "encrypted_identity": is_verified_owner,
                "mojang_session": is_mojang_verified,
                "modern_client": modern_client,
            }

            if not auto_verify:
                reasons = []
                if not is_mojang_verified:
                    reasons.append("no Mojang session")
                if not is_verified_owner:
                    reasons.append("no encrypted identity")
                if not modern_client:
                    reasons.append(f"missing evidence: {missing_fields}")
                log_info(f"[API] Solo clear from {player}: not auto-verified ({'; '.join(reasons)}) — saving as unverified for admin review")

            from modules.solo_clears import parse_time
            time_ms = parse_time(time_str)
            if time_ms <= 0:
                return web.json_response({'error': 'Invalid time format'}, status=400)

            if evidence.has_extended_evidence():
                vresult = validate_evidence(evidence, time_ms)
                if vresult.failures:
                    log_error(f"[API] Evidence validation failures for {player}: {vresult.failures}")
                if vresult.warnings:
                    log_info(f"[API] Evidence validation warnings for {player}: {vresult.warnings}")
                if vresult.is_outlier:
                    log_info(f"[API] Submission flagged as outlier for {player} (still auto-verified during warn-only rollout)")

            proof = "Auto-submitted via BlackAddons Mod API"
            discord_id = self.bot.daily_manager.get_user_id_by_ign(player) or uuid

            score_total = evidence.score_components.total if evidence.score_components else 0

            if is_mojang_verified:
                verify_method = "mojang"
            elif is_verified_owner:
                verify_method = "verified_identity"
            elif is_dev:
                verify_method = "dev_key"
            else:
                verify_method = "none"

            verification_meta = {
                "method": verify_method,
                "mojang_verified": is_mojang_verified,
                "is_dev_key": is_dev,
                "is_verified_owner": is_verified_owner,
                "modern_client": modern_client,
                "missing_evidence_fields": missing_fields,
                "verified_at": int(_time.time()),
            }

            evidence_meta = {
                "scoreboard_lines": evidence.scoreboard_lines,
                "tablist_lines": evidence.tablist_lines,
                "score_components": evidence.score_components.to_dict() if evidence.score_components else None,
                "dungeon_enter_tick": evidence.dungeon_enter_tick,
                "clear_trigger_tick": evidence.clear_trigger_tick,
                "client_clock_enter": evidence.client_clock_enter,
                "client_clock_clear": evidence.client_clock_clear,
                "mojang_server_id": evidence.mojang_server_id,
                "map_data": evidence.map_data,
                "needs_verification": evidence.needs_verification,
            }

            success, msg = await self.bot.solo_manager.submit_run(
                floor, player, uuid, time_ms, proof, discord_id,
                secrets=secrets, puzzles=puzzles, prince=prince, mimic=mimic,
                score=score_total, deaths=evidence.deaths, crypts=evidence.crypts,
                auto_verify=auto_verify,
                evidence=evidence_meta, verification=verification_meta,
            )

            if not success:
                return web.json_response({'error': msg}, status=400)
            
            import discord
            try:
                from core.secrets import SOLO_CLEAR_CHANNEL_ID
            except ImportError:
                SOLO_CLEAR_CHANNEL_ID = None

            if SOLO_CLEAR_CHANNEL_ID:
                solo_ch = self.bot.get_channel(SOLO_CLEAR_CHANNEL_ID)
                if solo_ch:
                    if auto_verify:
                        title = "New Auto-Verified API Solo Clear"
                        color = 0x00ff00
                    else:
                        title = "Unverified API Solo Clear"
                        color = 0xffa500

                    embed = discord.Embed(title=title, color=color)
                    embed.add_field(name="Player", value=f"`{player}`", inline=True)
                    embed.add_field(name="Floor", value=floor, inline=True)
                    embed.add_field(name="Time", value=time_str, inline=True)
                    embed.add_field(name="Stats", value=f"Secrets: {secrets}\nPuzzles: {len(puzzles)}\nPrince: {'✅' if prince else '❌'}\nMimic: {'✅' if mimic else '❌'}", inline=False)
                    embed.add_field(name="Proof", value=proof, inline=False)

                    map_file = None
                    if evidence.map_data:
                        try:
                            from services.map_renderer import render_map
                            import io as _io
                            png = render_map(evidence.map_data)
                            if png:
                                map_file = discord.File(_io.BytesIO(png), filename="minimap.png")
                                embed.set_image(url="attachment://minimap.png")
                        except Exception as map_err:
                            log_error(f"[API] map render failed: {map_err}")

                    view = None
                    if not auto_verify:
                        from modules.solo_clears import VerifyView
                        view = VerifyView(self.bot, floor, str(uuid))

                    send_kwargs = {"embed": embed}
                    if map_file is not None:
                        send_kwargs["file"] = map_file
                    if view is not None:
                        send_kwargs["view"] = view
                    await solo_ch.send(**send_kwargs)

            return web.json_response({'status': 'success', 'message': msg})
        except Exception as e:
            log_error(f"[API] Error processing POST /v1/solo_clear: {e}")
            return web.json_response({'error': str(e)}, status=500)

    async def handle_solo_leaderboard(self, request):
        try:
            floor = request.rel_url.query.get('floor', 'F7').upper()
            runs = self.bot.solo_manager.get_leaderboard(floor, 'verified')
            from modules.solo_clears import format_time
            result = []
            for i, run in enumerate(runs[:25]):
                result.append({
                    'rank': i + 1,
                    'ign': run.get('ign', 'Unknown'),
                    'time_ms': run.get('time_ms', 0),
                    'time_str': format_time(run.get('time_ms', 0)),
                    'secrets': run.get('secrets', 0),
                    'puzzles': run.get('puzzles', []),
                    'prince': run.get('prince', False),
                    'mimic': run.get('mimic', False),
                    'date_achieved': run.get('date_achieved', 0),
                })
            return web.json_response({'floor': floor, 'runs': result})
        except Exception as e:
            log_error(f"[API] Error processing GET /v1/solo_leaderboard: {e}")
            return web.json_response({'error': str(e)}, status=500)

async def setup(bot):
    await bot.add_cog(API(bot))
