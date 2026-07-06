"""分数计算测试"""
import unittest
from utils.riichi.scoring import calculate_score


class TestScoring(unittest.TestCase):

    def test_1han_non_dealer_ron(self):
        """1翻 闲家荣和 = 1000点"""
        result = calculate_score(han=1, is_dealer=False, is_tsumo=False)
        self.assertEqual(result["total"], 1000)
        self.assertEqual(result["score_name"], "1翻")

    def test_1han_dealer_ron(self):
        """1翻 庄家荣和 = 1500点 (1000*1.5=1500)"""
        result = calculate_score(han=1, is_dealer=True, is_tsumo=False)
        self.assertEqual(result["total"], 1500)

    def test_2han_dealer_ron(self):
        """2翻 庄家荣和 = 3000点 (2000*1.5)"""
        result = calculate_score(han=2, is_dealer=True, is_tsumo=False)
        self.assertEqual(result["total"], 3000)

    def test_3han_non_dealer_ron(self):
        """3翻 闲家荣和 = 3900点"""
        result = calculate_score(han=3, is_dealer=False, is_tsumo=False)
        self.assertEqual(result["total"], 3900)

    def test_4han_dealer_ron(self):
        """4翻 庄家荣和 = 11600点 (7700*1.5≈11600)"""
        result = calculate_score(han=4, is_dealer=True, is_tsumo=False)
        self.assertEqual(result["total"], 11600)

    def test_5han_mangan_non_dealer(self):
        """5翻 满贯 闲家=8000"""
        result = calculate_score(han=5, is_dealer=False, is_tsumo=False)
        self.assertEqual(result["total"], 8000)
        self.assertEqual(result["score_name"], "满贯")

    def test_5han_mangan_dealer(self):
        """5翻 满贯 庄家=12000"""
        result = calculate_score(han=5, is_dealer=True, is_tsumo=False)
        self.assertEqual(result["total"], 12000)

    def test_6han_haneman(self):
        """6翻 跳满=12000"""
        result = calculate_score(han=6, is_dealer=False, is_tsumo=False)
        self.assertEqual(result["total"], 12000)
        self.assertEqual(result["score_name"], "跳满")

    def test_8han_baiman(self):
        """8翻 倍满=16000"""
        result = calculate_score(han=8, is_dealer=False, is_tsumo=False)
        self.assertEqual(result["total"], 16000)
        self.assertEqual(result["score_name"], "倍满")

    def test_11han_sanbaiman(self):
        """11翻 三倍满=24000"""
        result = calculate_score(han=11, is_dealer=False, is_tsumo=False)
        self.assertEqual(result["total"], 24000)
        self.assertEqual(result["score_name"], "三倍满")

    def test_13han_kazoe_yakuman(self):
        """13翻 数え役满=32000"""
        result = calculate_score(han=13, is_dealer=False, is_tsumo=False)
        self.assertEqual(result["total"], 32000)

    def test_dealer_tsumo(self):
        """庄家自摸：闲家每人付 base/2"""
        result = calculate_score(han=3, is_dealer=True, is_tsumo=True)
        # base=3900, dealer tsumo: each non-dealer pays ceil100(3900//2)=2000
        self.assertEqual(result["payments"]["non_dealer"], 2000)
        self.assertEqual(result["total"], 6000)  # 2000*3

    def test_non_dealer_tsumo(self):
        """闲家自摸：庄家付 base/2，闲家付 base/4"""
        result = calculate_score(han=3, is_dealer=False, is_tsumo=True)
        # base=3900, non-dealer tsumo: dealer pays ceil100(3900//2)=2000
        # other non-dealers pay ceil100(3900//4)=1000
        self.assertEqual(result["payments"]["dealer"], 2000)
        self.assertEqual(result["payments"]["non_dealer"], 1000)
        self.assertEqual(result["total"], 4000)  # 2000+1000+1000

    def test_honba_bonus_ron(self):
        """本场棒：荣和+300/本场"""
        result = calculate_score(han=1, is_dealer=False, is_tsumo=False, honba=2)
        self.assertEqual(result["total"], 1600)  # 1000 + 300*2

    def test_yakuman_single(self):
        """1倍役满 闲家=32000"""
        result = calculate_score(han=0, yakuman=1, is_dealer=False, is_tsumo=False)
        self.assertEqual(result["total"], 32000)
        self.assertEqual(result["score_name"], "役满")

    def test_yakuman_double(self):
        """2倍役满=64000"""
        result = calculate_score(han=0, yakuman=2, is_dealer=False, is_tsumo=False)
        self.assertEqual(result["total"], 64000)
        self.assertEqual(result["score_name"], "2倍役满")


if __name__ == "__main__":
    unittest.main()
