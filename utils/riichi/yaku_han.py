from utils.pair_split import seven_pair_split, common_pair_split, Triplet, Sequence, Quad, Pair


# ── 牌编码工具 ────────────────────────────────────────────

def convert_tile_to_num(tile):
    """牌字符串 → 数字编码。0~8万 9~17饼 18~26索 27~33字"""
    if tile == "-" or tile == "-1":
        return -1
    suit_dict = {'m': 0, 'p': 9, 's': 18, 'z': 27}
    number = int(tile[0])
    suit = tile[1]
    if suit not in suit_dict:
        raise ValueError("Invalid suit: {}".format(suit))
    if suit == 'z' and (number < 1 or number > 7):
        raise ValueError("Invalid honor tile number: {}".format(number))
    if suit != 'z' and (number < 0 or number > 9):
        raise ValueError("Invalid tile number: {}".format(number))
    if suit == 'z' and number >= 5:
        number = 12 - number  # 5z=白,6z=发,7z=中 → 31=中,32=发,33=白
    return suit_dict[suit] + (number - 1 if number != 0 else 4)


def convert_hand_to_num(hand):
    return [convert_tile_to_num(tile) for tile in hand]


def tile_suit(tile_num: int) -> int:
    """返回花色: 0=万, 1=饼, 2=索, 3=字"""
    if tile_num < 0:
        return -1
    if tile_num <= 8:
        return 0
    if tile_num <= 17:
        return 1
    if tile_num <= 26:
        return 2
    return 3


def is_terminal(tile_num: int) -> bool:
    """是否为老头牌（1或9的数牌）"""
    return tile_num >= 0 and tile_num <= 33 and tile_suit(tile_num) < 3 and tile_num % 9 in (0, 8)


def is_honor(tile_num: int) -> bool:
    """是否为字牌"""
    return 27 <= tile_num <= 33


def is_terminal_or_honor(tile_num: int) -> bool:
    """幺九牌"""
    return is_terminal(tile_num) or is_honor(tile_num)


def is_simple(tile_num: int) -> bool:
    """中张牌（2-8数牌）"""
    return not is_terminal_or_honor(tile_num)


# ── 门前清判定 ────────────────────────────────────────────

def is_menzenqing(hand_num, furo_num, hu_num):
    for meld in furo_num:
        if len(meld) == 3 or (-1 not in meld):
            return False
    return True


# ── 役种验证器 ────────────────────────────────────────────

def is_pinfu(pair_split, hu_num, settings):
    if len(pair_split) != 5:
        return False
    has_pair = False
    for meld in pair_split:
        if isinstance(meld, Pair):
            if has_pair:
                return False
            has_pair = True
            if meld[0] == settings["player_wind_num"] or \
               meld[0] == settings["phase_wind_num"] or \
               meld[0] in [31, 32, 33]:
                return False
        elif not isinstance(meld, Sequence):
            return False
    for meld in pair_split:
        if len(meld) == 3:
            if hu_num == meld[0] or hu_num == meld[2]:
                return True
    return False


def is_tanyao(pair_split, hu_num, settings):
    disallow_nums = [0, 8, 9, 17, 18, 26, 27, 28, 29, 30, 31, 32, 33]
    for meld in pair_split:
        for tile in meld:
            if tile in disallow_nums:
                return False
    return True


def is_yakuhai_player_wind(pair_split, hu_num, settings):
    for meld in pair_split:
        if isinstance(meld, Triplet) or isinstance(meld, Quad):
            if meld.num == settings["player_wind_num"]:
                return True
    return False


def is_yakuhai_phase_wind(pair_split, hu_num, settings):
    for meld in pair_split:
        if isinstance(meld, Triplet) or isinstance(meld, Quad):
            if meld.num == settings["phase_wind_num"]:
                return True
    return False


def is_yakuhai_chuu(pair_split, hu_num, settings):
    for meld in pair_split:
        if isinstance(meld, Triplet) or isinstance(meld, Quad):
            if meld.num == 31:
                return True
    return False


def is_yakuhai_hatsu(pair_split, hu_num, settings):
    for meld in pair_split:
        if isinstance(meld, Triplet) or isinstance(meld, Quad):
            if meld.num == 32:
                return True
    return False


