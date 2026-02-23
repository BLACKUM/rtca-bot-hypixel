import json
import os
from typing import List, Dict, Any

CONFIG_FILE = "data/config.json"

class BotConfig:
    def __init__(self, file_path=CONFIG_FILE, load_from_file=True):
        self.file_path = file_path
        self.xp_per_run_default: float = 300000.0
        self.target_level: int = 50
        self.debug_mode: bool = True
        self.profile_cache_ttl: int = 60
        self.prices_cache_ttl: int = 259200
        self.irc_channel_id: int = 0
        self.primary_api: str = "soopy"
        self.owner_ids: List[int] = [377351386637271041, 679725029109399574]
        self.congrats_gifs: List[str] = [
            "https://c.tenor.com/n5-r2F_JeGMAAAAd/tenor.gif",
            "https://c.tenor.com/xAW8c7Z8-3cAAAAd/tenor.gif",
            "https://c.tenor.com/4YDfECEyEtwAAAAd/tenor.gif",
            "https://c.tenor.com/8Zvt_ouixT8AAAAd/tenor.gif",
            "https://c.tenor.com/I5LkHI4yrRcAAAAd/tenor.gif",
            "https://c.tenor.com/JDUuuveDLeQAAAAd/tenor.gif",
            "https://c.tenor.com/Xqc4YXfCySEAAAAd/tenor.gif",
            "https://c.tenor.com/UgvKJP8OIHoAAAAd/tenor.gif",
            "https://c.tenor.com/O57p6KOsleoAAAAd/tenor.gif",
            "https://c.tenor.com/gdBh7nScJMYAAAAd/tenor.gif",
            "https://c.tenor.com/mamnZXgZxqIAAAAd/tenor.gif",
            "https://c.tenor.com/lfbOYamuNSoAAAAd/tenor.gif",
            "https://c.tenor.com/8WpxdEqUcWEAAAAd/tenor.gif",
            "https://c.tenor.com/jI79BCqsw68AAAAd/tenor.gif",
            "https://c.tenor.com/XgzhRq264JcAAAAd/tenor.gif",
            "https://c.tenor.com/VngFH2yD0RAAAAAC/tenor.gif",
            "https://c.tenor.com/JEFazVKAde0AAAAd/tenor.gif",
            "https://c.tenor.com/GEAz2m-SWAsAAAAd/tenor.gif",
            "https://c.tenor.com/LcsbStHRMCMAAAAC/tenor.gif",
            "https://c.tenor.com/Dgmg1Dzjq-oAAAAd/tenor.gif",
            "https://media.tenor.com/UlNu8AJREWwAAAAM/kermit-the-frog-go-the-fuck-outside-punk.gif",
            "https://i.imgflip.com/8axaft.gif",
            "https://media.tenor.com/0lsV1eolzSMAAAAM/shower-soap.gif",
            "https://media.tenor.com/jcG6b0cZgQEAAAAM/homer-bath.gif",
            "https://media.tenor.com/XX7CWmfJ8ZIAAAAM/shower-dogs.gif",
            "https://img1.picmix.com/output/pic/normal/2/8/0/6/11396082_40409.gif",
            "https://media.tenor.com/MMo4B6tp-GMAAAAM/job-application.gif",
            "https://media.tenor.com/Rs-PNa8EBFcAAAAM/job-jumpscare-job-application.gif",
            "https://media.tenor.com/JkMtMAjXHS8AAAAM/job-job-application.gif",
            "https://c.tenor.com/xyMEZ2xCttcAAAAC/tenor.gif",
            "https://media.tenor.com/Kp0_YKtqqXIAAAAe/job-application.png",
            "https://media.tenor.com/Gk2yr271HUsAAAAe/job-application.png",
            "https://media.tenor.com/UsDCL6bOIT4AAAAM/touch-grass-touch.gif",
            "https://i.imgflip.com/6f5788.gif",
            "https://media2.giphy.com/media/v1.Y2lkPTZjMDliOTUyODIyMXFzamljbm9sc2d1NnVzdDJvYXllN2Jjcm14Y25kYm00cGF5ZSZlcD12MV9naWZzX3NlYXJjaCZjdD1n/bum2UBz4nR9IxZmWde/giphy-downsized.gif",
            "https://media3.giphy.com/media/v1.Y2lkPTZjMDliOTUyODVzb2JyeXpveng0Z2FocHdsczF6enZqbDN6NDBiZmhuaWlndXl1NiZlcD12MV9naWZzX3NlYXJjaCZjdD1n/JyOtBwVBKFoeIQ14Po/200w_d.gif",
            "https://media.discordapp.net/attachments/1122856048374595647/1152961363614908497/JIXMersMo8xcnmXQ.gif?ex=69591b72&is=6957c9f2&hm=40759ab651245f54ba2e5f10640403b43806c1cfe5cbf542ec4be9d2a4607437&=&width=585&height=75",
            "https://media.discordapp.net/attachments/1263938847910269000/1276128862849339393/minus-infinite-social-credit-china.gif?ex=6958f21e&is=6957a09e&hm=34acdfe4c04a23c4d4e4256f908b7523d41670e382018038544bfc3aeb2823ff&=&width=800&height=450",
            "https://media.discordapp.net/attachments/1263938847910269000/1276125652730380349/gypsycrusadervshoke.gif?ex=6958ef20&is=69579da0&hm=545b63f83cb383740758971ca6940b9f9b22d1bd9d832ed09089d9246c15ffc0&=&width=800&height=503",
            "https://media.discordapp.net/attachments/1263938847910269000/1276130366847057950/redditsave.com_y2dkx7x76f481.gif?ex=6958f384&is=6957a204&hm=da6abb1ff3db36d77abaf35e8103173e849eb85297686fb2edcb1f1dec3cb57f&=&width=800&height=800",
            "https://media.discordapp.net/attachments/1236050415020277840/1267879801566269481/caption.gif?ex=69594214&is=6957f094&hm=2581bd92a3109cad09926351f8b69d6bc279a5003b64536ddb50684697b5eb5d&=&width=750&height=934",
            "https://media.discordapp.net/attachments/993269478060195950/1118188097222488104/ED6EFBC5-A68E-48C6-9103-B123B1ECC22D.gif?ex=69592a51&is=6957d8d1&hm=9b2954746a2d198cd8442724df3d8ccb09134436db77a0cdfdbc5b13cf79876e&=&width=254&height=60",
            "https://cdn.discordapp.com/attachments/982414624844554241/1185533720233508894/tM1qwcbNS15DWrFk.gif?ex=6958f3d1&is=6957a251&hm=9708f3e09cc4e9d50d986acaf7086d2177ba9e1c4bc09a6b96214851f9a9c28a",
            "https://media.discordapp.net/attachments/1255211359227084821/1269003922413060176/caption.gif?ex=6958bbc0&is=69576a40&hm=aec2497118642f46043347f8f462cc2f4e9fdd19d60cd0882d414949b84efcd8&=&width=294&height=375",
            "https://media.discordapp.net/attachments/773213826186739775/979470724098039878/puzzlehater.gif.gif?ex=6958c972&is=695777f2&hm=f9d81391304ff5749a3deeea31c77a76627bb1b7c14c872e148fe28afd26344a&=&width=168&height=168",
            "https://media.discordapp.net/attachments/1347938901825814592/1400962571082924132/MedalTVMinecraft20250731185114-1753971386_1.gif?ex=6958e9d1&is=69579851&hm=dcaf2ed25e77aca670c8f26e47e332c73c3d202af44bb5f5140369b7eda85757&=&width=865&height=485",
            "https://media.discordapp.net/attachments/1275995649988628574/1300897696269209681/wdhu.gif?ex=6958bf24&is=69576da4&hm=dc133d83ca5895f9975fee6ce031e2ad7bd4aad3cd84006b75de18ae3093abc7&=&width=658&height=849",
            "https://media.discordapp.net/attachments/1172235640117669921/1402064324805132479/a276ic.gif?ex=6958f768&is=6957a5e8&hm=01f61333a5246f22918ca0791a5ea7950a9470ce5d55f8e55491c423eab243ec&=&width=450&height=236",
            "https://media.discordapp.net/attachments/1397725617239363625/1403384070540365914/meowmeow.gif?ex=69592744&is=6957d5c4&hm=39de6c27bf9cca6fd7e61e2b61e8d232ce4bf1979e960d483204ba27e93b4605&=&width=445&height=445",
            "https://media.discordapp.net/attachments/1379474866725453988/1420884081176084551/togif.gif?ex=6958e0ab&is=69578f2b&hm=11c34bd40104687de43199b1e43539f6f8fa59083525b3736cf39d1f8d66fc70&=&width=1545&height=875",
            "https://media.discordapp.net/attachments/1160332174344597554/1228784996169552055/thirty11.gif?ex=695a12f4&is=6958c174&hm=3a08d3b7af929b028f99fe4eb0916043c3e1dc22425ca48940654ae46fe6febc&=&width=288&height=199",
            "https://media.discordapp.net/attachments/1423627182697086996/1424142662197317724/attachment.gif?ex=695a2f75&is=6958ddf5&hm=59a83af7929562b7a7cd568d4c21b00b58e260c703d787384661cf5683150c63&=&width=960&height=1075",
            "https://media.discordapp.net/attachments/1420147559011192924/1447572753149591592/togif.gif?ex=6959122e&is=6957c0ae&hm=b55333c72e8ef1c3e5b9cc6247a0b414412b0d1e6e49973edb9dd3919d74b401&=&width=1024&height=796"
        ]
        
        if load_from_file:
            self.load()

    def load(self):
        from core.logger import log_error, log_info
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r') as f:
                    data = json.load(f)
                    self._update_from_dict(data)
            except Exception as e:
                log_error(f"Failed to load config: {e}")
        else:
            log_info("Config file not found, using defaults.")
            self.save()

    def save(self):
        from core.logger import log_error
        data = {
            "xp_per_run_default": self.xp_per_run_default,
            "target_level": self.target_level,
            "debug_mode": self.debug_mode,
            "profile_cache_ttl": self.profile_cache_ttl,
            "prices_cache_ttl": self.prices_cache_ttl,
            "irc_channel_id": self.irc_channel_id,
            "primary_api": self.primary_api,
            "owner_ids": self.owner_ids,
            "congrats_gifs": self.congrats_gifs
        }
        try:
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            temp_path = self.file_path + ".tmp"
            with open(temp_path, 'w') as f:
                json.dump(data, f, indent=4)
            os.replace(temp_path, self.file_path)
        except Exception as e:
            log_error(f"Failed to save config: {e}")

    def _update_from_dict(self, data: Dict[str, Any]):
        self.xp_per_run_default = data.get("xp_per_run_default", self.xp_per_run_default)
        self.target_level = data.get("target_level", self.target_level)
        self.debug_mode = data.get("debug_mode", self.debug_mode)
        self.profile_cache_ttl = data.get("profile_cache_ttl", self.profile_cache_ttl)
        self.prices_cache_ttl = data.get("prices_cache_ttl", self.prices_cache_ttl)
        self.irc_channel_id = data.get("irc_channel_id", self.irc_channel_id)
        self.primary_api = data.get("primary_api", self.primary_api)
        if "owner_ids" in data:
            self.owner_ids = data["owner_ids"]
        if "congrats_gifs" in data:
            self.congrats_gifs = data["congrats_gifs"]
