"""副露判断工具，根据手牌和场上打出的牌给出可能的副露组合。
0~8 are manzu, 9~17 are pinzu, 18~26 are souzu, 27~33 are honors.
"""


def get_chi_combinations(hand, furo, card):
    """Get all possible chi (吃) combinations.

    Args:
        hand (list[num]): A list of tiles representing the hand.
        furo (list[list[num]]): A list of melds.
        card (num): last played card

    Returns:
        list[tuple[list[num], list[list[num]], str]]: A list of (hand, furo, "chi") tuples.
    """
    results = []
    if card > 26:
        return results

    tile_count = [0] * 34
    for tile in hand:
        tile_count[tile] += 1

    card_in_suit = card % 9

    # Card as first tile: [card, card+1, card+2]
    if card_in_suit <= 6:
        if tile_count[card + 1] >= 1 and tile_count[card + 2] >= 1:
            new_hand = hand.copy()
            new_hand.remove(card + 1)
            new_hand.remove(card + 2)
            new_furo = furo + [[card, card + 1, card + 2]]
            results.append((new_hand, new_furo, "chi"))

    # Card as middle tile: [card-1, card, card+1]
    if 1 <= card_in_suit <= 7:
        if tile_count[card - 1] >= 1 and tile_count[card + 1] >= 1:
            new_hand = hand.copy()
            new_hand.remove(card - 1)
            new_hand.remove(card + 1)
            new_furo = furo + [[card - 1, card, card + 1]]
            results.append((new_hand, new_furo, "chi"))

    # Card as last tile: [card-2, card-1, card]
    if card_in_suit >= 2:
        if tile_count[card - 2] >= 1 and tile_count[card - 1] >= 1:
            new_hand = hand.copy()
            new_hand.remove(card - 2)
            new_hand.remove(card - 1)
            new_furo = furo + [[card - 2, card - 1, card]]
            results.append((new_hand, new_furo, "chi"))

    return results


def get_pon_combinations(hand, furo, card):
    """Get all possible pon (碰) combinations.

    Args:
        hand (list[num]): A list of tiles representing the hand.
        furo (list[list[num]]): A list of melds.
        card (num): last played card

    Returns:
        list[tuple[list[num], list[list[num]], str]]: A list of (hand, furo, "pon") tuples.
    """
    results = []
    count = hand.count(card)
    if count >= 2:
        new_hand = hand.copy()
        new_hand.remove(card)
        new_hand.remove(card)
        new_furo = furo + [[card, card, card]]
        results.append((new_hand, new_furo, "pon"))

    return results


def get_daiminkan_combinations(hand, furo, card):
    """Get all possible daiminkan (大明杠) combinations.

    Args:
        hand (list[num]): A list of tiles representing the hand.
        furo (list[list[num]]): A list of melds.
        card (num): last played card

    Returns:
        list[tuple[list[num], list[list[num]], str]]: A list of (hand, furo, "daiminkan") tuples.
    """
    results = []
    count = hand.count(card)
    if count >= 3:
        new_hand = hand.copy()
        new_hand.remove(card)
        new_hand.remove(card)
        new_hand.remove(card)
        new_furo = furo + [[card, card, card, card]]
        results.append((new_hand, new_furo, "daiminkan"))

    return results


def get_ankan_combinations(hand, furo):
    """Get all possible ankan (暗杠) combinations.

    Args:
        hand (list[num]): A list of tiles representing the hand.
        furo (list[list[num]]): A list of melds.

    Returns:
        list[tuple[list[num], list[list[num]], str]]: A list of (hand, furo, "ankan") tuples.
    """
    results = []
    tile_count = [0] * 34
    for tile in hand:
        tile_count[tile] += 1

    for tile in range(34):
        if tile_count[tile] >= 4:
            new_hand = hand.copy()
            for _ in range(4):
                new_hand.remove(tile)
            new_furo = furo + [[tile, tile, tile, -1]]
            results.append((new_hand, new_furo, "ankan"))

    return results


def get_kakan_combinations(hand, furo):
    """Get all possible kakan (加杠) combinations.

    Args:
        hand (list[num]): A list of tiles representing the hand.
        furo (list[list[num]]): A list of melds.

    Returns:
        list[tuple[list[num], list[list[num]], str]]: A list of (hand, furo, "kakan") tuples.
    """
    results = []

    for i, meld in enumerate(furo):
        if len(meld) == 3 and meld[0] == meld[1] == meld[2]:
            tile = meld[0]
            if tile in hand:
                new_hand = hand.copy()
                new_hand.remove(tile)
                new_furo = furo.copy()
                new_furo[i] = [tile, tile, tile, tile]
                results.append((new_hand, new_furo, "kakan"))

    return results


KITA_TILE = 30  # 北


def get_kita_combinations(hand, furo):
    """Get all possible kita (拔北) combinations.

    Args:
        hand (list[num]): A list of tiles representing the hand.
        furo (list[list[num]]): A list of melds.

    Returns:
        list[tuple[list[num], list[list[num]], str]]: A list of (hand, furo, "kita") tuples.
    """
    results = []
    for tile in hand:
        if tile == KITA_TILE:
            new_hand = hand.copy()
            new_hand.remove(tile)
            new_furo = furo + [[tile]]
            results.append((new_hand, new_furo, "kita"))

    return results


def get_possible_furo(hand, furo, card, allow_chi=True):
    """Get all possible meld combinations based on the hand and the last discarded tile.

    Args:
        hand (list[num]): A list of tiles representing the hand. 0~8 are manzu, 9~17 are pinzu, 18~26 are souzu, 27~33 are honors.
        furo (list[list[num]]): A list of melds.
        card (num): last played card
        allow_chi (bool): whether to include chi (吃) combinations. Defaults to True.

    Returns:
        list[tuple[list[num], list[list[num]], str]]: A list of (hand, furo, furo_type) tuples.
    """
    results = get_pon_combinations(hand, furo, card) + \
              get_daiminkan_combinations(hand, furo, card)
    if allow_chi:
        results += get_chi_combinations(hand, furo, card)
    return results
