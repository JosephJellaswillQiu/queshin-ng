import unittest
from utils.furo import (
    get_chi_combinations,
    get_pon_combinations,
    get_daiminkan_combinations,
    get_ankan_combinations,
    get_kakan_combinations,
    get_kita_combinations,
    get_possible_furo,
    KITA_TILE,
)


class TestChiCombinations(unittest.TestCase):
    def test_chi_card_as_first(self):
        # hand: 2m, 3m -> card 1m -> chi [1m, 2m, 3m]
        hand = [1, 2]
        furo = []
        card = 0  # 1m
        result = get_chi_combinations(hand, furo, card)
        self.assertEqual(len(result), 1)
        new_hand, new_furo, furo_type = result[0]
        self.assertEqual(sorted(new_hand), [])
        self.assertEqual(new_furo, [[0, 1, 2]])
        self.assertEqual(furo_type, "chi")

    def test_chi_card_as_middle(self):
        # hand: 4m, 6m -> card 5m -> chi [4m, 5m, 6m]
        hand = [3, 5]
        furo = []
        card = 4  # 5m
        result = get_chi_combinations(hand, furo, card)
        self.assertEqual(len(result), 1)
        new_hand, new_furo, furo_type = result[0]
        self.assertEqual(sorted(new_hand), [])
        self.assertEqual(new_furo, [[3, 4, 5]])
        self.assertEqual(furo_type, "chi")

    def test_chi_card_as_last(self):
        # hand: 7p, 8p -> card 9p -> chi [7p, 8p, 9p]
        hand = [15, 16]
        furo = []
        card = 17  # 9p
        result = get_chi_combinations(hand, furo, card)
        self.assertEqual(len(result), 1)
        new_hand, new_furo, furo_type = result[0]
        self.assertEqual(sorted(new_hand), [])
        self.assertEqual(new_furo, [[15, 16, 17]])
        self.assertEqual(furo_type, "chi")

    def test_chi_multiple_possibilities(self):
        # hand: 2m, 3m, 4m, 5m -> card 3m -> chi [1m,2m,3m] or [2m,3m,4m] or [3m,4m,5m]
        # wait, card=3m=2. Card as first: need 3,4 -> [2,3,4]; as middle: need 1,3 -> [1,2,3]; as last: need 1,2 but card is 2 so card_in_suit=2, need 0,1
        # Actually let me reconsider:
        # card=2 (3m). card_in_suit=2.
        # first: card_in_suit <= 6, need card+1=3, card+2=4 -> [2,3,4]
        # middle: 1 <= card_in_suit <= 7, need card-1=1, card+1=3 -> [1,2,3]
        # last: card_in_suit >= 2, need card-2=0, card-1=1 -> [0,1,2]
        hand = [0, 1, 3, 4]  # 1m, 2m, 4m, 5m
        furo = []
        card = 2  # 3m
        result = get_chi_combinations(hand, furo, card)
        # Should have 3 possibilities: [0,1,2] as last, [1,2,3] as middle, [2,3,4] as first
        self.assertEqual(len(result), 3)
        furo_types = [r[2] for r in result]
        self.assertTrue(all(t == "chi" for t in furo_types))

    def test_chi_edge_of_suit_no_cross(self):
        # 9m (8) cannot form chi with 1p (9) — different suits
        hand = [7, 9]  # 8m, 1p
        furo = []
        card = 8  # 9m
        result = get_chi_combinations(hand, furo, card)
        # card_in_suit=8, only first check: card_in_suit <= 6? No (8>6)
        # middle: 1 <= 8 <= 7? No
        # last: 8 >= 2? Yes, need 6,7 (which are 7m, 8m) — we have 7m but not both
        self.assertEqual(len(result), 0)

    def test_chi_honor_tile(self):
        # Honors (27+) cannot form chi
        hand = [27, 28]
        furo = []
        card = 29  # 西
        result = get_chi_combinations(hand, furo, card)
        self.assertEqual(len(result), 0)

    def test_chi_not_enough_tiles(self):
        # hand only has one of the two needed tiles
        hand = [1, 5]  # 2m, 6m
        furo = []
        card = 3  # 4m — need 2 and 5 as middle? no, need 2 and 4. As first? need 4 and 5.
        # card_in_suit=3
        # first: need 4,5 -> we have 5 but not 4
        # middle: need 2,4 -> we have 2 but not 4
        # last: need 1,2 -> only have 2, missing 1
        result = get_chi_combinations(hand, furo, card)
        self.assertEqual(len(result), 0)

    def test_chi_with_existing_furo(self):
        # Existing furo should be preserved
        hand = [1, 2]  # 2m, 3m
        furo = [[10, 10, 10]]  # existing pon
        card = 0  # 1m
        result = get_chi_combinations(hand, furo, card)
        self.assertEqual(len(result), 1)
        new_hand, new_furo, furo_type = result[0]
        self.assertEqual(new_furo, [[10, 10, 10], [0, 1, 2]])