def is_yakuhai_shiro(pair_split, hu_num, settings):
    for meld in pair_split:
        if isinstance(meld, Triplet) or isinstance(meld, Quad):
            if meld.num == 33:
                return True
    return False


def is_riichi(pair_split, hu_num, settings):
    return settings.get("riichi", 0) >= 1


def is_double_riichi(pair_split, hu_num, settings):
    return settings.get("riichi", 0) == 2


def is_ippatus(pair_split, hu_num, settings):
    return settings.get("ippatus", False)


def is_menzenchin_tsumohou(pair_split, hu_num, settings):
    return not settings.get("ron", True)


def is_pure_double_sequence(pair_split, hu_num, settings):
    meld_count = []
    for meld in pair_split:
        if isinstance(meld, Sequence):
            key = (meld.num, meld.furo)
            if key in meld_count:
                return True
            meld_count.append(key)
    return False


def is_after_a_kan(pair_split, hu_num, settings):
    return settings.get("after_a_kan", False)


def is_robbing_a_kan(pair_split, hu_num, settings):
    return settings.get("robbing_a_kan", False)


def is_under_the_sea(pair_split, hu_num, settings):
    return settings.get("under_the_sea", False)


def is_under_the_river(pair_split, hu_num, settings):
    return settings.get("under_the_river", False)


def is_all_triplets(pair_split, hu_num, settings):
    for meld in pair_split:
        if isinstance(meld, Sequence):
            return False
    return True


def is_triple_triplets(pair_split, hu_num, settings):
    triplets = {}
    for meld in pair_split:
        if isinstance(meld, Triplet) or isinstance(meld, Quad):
            s = tile_suit(meld.num)
            n = meld.num % 9
            if s < 3:
                triplets[(s, n)] = True
    for n in range(9):
        if (0, n) in triplets and (1, n) in triplets and (2, n) in triplets:
            return True
    return False


def is_three_quads(pair_split, hu_num, settings):
    quad_len = sum(1 for meld in pair_split if isinstance(meld, Quad))
    return quad_len >= 3


# ── 新增役种验证器 ────────────────────────────────────────

def is_honitsu(pair_split, hu_num, settings):
    """混一色：只有一种数牌花色 + 字牌"""
    suits = set()
    for meld in pair_split:
        for tile in meld:
            s = tile_suit(tile)
            if s < 3:
                suits.add(s)
            elif s > 3:
                return False
    return len(suits) == 1 and 3 not in suits


def is_chinitsu(pair_split, hu_num, settings):
    """清一色：全部同一种数牌花色，无字牌"""
    suits = set()
    for meld in pair_split:
        for tile in meld:
            s = tile_suit(tile)
            if s == 3 or s == -1:
                return False
            suits.add(s)
    return len(suits) == 1


def is_ikkitsuukan(pair_split, hu_num, settings):
    """一气通贯：同花色 123+456+789 三组顺子"""
    sequences_by_suit = {0: set(), 1: set(), 2: set()}
    for meld in pair_split:
        if isinstance(meld, Sequence):
            s = tile_suit(meld.num)
            seq_num = meld.num % 9
            sequences_by_suit[s].add(seq_num)
    for s in range(3):
        if 0 in sequences_by_suit[s] and 3 in sequences_by_suit[s] and 6 in sequences_by_suit[s]:
            return True
    return False


def is_sanshoku_doujun(pair_split, hu_num, settings):
    """三色同顺：万/饼/索各有相同数字的顺子"""
    seq_nums = {0: set(), 1: set(), 2: set()}
    for meld in pair_split:
        if isinstance(meld, Sequence):
            s = tile_suit(meld.num)
            n = meld.num % 9
            seq_nums[s].add(n)
    for n in range(7):
        if n in seq_nums[0] and n in seq_nums[1] and n in seq_nums[2]:
            return True
    return False


def is_chiitoitsu(pair_split, hu_num, settings):
    """七对子：7个不同对子（接受 Pair 或 [x,x] 列表）"""
    if len(pair_split) != 7:
        return False
    for meld in pair_split:
        if isinstance(meld, Pair):
            continue
        elif isinstance(meld, list) and len(meld) == 2 and meld[0] == meld[1]:
            continue
        else:
            return False
    return True


