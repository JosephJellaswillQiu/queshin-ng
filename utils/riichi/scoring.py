"""
立直麻将分数计算模块。
"""

# 番数 → (基本点数, 名称)
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

# 役满每番的基本点数（复合役满）
YAKUMAN_POINTS = 32000


def calculate_score(han: int, yakuman: int = 0,
                    is_dealer: bool = False, is_tsumo: bool = False,
                    honba: int = 0):
    """
    计算和牌后各家应付点数。

    Args:
        han: 番数
        yakuman: 役满倍数（0=不是役满, 1=1倍役满, 2=2倍...）
        is_dealer: 和牌者是否为庄家
        is_tsumo: 是否为自摸
        honba: 本场棒数（每本场+300点）

    Returns:
        dict: {
            "base_points": int,       # 基本点数
            "score_name": str,        # 满贯/跳满等名称
            "payments": {             # 各家支付
                "dealer": int,        # 庄家支付
                "non_dealer": int,    # 闲家每人支付
            },
            "total": int,             # 总收入
            "honba_bonus": int,       # 本场棒收入
        }
    """
    # 役满优先
    if yakuman > 0:
        base = YAKUMAN_POINTS * yakuman
        score_name = f"{yakuman}倍役满" if yakuman > 1 else "役满"
    else:
        capped_han = min(han, 13)
        base, score_name = HAN_POINTS_TABLE.get(capped_han, (32000, "役满"))

    honba_bonus = honba * 300

    if is_tsumo:
        if is_dealer:
            # 庄家自摸：闲家每人付 base/2（向上取百）
            per_non_dealer = _ceil100(base // 2) + honba * 100
            total = per_non_dealer * 3
            payments = {"dealer": 0, "non_dealer": per_non_dealer, "honba_per": honba * 100}
        else:
            # 闲家自摸：庄家付 base/2，闲家付 base/4
            dealer_pay = _ceil100(base // 2) + honba * 100
            non_dealer_pay = _ceil100(base // 4) + honba * 100
            total = dealer_pay + non_dealer_pay * 2
            payments = {"dealer": dealer_pay, "non_dealer": non_dealer_pay, "honba_per": honba * 100}
    else:
        # 荣和：放铳者全付
        if is_dealer:
            total = _ceil100(base * 1.5) + honba_bonus
        else:
            total = base + honba_bonus
        payments = {"dealer": 0, "non_dealer": 0, "ron_total": total}

    return {
        "base_points": base,
        "score_name": score_name,
        "han": han,
        "yakuman": yakuman,
        "is_dealer": is_dealer,
        "is_tsumo": is_tsumo,
        "honba": honba,
        "payments": payments,
        "total": total,
        "honba_bonus": honba_bonus,
    }


def _ceil100(n: int) -> int:
    """向上取整到100"""
    return ((n + 99) // 100) * 100