class TestPonCombinations(unittest.TestCase):
    def test_pon_success(self):
        hand = [5, 5, 5, 10, 11]  # two 6m
        furo = []
        card = 5  # 6m
        result = get_pon_combinations(hand, furo, card)
        self.assertEqual(len(result), 1)
        new_hand, new_furo, furo_type = result[0]
        self.assertEqual(sorted(new_hand), [5, 10, 11])
        self.assertEqual(new_furo, [[5, 5, 5]])
        self.assertEqual(furo_type, "pon")

    def test_pon_three_copies(self):
        hand = [5, 5, 5, 10, 11]
        furo = []
        card = 5
        result = get_pon_combinations(hand, furo, card)
        self.assertEqual(len(result), 1)
        new_hand, _, _ = result[0]
        self.assertEqual(sorted(new_hand), [5, 10, 11])

    def test_pon_not_enough(self):
        hand = [5, 10, 11]
        furo = []
        card = 5
        result = get_pon_combinations(hand, furo, card)
        self.assertEqual(len(result), 0)

    def test_pon_honor(self):
        hand = [27, 27, 28, 29, 30]
        furo = []
        card = 27  # 東
        result = get_pon_combinations(hand, furo, card)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][2], "pon")

    def test_pon_with_existing_furo(self):
        hand = [5, 5, 10, 11]
        furo = [[1, 2, 3]]
        card = 5
        result = get_pon_combinations(hand, furo, card)
        self.assertEqual(len(result), 1)
        _, new_furo, _ = result[0]
        self.assertEqual(new_furo, [[1, 2, 3], [5, 5, 5]])


class TestDaiminkanCombinations(unittest.TestCase):
    def test_daiminkan_success(self):
        hand = [5, 5, 5, 10, 11]
        furo = []
        card = 5
        result = get_daiminkan_combinations(hand, furo, card)
        self.assertEqual(len(result), 1)
        new_hand, new_furo, furo_type = result[0]
        self.assertEqual(sorted(new_hand), [10, 11])
        self.assertEqual(new_furo, [[5, 5, 5, 5]])
        self.assertEqual(furo_type, "daiminkan")

    def test_daiminkan_not_enough(self):
        hand = [5, 5, 10, 11]
        furo = []
        card = 5
        result = get_daiminkan_combinations(hand, furo, card)
        self.assertEqual(len(result), 0)

    def test_daiminkan_four_copies(self):
        hand = [5, 5, 5, 5, 10]
        furo = []
        card = 5
        result = get_daiminkan_combinations(hand, furo, card)
        self.assertEqual(len(result), 1)


class TestAnkanCombinations(unittest.TestCase):
    def test_ankan_success(self):
        hand = [3, 3, 3, 3, 10, 11]  # four 4m
        furo = []
        result = get_ankan_combinations(hand, furo)
        self.assertEqual(len(result), 1)
        new_hand, new_furo, furo_type = result[0]
        self.assertEqual(sorted(new_hand), [10, 11])
        self.assertEqual(new_furo, [[3, 3, 3, -1]])
        self.assertEqual(furo_type, "ankan")

    def test_ankan_no_quad(self):
        hand = [3, 3, 3, 10, 11]
        furo = []
        result = get_ankan_combinations(hand, furo)
        self.assertEqual(len(result), 0)

    def test_ankan_multiple_quads(self):
        hand = [3, 3, 3, 3, 10, 10, 10, 10]
        furo = []
        result = get_ankan_combinations(hand, furo)
        self.assertEqual(len(result), 2)

    def test_ankan_honor(self):
        hand = [27, 27, 27, 27, 28]
        furo = []
        result = get_ankan_combinations(hand, furo)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][2], "ankan")


class TestKakanCombinations(unittest.TestCase):
    def test_kakan_success(self):
        hand = [5, 10, 11]  # 5=6m is the 4th tile
        furo = [[5, 5, 5]]  # existing open pon of 6m
        result = get_kakan_combinations(hand, furo)
        self.assertEqual(len(result), 1)
        new_hand, new_furo, furo_type = result[0]
        self.assertEqual(sorted(new_hand), [10, 11])
        self.assertEqual(new_furo[0], [5, 5, 5, 5])
        self.assertEqual(furo_type, "kakan")

    def test_kakan_no_matching_tile_in_hand(self):
        hand = [10, 11, 12]
        furo = [[5, 5, 5]]
        result = get_kakan_combinations(hand, furo)
        self.assertEqual(len(result), 0)

    def test_kakan_no_open_pon(self):
        hand = [5, 10, 11]
        furo = [[1, 2, 3]]  # chi, not pon
        result = get_kakan_combinations(hand, furo)
        self.assertEqual(len(result), 0)

    def test_kakan_multiple_pons(self):
        hand = [5, 10]
        furo = [[5, 5, 5], [10, 10, 10]]
        result = get_kakan_combinations(hand, furo)
        self.assertEqual(len(result), 2)

    def test_kakan_empty_furo(self):
        hand = [5, 5, 5, 5]
        furo = []
        result = get_kakan_combinations(hand, furo)
        self.assertEqual(len(result), 0)