def is_honchantaiyaochuu(pair_split, hu_num, settings):
    """混全帯幺九：所有面子+雀头都包含幺九牌"""
    for meld in pair_split:
        contains_terminal_or_honor = any(
            is_terminal_or_honor(tile) for tile in meld
        )
        if not contains_terminal_or_honor:
            return False
    return True


def is_junchan_taiyaochuu(pair_split, hu_num, settings):
    """纯全帯幺九：所有面子+雀头都包含老头牌，且不含字牌"""
    for meld in pair_split:
        contains_terminal = any(is_terminal(tile) for tile in meld)
        if not contains_terminal:
            return False
        has_honor = any(is_honor(tile) for tile in meld)
        if has_honor:
            return False
    return True


def is_sanshoku_doukou(pair_split, hu_num, settings):
    """三色同刻：万/饼/索各有相同数字的刻子（已有 is_triple_triplets，别名）"""
    return is_triple_triplets(pair_split, hu_num, settings)


# ── 役种列表 ──────────────────────────────────────────────

yaku_han_list = {
    # 1翻役
    "yaku.riichi":              {"han": 1, "yakuman": 0, "validator": is_riichi,              "allow_furo": 0},
    "yaku.ippatus":             {"han": 1, "yakuman": 0, "validator": is_ippatus,             "allow_furo": 0},
    "yaku.menzenchin_tsumohou": {"han": 1, "yakuman": 0, "validator": is_menzenchin_tsumohou, "allow_furo": 0},
    "yaku.pinfu":               {"han": 1, "yakuman": 0, "validator": is_pinfu,               "allow_furo": 0},
    "yaku.tanyao":              {"han": 1, "yakuman": 0, "validator": is_tanyao,              "allow_furo": 1},
    "yaku.pure_double_sequence":{"han": 1, "yakuman": 0, "validator": is_pure_double_sequence,"allow_furo": 0},
    "yaku.yakuhai.player_wind": {"han": 1, "yakuman": 0, "validator": is_yakuhai_player_wind, "allow_furo": 1},
    "yaku.yakuhai.phase_wind":  {"han": 1, "yakuman": 0, "validator": is_yakuhai_phase_wind,  "allow_furo": 1},
    "yaku.yakuhai.chuu":        {"han": 1, "yakuman": 0, "validator": is_yakuhai_chuu,        "allow_furo": 1},
    "yaku.yakuhai.hatsu":       {"han": 1, "yakuman": 0, "validator": is_yakuhai_hatsu,       "allow_furo": 1},
    "yaku.yakuhai.shiro":       {"han": 1, "yakuman": 0, "validator": is_yakuhai_shiro,       "allow_furo": 1},
    "yaku.after_a_kan":         {"han": 1, "yakuman": 0, "validator": is_after_a_kan,         "allow_furo": 0},
    "yaku.robbing_a_kan":       {"han": 1, "yakuman": 0, "validator": is_robbing_a_kan,       "allow_furo": 0},
    "yaku.under_the_sea":       {"han": 1, "yakuman": 0, "validator": is_under_the_sea,       "allow_furo": 0},
    "yaku.under_the_river":     {"han": 1, "yakuman": 0, "validator": is_under_the_river,     "allow_furo": 0},

    # 2翻役
    "yaku.double_riichi":       {"han": 2, "yakuman": 0, "validator": is_double_riichi,       "allow_furo": 0},
    "yaku.all_triplets":        {"han": 2, "yakuman": 0, "validator": is_all_triplets,        "allow_furo": 0},
    "yaku.triple_triplets":     {"han": 2, "yakuman": 0, "validator": is_triple_triplets,     "allow_furo": 0},
    "yaku.three_quads":         {"han": 2, "yakuman": 0, "validator": is_three_quads,         "allow_furo": 0},
    "yaku.chiitoitsu":          {"han": 2, "yakuman": 0, "validator": is_chiitoitsu,          "allow_furo": 0},
    "yaku.sanshoku_doujun":     {"han": 2, "yakuman": 0, "validator": is_sanshoku_doujun,    "allow_furo": -1},
    "yaku.ikkitsuukan":         {"han": 2, "yakuman": 0, "validator": is_ikkitsuukan,         "allow_furo": -1},
    "yaku.honchantaiyaochuu":   {"han": 2, "yakuman": 0, "validator": is_honchantaiyaochuu,   "allow_furo": -1},

    # 3翻役
    "yaku.honitsu":             {"han": 3, "yakuman": 0, "validator": is_honitsu,             "allow_furo": -1},
    "yaku.junchan_taiyaochuu":  {"han": 3, "yakuman": 0, "validator": is_junchan_taiyaochuu,  "allow_furo": -1},

    # 6翻役
    "yaku.chinitsu":            {"han": 6, "yakuman": 0, "validator": is_chinitsu,            "allow_furo": -1},
}


