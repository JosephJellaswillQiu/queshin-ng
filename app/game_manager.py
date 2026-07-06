from typing import List, Dict, Optional, Set
import random
from utils.riichi.yaku_han import yaku_han
from utils.pair_split import common_pair_split, seven_pair_split
from utils.furo import (
    get_possible_furo, get_ankan_combinations, get_kakan_combinations,
    get_kita_combinations
)

# 风牌对应关系
WIND_TILES = ["1z", "2z", "3z", "4z"]  # 东南西北
WIND_NAMES = ["东", "南", "西", "北"]
SEAT_LABELS = ["东", "南", "西", "北"]

class MajRoom:
    def __init__(self, room_id: int, room_name: str):
        self.room_id = room_id
        self.room_name = room_name
        self.players: List[str] = []          # 玩家 sid，[0]=东(庄), [1]=南, [2]=西, [3]=北
        self.player_ids: List[int] = []       # 玩家 user_id
        self.hands: Dict[str, List[str]] = {} # sid → 手牌
        self.player_rivers: Dict[str, List[str]] = {}  # sid → 牌河（每人自己的弃牌）
        self.player_furo: Dict[str, List[List[str]]] = {}  # sid → 副露列表
        self.wall: List[str] = []             # 牌山
        self.dead_wall: List[str] = []        # 王牌（14张）
        self.dora_indicators: List[str] = []  # 已翻开的宝牌指示牌

        # 回合状态
        self.dealer_idx: int = 0              # 庄家在 players 中的索引
        self.current_turn_idx: int = 0        # 当前出牌玩家在 players 中的索引
        self.is_playing: bool = False
        self.riichi_declared: Set[str] = set() # 已立直的玩家 sid
        self.riichi_sticks: int = 0           # 供托（立直棒）

        # 游戏设置
        self.settings = {
            "phase_wind": "1z",           # 场风
            "phase_wind_num": 27,         # 场风数字
            "round_number": 0,            # 0=东1, 1=东2, ... 3=东4, 4=南1...
            "honba": 0,                   # 本场棒
            "dora": ["1m"],               # 宝牌列表（字符串）
            "ura_dora": ["2m"],           # 里宝牌
            "riichi": 0,                   # 立直状态（按玩家设置）
            "ippatus": False,
            "after_a_kan": False,
            "robbing_a_kan": False,
            "under_the_sea": False,
            "under_the_river": False,
            "ron": True,
        }

    # ── 座位/风位 ──────────────────────────────────────────

    def get_seat_index(self, sid: str) -> int:
        """获取玩家座位索引 (0-3)"""
        try:
            return self.players.index(sid)
        except ValueError:
            return -1

    def get_player_wind(self, sid: str) -> str:
        """根据座位和庄家位置计算玩家自风"""
        seat_idx = self.get_seat_index(sid)
        if seat_idx < 0:
            return "1z"
        relative = (seat_idx - self.dealer_idx) % 4
        return WIND_TILES[relative]

    def get_seat_label(self, sid: str) -> str:
        seat_idx = self.get_seat_index(sid)
        return SEAT_LABELS[seat_idx] if seat_idx >= 0 else "?"

    # ── 玩家管理 ──────────────────────────────────────────

    def add_player(self, sid: str, user_id: int) -> bool:
        if len(self.players) < 4:
            self.players.append(sid)
            self.player_ids.append(user_id)
            self.player_rivers[sid] = []
            self.player_furo[sid] = []
            return True
        return False

    def remove_player(self, sid: str):
        if sid in self.players:
            idx = self.players.index(sid)
            self.players.pop(idx)
            self.player_ids.pop(idx)
            self.hands.pop(sid, None)
            self.player_rivers.pop(sid, None)
            self.player_furo.pop(sid, None)
            self.riichi_declared.discard(sid)

    # ── 牌山/游戏初始化 ────────────────────────────────────

    @staticmethod
    def _generate_full_wall() -> List[str]:
        """生成一副完整的136张麻将牌"""
        suits = ['m', 'p', 's']
        honors = ['1z', '2z', '3z', '4z', '5z', '6z', '7z']
        wall = []
        for _ in range(4):
            for s in suits:
                for n in range(1, 10):
                    wall.append(f"{n}{s}")
            for h in honors:
                wall.append(h)
        random.shuffle(wall)
        return wall

    def init_game(self):
        """初始化一局游戏"""
        self.is_playing = True
        self.dealer_idx = 0
        self.current_turn_idx = 0
        self.riichi_declared.clear()
        self.riichi_sticks = 0
        self.player_rivers = {sid: [] for sid in self.players}
        self.player_furo = {sid: [] for sid in self.players}
        self.dora_indicators = []

        # 生成牌山
        full_wall = self._generate_full_wall()
        # 最后14张作为王牌
        self.dead_wall = full_wall[-14:]
        self.wall = full_wall[:-14]

        # 翻开第一张宝牌指示牌（王牌倒数第5张）
        self.dora_indicators.append(self.dead_wall[-5])
        dora_tile = self._next_dora(self.dead_wall[-5])
        self.settings["dora"] = [dora_tile]
        self.settings["ura_dora"] = [dora_tile]  # 里宝牌暂时相同，立直后单独计算

        # 发牌：每人13张
        for p in self.players:
            self.hands[p] = [self.wall.pop() for _ in range(13)]
            self.hands[p].sort()

        # 庄家摸第14张
        dealer_sid = self.players[self.dealer_idx]
        self.hands[dealer_sid].append(self.wall.pop())
        self.hands[dealer_sid].sort()

    @staticmethod
    def _next_dora(indicator: str) -> str:
        """根据指示牌计算宝牌"""
        suit = indicator[1]
        num = int(indicator[0])
        if suit == 'z':
            # 字牌：1z→2z, 2z→3z, 3z→4z, 4z→1z, 5z→6z, 6z→7z, 7z→5z
            mapping = {'1': '2', '2': '3', '3': '4', '4': '1',
                       '5': '6', '6': '7', '7': '5'}
            return mapping[str(num)] + 'z'
        else:
            # 数牌：1→2, 2→3, ... 9→1
            return str(num % 9 + 1) + suit

    def flip_new_dora(self):
        """杠之后翻新的宝牌指示牌"""
        # 王牌从右往左翻：-5, -7, -9, -11, -3（每次杠翻一张）
        dora_order = [-5, -7, -9, -11, -3]
        idx = len(self.dora_indicators)
        if idx < len(dora_order):
            indicator = self.dead_wall[dora_order[idx]]
            self.dora_indicators.append(indicator)
            dora_tile = self._next_dora(indicator)
            self.settings["dora"].append(dora_tile)

    def draw_tile(self, sid: str) -> Optional[str]:
        """从牌山摸牌"""
        if not self.wall:
            return None
        tile = self.wall.pop()
        self.hands[sid].append(tile)
        return tile

    def draw_kan_tile(self, sid: str) -> Optional[str]:
        """杠之后从岭上摸牌"""
        if not self.dead_wall:
            return None
        tile = self.dead_wall.pop(0)  # 从王牌头部取
        self.hands[sid].append(tile)
        return tile

    # ── 出牌/弃牌 ──────────────────────────────────────────

    def discard_tile(self, sid: str, tile: str) -> bool:
        """玩家出牌，返回是否成功"""
        if sid not in self.hands or tile not in self.hands[sid]:
            return False
        self.hands[sid].remove(tile)
        self.player_rivers[sid].append(tile)
        # 出牌后重置一发标记
        if sid in self.riichi_declared:
            self.settings["ippatus"] = False
        return True

    # ── 副露 ────────────────────────────────────────────────

    def get_furo_options(self, sid: str, tile: str, allow_chi: bool = True):
        """获取玩家对某张牌的副露选项"""
        hand = self.hands.get(sid, [])
        furo = self.player_furo.get(sid, [])
        # 转换为数字编码
        from utils.riichi.yaku_han import convert_hand_to_num
        hand_num = convert_hand_to_num(hand)
        furo_num = [convert_hand_to_num(m) for m in furo]
        from utils.riichi.yaku_han import convert_tile_to_num
        tile_num = convert_tile_to_num(tile)
        return get_possible_furo(hand_num, furo_num, tile_num, allow_chi)

    def add_furo_to_player(self, sid: str, new_hand, new_furo):
        """应用副露结果到玩家"""
        from utils.riichi.yaku_han import convert_tile_to_num
        # 将数字编码转回字符串（简化：直接替换手牌和副露）
        # 实际项目需维护数字-字符串映射，这里保持字符串操作
        pass

    # ── 立直 ────────────────────────────────────────────────

    def can_riichi(self, sid: str) -> bool:
        """检查是否可以立直：门前清、手牌14张"""
        if sid in self.riichi_declared:
            return False
        if self.player_furo.get(sid, []):
            return False  # 有副露不能立直
        hand = self.hands.get(sid, [])
        return len(hand) == 14  # 摸牌后未出牌时14张

    def declare_riichi(self, sid: str):
        """声明立直"""
        self.riichi_declared.add(sid)
        self.riichi_sticks += 1
        self.settings["ippatus"] = True  # 立直后下一巡为一发

    # ── 和牌判定 ────────────────────────────────────────────

    def check_win(self, sid: str, win_tile: str, is_tsumo: bool = False):
        """检查玩家是否可以和牌，返回和牌结果或 False"""
        hand = self.hands.get(sid, [])
        if sid not in self.player_furo:
            return False
        furo = self.player_furo[sid]

        # 构建针对该玩家的 settings
        player_settings = self.settings.copy()
        player_settings["player_wind"] = self.get_player_wind(sid)
        player_settings["riichi"] = 1 if sid in self.riichi_declared else 0
        player_settings["ron"] = not is_tsumo

        result = yaku_han(hand, furo, win_tile, player_settings)
        return result

    # ── 振听判定 ────────────────────────────────────────────

    def is_furiten(self, sid: str, win_tile: str) -> bool:
        """
        检查玩家对 win_tile 是否振听。
        振听：自己牌河中包含能和牌的牌 → 不能荣和，只能自摸。
        """
        hand = self.hands.get(sid, [])
        furo = self.player_furo.get(sid, [])
        river = self.player_rivers.get(sid, [])

        # 检查自己打过的每一张牌，如果它能组成和牌形 → 振听
        for discarded in set(river):
            # 用弃牌替换和牌尝试
            test_hand = hand.copy()
            if win_tile in test_hand:
                # 用弃牌替换 win_tile，检查是否依然能和
                pass  # 需要更精确的判定
            # 简化：check_win 用 discarded 作为和牌
            player_settings = self.settings.copy()
            player_settings["player_wind"] = self.get_player_wind(sid)
            player_settings["riichi"] = 1 if sid in self.riichi_declared else 0
            player_settings["ron"] = True
            if yaku_han(hand, furo, discarded, player_settings):
                return True
        return False

    # ── 听牌判定 ────────────────────────────────────────────

    def is_tenpai(self, sid: str) -> bool:
        """检查玩家是否听牌（差一张就能和）"""
        hand = self.hands.get(sid, [])
        furo = self.player_furo.get(sid, [])
        from utils.riichi.yaku_han import convert_hand_to_num, convert_tile_to_num

        # 遍历所有可能的牌，检查是否能和
        all_tiles = set()
        for s in ['m', 'p', 's']:
            for n in range(1, 10):
                all_tiles.add(f"{n}{s}")
        for n in range(1, 8):
            all_tiles.add(f"{n}z")

        player_settings = self.settings.copy()
        player_settings["player_wind"] = self.get_player_wind(sid)
        player_settings["riichi"] = 1 if sid in self.riichi_declared else 0
        player_settings["ron"] = True

        for tile in all_tiles:
            if yaku_han(hand, furo, tile, player_settings):
                return True
        return False

    # ── 局流转 ──────────────────────────────────────────────

    def next_round(self, dealer_stays: bool = False):
        """
        进入下一局。
        dealer_stays: True=庄家连庄, False=轮庄
        """
        if not dealer_stays:
            self.dealer_idx = (self.dealer_idx + 1) % 4
            self.settings["honba"] = 0
        else:
            self.settings["honba"] += 1

        # 推进局数
        self.settings["round_number"] += 1
        # 更新场风
        phase_winds = ["1z", "1z", "1z", "1z",  # 东1-4
                       "2z", "2z", "2z", "2z",  # 南1-4
                       "3z", "3z", "3z", "3z"]  # 西1-4
        rn = self.settings["round_number"]
        if rn < len(phase_winds):
            self.settings["phase_wind"] = phase_winds[rn]
            from utils.riichi.yaku_han import convert_tile_to_num
            self.settings["phase_wind_num"] = convert_tile_to_num(phase_winds[rn])

    def is_game_over(self) -> bool:
        """检查整场游戏是否结束（南四局结束或有人飞了）"""
        return self.settings["round_number"] >= 8  # 南四局 = 7


class RoomManager:
    def __init__(self):
        self.rooms: Dict[str, MajRoom] = {}

    def create_room(self, room_id: int, room_name: str) -> Optional[MajRoom]:
        if room_name not in self.rooms:
            self.rooms[room_name] = MajRoom(room_id, room_name)
            return self.rooms[room_name]
        return None

    def get_room(self, room_name: str) -> Optional[MajRoom]:
        return self.rooms.get(room_name)

    def remove_room(self, room_name: str):
        if room_name in self.rooms:
            del self.rooms[room_name]


room_manager = RoomManager()