class TestKitaCombinations(unittest.TestCase):
    def test_kita_single_north(self):
        hand = [KITA_TILE, 1, 2, 3]
        furo = []
        result = get_kita_combinations(hand, furo)
        self.assertEqual(len(result), 1)
        new_hand, new_furo, furo_type = result[0]
        self.assertEqual(sorted(new_hand), [1, 2, 3])
        self.assertEqual(new_furo, [[KITA_TILE]])
        self.assertEqual(furo_type, "kita")

    def test_kita_multiple_north(self):
        hand = [KITA_TILE, KITA_TILE, KITA_TILE, 1, 2]
        furo = []
        result = get_kita_combinations(hand, furo)
        self.assertEqual(len(result), 3)
        for _, _, furo_type in result:
            self.assertEqual(furo_type, "kita")

    def test_kita_no_north(self):
        hand = [1, 2, 3, 4, 5]
        furo = []
        result = get_kita_combinations(hand, furo)
        self.assertEqual(len(result), 0)

    def test_kita_other_honors_not_kita(self):
        # Only north (30) can be kita, not other winds
        hand = [27, 28, 29, 31, 32, 33]
        furo = []
        result = get_kita_combinations(hand, furo)
        self.assertEqual(len(result), 0)


class TestGetPossibleFuro(unittest.TestCase):
    def test_possible_furo_with_chi(self):
        hand = [0, 1, 5, 5, 10, 11]  # 1m,2m for chi, two 6m for pon
        furo = []
        card = 2  # 3m: chi as last [0,1,2], pon no, daiminkan no
        result = get_possible_furo(hand, furo, card, allow_chi=True)
        # chi: [0,1,2] -> hand becomes [5,5,10,11]
        self.assertEqual(len(result), 1)
        new_hand, new_furo, furo_type = result[0]
        self.assertEqual(sorted(new_hand), [5, 5, 10, 11])
        self.assertEqual(new_furo, [[0, 1, 2]])
        self.assertEqual(furo_type, "chi")

    def test_possible_furo_without_chi(self):
        hand = [0, 1, 5, 5, 10, 11]
        furo = []
        card = 2  # 3m
        result = get_possible_furo(hand, furo, card, allow_chi=False)
        self.assertEqual(len(result), 0)

    def test_possible_furo_pon_and_daiminkan(self):
        # Hand has 3 copies: daiminkan should be returned
        hand = [5, 5, 5, 10, 11]
        furo = []
        card = 5
        result = get_possible_furo(hand, furo, card, allow_chi=True)
        # Should have both pon and daiminkan
        self.assertEqual(len(result), 2)
        types = [r[2] for r in result]
        self.assertIn("pon", types)
        self.assertIn("daiminkan", types)

    def test_possible_furo_all_three(self):
        hand = [0, 1, 0, 0, 0, 10]  # four 1m (0), also 2m (1) for chi
        furo = []
        card = 0  # 1m
        result = get_possible_furo(hand, furo, card, allow_chi=True)
        # pon: yes (3+ copies), daiminkan: yes (3+ copies), chi: card=0, card_in_suit=0
        # first: need 1,2 -> we have 1 but not 2 -> no chi
        # So results: pon + daiminkan = 2
        # Actually wait, card=0 is 1m. Chi as first: need 1m+1, 1m+2 -> 1,2 -> we have 1 but not 2, so no chi from first.
        # Chi as middle: card_in_suit=0, not between 1-7, so no.
        # Chi as last: card_in_suit=0, not >=2, so no.
        self.assertEqual(len(result), 2)

    def test_possible_furo_chi_and_pon(self):
        # hand has tiles for both chi and pon with the card
        hand = [5, 5, 3, 4]  # two 6m + 4m,5m -> card 5m can form chi [3,4,5]...
        # Wait card=4 is 5m. card_in_suit=4.
        # chi as first: need 5,6 (6m,7m) -> no
        # chi as middle: need 3,5 (4m,6m) -> we have 3 and 5! [3,4,5]
        # chi as last: need 2,3 (3m,4m) -> we have 3 but not 2
        # pon: card=4, we only have one 5m -> no
        # So only chi
        furo = []
        card = 4
        result = get_possible_furo(hand, furo, card, allow_chi=True)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][2], "chi")

    def test_possible_furo_default_allow_chi(self):
        hand = [0, 1, 10, 11]
        furo = []
        card = 2  # 3m
        result = get_possible_furo(hand, furo, card)
        # default allow_chi=True -> should find chi
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][2], "chi")

    def test_possible_furo_empty(self):
        hand = [10, 11, 12, 13]
        furo = []
        card = 5
        result = get_possible_furo(hand, furo, card)
        self.assertEqual(len(result), 0)


if __name__ == '__main__':
    unittest.main()
