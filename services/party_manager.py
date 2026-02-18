import time
import uuid

class PartyManager:
    def __init__(self):
        self.parties = {}
        self.cleanup_interval = 600

    def add_party(self, player_name, player_uuid, floor, note, reqs, max_size=5):
        self.cleanup()
        party_id = str(uuid.uuid4())
        self.parties[player_uuid] = {
            "id": party_id,
            "leader_name": player_name,
            "leader_uuid": player_uuid,
            "floor": floor,
            "note": note,
            "reqs": reqs,
            "max_size": max_size,
            "member_count": 1,
            "timestamp": time.time()
        }
        return self.parties[player_uuid]

    def remove_party(self, player_uuid):
        if player_uuid in self.parties:
            del self.parties[player_uuid]
            return True
        return False

    def update_party(self, player_uuid, member_count=None):
        if player_uuid in self.parties:
            if member_count is not None:
                self.parties[player_uuid]["member_count"] = member_count
            self.parties[player_uuid]["timestamp"] = time.time()
            return True
        return False

    def get_parties(self, floor=None):
        self.cleanup()
        
        all_parties = list(self.parties.values())
        
        floor_order = ["M7", "M6", "M5", "M4", "M3", "M2", "M1", 
                       "F7", "F6", "F5", "F4", "F3", "F2", "F1", "Entrance"]
        
        def get_sort_key(p):
            f = p["floor"].upper()
            try:
                return floor_order.index(f)
            except ValueError:
                return 99

        if floor and floor.upper() != "ALL":
            filtered = [p for p in all_parties if p["floor"].upper() == floor.upper()]
            return sorted(filtered, key=get_sort_key)
            
        return sorted(all_parties, key=get_sort_key)

    def cleanup(self):
        now = time.time()
        expired = [uid for uid, p in self.parties.items() if now - p["timestamp"] > self.cleanup_interval]
        for uid in expired:
            del self.parties[uid]

party_manager = PartyManager()
