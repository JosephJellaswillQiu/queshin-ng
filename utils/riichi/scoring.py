"""
立直麻将分数计算模块。
"""
from utils.riichi.yaku_han import tile_suit, is_terminal_or_honor


# ── 番数→满贯表 ──────────────────────────────────────────

HAN_POINTS_TABLE = {
    1:  (1000, "1翻"),
    2:  (2000, "2翻"),
    3:  (3900, "3翻"),
    4:  (7700, "4翻"),
    5:  (8000,  "满贯"),
    6:  (12000, "跳满"),
    7:  (12000, "跳满"),
    8:  (16000, "倍满"),
    9:  (16000, "倍满"),
    10: (16000, "倍满"),
    11: (24000, "三倍满"),
    12: (24000, "三倍满"),
    13: (32000, "役满(数え)"),
}

YAKUMAN_POINTS = 32000


# ── 符数计算 ──────────────────────────────────────────────

def calculate_fu(hand_tiles, furo, win_tile, is_tsumo=False, is_menzen=True):
    """
    计算和牌时的符数。

    Args:
        hand_tiles: 手牌（字符串列表，不含和牌）
        furo: 副露列表
        win_tile: 和了牌
        is_tsumo: 是否自摸
        is_menzen: 是否门前清

    Returns:
        int: 符数（已向上取整到十位）
    """
    from utils.riichi.yaku_han import convert_hand_to_num
    from utils.pair_split import common_pair_split, Pair, Triplet, Sequence, Quad

    hand_num = convert_hand_to_num(hand_tiles)
    furo_num = [convert_hand_to_num(m) for m in furo]
    win_num = convert_hand_to_num(win_tile)

    # 基础符
    if is_tsumo and is_menzen:
        fu = 20  # 门前清自摸
    else:
        fu = 30  # 其他

    # 尝试找到最佳拆分
    test_hand = hand_num.copy()
    if len(hand_num) % 3 == 1:
        test_hand.append(win_num)

    splits = common_pair_split(test_hand, furo_num)
    best_fu = fu

    for split in splits:
        extra_fu = 0
        for meld in split:
            if isinstance(meld, Triplet):
                is_yaochuu = is_terminal_or_honor(meld.num)
                if meld.furo:
                    extra_fu += 4 if is_yaochuu else 2  # 明刻
                else:
                    extra_fu += 8 if is_yaochuu else 4  # 暗刻
            elif isinstance(meld, Quad):
                is_yaochuu = is_terminal_or_honor(meld.num)
                if meld.furo:
                    extra_fu += 16 if is_yaochuu else 8  # 明杠
                else:
                    extra_fu += 32 if is_yaochuu else 16  # 暗杠
            elif isinstance(meld, Pair):
                # 雀头：役牌对子 +2
                if meld.num in [31, 32, 33]:  # 三元牌
                    extra_fu += 2
                # 自风/场风对子 +2（这里简化，由外部 settings 判断）
            # 顺子不加符

        # 听牌形符
        is_tanki = False
        is_kanchan = False
        is_penchan = False
        win_in_hand = win_num in test_hand

        if not is_tanki and not is_kanchan and not is_penchan:
            # 检查听牌形（简化：如果和了牌在某顺子的中间 → 嵌张；在两端 → 边张）
            for meld in split:
                if isinstance(meld, Sequence):
                    seq_start = meld.num % 9
                    if win_num == meld.num + 1 and seq_start == 0:
                        is_penchan = True  # 边张（12等3）
                    elif win_num == meld.num + 1 and seq_start == 6:
                        is_penchan = True  # 边张（78等9）
                    elif win_num == meld.num + 1:
                        is_kanchan = True  # 嵌张（24等3）

        if is_tanki:
            extra_fu += 2
        elif is_kanchan:
            extra_fu += 2
        elif is_penchan:
            extra_fu += 2

        # 门清荣和 +10
        if is_menzen and not is_tsumo and not furo_num:
            extra_fu += 10

        total = fu + extra_fu
        if total > best_fu:
            best_fu = total

    # 向上取整到十位
    return ((best_fu + 9) // 10) * 10


# ── 分数计算 ──────────────────────────────────────────────

def calculate_score(han: int, yakuman: int = 0,
                    is_dealer: bool = False, is_tsumo: bool = False,
                    honba: int = 0, fu: int = 30):
    """
    计算和牌后各家应付点数。

    Args:
        han: 番数
        yakuman: 役满倍数
        is_dealer: 是否为庄家
        is_tsumo: 是否自摸
        honba: 本场棒数
        fu: 符数（仅1-4翻时使用，默认30）

    Returns:
        dict: 包含 base_points, score_name, payments, total 等
    """
    # 役满优先
    if yakuman > 0:
        basic = YAKUMAN_POINTS * yakuman
        score_name = f"{yakuman}倍役满" if yakuman > 1 else "役满"
        base_ron = basic  # 役满的 basic=ron_total for non-dealer
    elif han >= 5:
        capped_han = min(han, 13)
        base_ron, score_name = HAN_POINTS_TABLE.get(capped_han, (32000, "役满"))
        basic = base_ron // 4  # 反算基本点
    elif han >= 1:
        # fu * 2^(han+2)，上限 2000（满贯基本点）
        basic = fu * (2 ** (han + 2))
        if basic > 2000:
            basic = 2000
        base_ron = _ceil100(basic * 4)
        score_name = f"{han}翻{fu}符"
    else:
        basic = 0
        base_ron = 0
        score_name = "无效"

    honba_bonus = honba * 300

    if is_tsumo:
        if is_dealer:
            per = _ceil100(basic * 2) + honba * 100
            total = per * 3
            payments = {"dealer": 0, "non_dealer": per, "honba_per": honba * 100}
        else:
            dealer_pay = _ceil100(basic * 2) + honba * 100
            non_pay = _ceil100(basic * 1) + honba * 100
            total = dealer_pay + non_pay * 2
            payments = {"dealer": dealer_pay, "non_dealer": non_pay, "honba_per": honba * 100}
    else:
        if is_dealer:
            total = _ceil100(basic * 6) + honba_bonus
        else:
            total = basic * 4  # basic*4 已取整
            # 役满/满贯表用 base_ron
            if yakuman > 0 or han >= 5:
                total = base_ron + honba_bonus
            else:
                total = _ceil100(basic * 4) + honba_bonus
        payments = {"dealer": 0, "non_dealer": 0, "ron_total": total}

    return {
        "base_points": basic * 4 if han < 5 else basic,
        "score_name": score_name,
        "han": han,
        "yakuman": yakuman,
        "fu": fu,
        "is_dealer": is_dealer,
        "is_tsumo": is_tsumo,
        "honba": honba,
        "payments": payments,
        "total": total,
        "honba_bonus": honba_bonus,
    }


def _ceil100(n: int) -> int:
    return ((n + 99) // 100) * 100