# ── 主函数 ────────────────────────────────────────────────

def yaku_han(hand, furo, hu, settings):
    settings["player_wind_num"] = convert_tile_to_num(settings.get("player_wind", "1z"))
    settings["phase_wind_num"] = convert_tile_to_num(settings.get("phase_wind", "1z"))
    settings["dora_num"] = convert_hand_to_num(settings.get("dora", []))
    settings["ura_dora_num"] = convert_hand_to_num(settings.get("ura_dora", []))

    hand_num = convert_hand_to_num(hand)
    furo_num = [convert_hand_to_num(meld) for meld in furo]
    hu_num = convert_tile_to_num(hu)
    all_tile_strs = hand + [t for meld in furo for t in meld]

    # 将和牌加入
    test_hand = hand_num.copy()
    if len(hand_num) % 3 == 1:
        test_hand.append(hu_num)
        all_tile_strs.append(hu)

    menzenqing = is_menzenqing(hand_num, furo_num, hu_num)

    # 标准牌型拆分（一般形）+ 七对子
    pair_splits = (seven_pair_split(test_hand, furo_num, False, False) +
                   common_pair_split(test_hand, furo_num))

    # 七对子单独处理（门前清时尝试，允许相同对子）
    if menzenqing and not furo_num:
        chiitoi_splits = seven_pair_split(test_hand, furo_num, True, False)
        if chiitoi_splits and len(chiitoi_splits[0]) == 7:
            pair_splits = chiitoi_splits + pair_splits

    max_han = 0
    max_yakuman = 0
    max_yakus = []
    max_yakuman_yakus = []

    for pair_split in pair_splits:
        han = 0
        yakuman = 0
        yakus = []
        yakuman_yakus = []

        for yaku_key, yaku_def in yaku_han_list.items():
            if yaku_def["allow_furo"] == 0 and not menzenqing:
                continue
            try:
                if yaku_def["validator"](pair_split, hu_num, settings):
                    update_han = yaku_def["han"]
                    if yaku_def["allow_furo"] == -1 and not menzenqing:
                        update_han -= 1
                    han += update_han
                    yakuman += yaku_def["yakuman"]
                    if yaku_def["yakuman"] > 0:
                        yakuman_yakus.append((yaku_key, 0))
                    else:
                        yakus.append((yaku_key, update_han))
            except Exception:
                pass

        if yakuman > max_yakuman or (yakuman == max_yakuman and han > max_han):
            max_han = han
            max_yakuman = yakuman
            max_yakus = yakus
            max_yakuman_yakus = yakuman_yakus

    if max_han > 0 or max_yakuman > 0:
        dora_num = 0
        red_dora_num = 0
        ura_dora_num = 0
        for t in all_tile_strs:
            if t in settings.get("dora", []):
                dora_num += 1
            if t in settings.get("ura_dora", []):
                ura_dora_num += 1
            if t in ["0m", "0p", "0s"]:
                red_dora_num += 1
        if dora_num > 0:
            max_han += dora_num
            max_yakus.append(("yaku.dora", dora_num))
        if red_dora_num:
            max_han += red_dora_num
            max_yakus.append(("yaku.red_dora", red_dora_num))
        if settings.get("riichi", 0):
            max_han += ura_dora_num
            if ura_dora_num:
                max_yakus.append(("yaku.ura_dora", ura_dora_num))
        return {
            "han": max_han,
            "yakus": max_yakus,
            "yakuman": max_yakuman,
            "yakuman_yakus": max_yakuman_yakus,
        }

    return False
