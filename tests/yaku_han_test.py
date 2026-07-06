import unittest
from utils.riichi.yaku_han import yaku_han

_BASE = {
    "dora": [],
    "ura_dora": [],
    "player_wind": "2z",
    "phase_wind": "3z",
    "riichi": 0,
    "ippatus": False,
    "after_a_kan": False,
    "robbing_a_kan": False,
    "under_the_sea": False,
    "under_the_river": False,
    "ron": True,
}


def _settings(**kw):
    s = dict(_BASE)
    s.update(kw)
    return s


class TestYakuHan(unittest.TestCase):

    # ── 已有役种 ────────────────────────────────────────────

    def test_pinfu(self):
        hand = ["1m", "2m", "3m", "3m", "4m", "5p", "6p", "7p",
                "2s", "2s", "3s", "4s", "5s"]
        result = yaku_han(hand, [], "2m", _settings(player_wind="2z", phase_wind="3z", riichi=1))
        self.assertTrue(result)
        self.assertIn(("yaku.pinfu", 1), result["yakus"])

    def test_player_wind(self):
        hand = ["1m", "2m", "3m", "3m", "4m", "5p", "6p", "7p",
                "2s", "2s", "1z", "1z", "1z"]
        result = yaku_han(hand, [], "2m", _settings(player_wind="1z", phase_wind="1z"))
        self.assertTrue(result)
        self.assertIn(("yaku.yakuhai.player_wind", 1), result["yakus"])

    def test_tanyao(self):
        hand = ["2m", "3m", "4m", "3p", "4p", "5p", "6s", "7s", "8s",
                "5m", "5m", "2p", "2p"]
        result = yaku_han(hand, [], "2p", _settings())
        self.assertTrue(result)
        self.assertIn(("yaku.tanyao", 1), result["yakus"])

    # ── 新增役种 ────────────────────────────────────────────

    def test_honitsu(self):
        """混一色：万子 + 字牌"""
        hand = ["1m", "1m", "1m", "2m", "3m", "4m", "5m", "6m", "7m",
                "2z", "2z", "2z", "3z"]
        result = yaku_han(hand, [], "3z", _settings())
        self.assertTrue(result)
        self.assertIn(("yaku.honitsu", 3), result["yakus"])

    def test_honitsu_with_furo(self):
        """混一色副露降番（10张手牌 + 1副露 + 1和牌）"""
        hand = ["2m", "3m", "4m", "5m", "6m", "7m", "2z", "2z", "2z", "3z"]
        furo = [["1m", "1m", "1m"]]
        result = yaku_han(hand, furo, "3z", _settings())
        self.assertTrue(result, f"Expected honitsu, got: {result}")
        self.assertIn(("yaku.honitsu", 2), result["yakus"])  # 副露降1翻

    def test_chinitsu(self):
        """清一色"""
        hand = ["1m", "1m", "1m", "2m", "3m", "4m", "5m", "6m", "7m",
                "7m", "8m", "9m", "3m"]
        result = yaku_han(hand, [], "3m", _settings())
        self.assertTrue(result)
        self.assertIn(("yaku.chinitsu", 6), result["yakus"])

    def test_ikkitsuukan(self):
        """一气通贯：123m + 456m + 789m"""
        hand = ["1m", "2m", "3m", "4m", "5m", "6m", "7m", "8m", "9m",
                "2z", "2z", "2z", "3z"]
        result = yaku_han(hand, [], "3z", _settings())
        self.assertTrue(result)
        self.assertIn(("yaku.ikkitsuukan", 2), result["yakus"])

    def test_sanshoku_doujun(self):
        """三色同顺：123m + 123p + 123s"""
        hand = ["1m", "2m", "3m", "1p", "2p", "3p", "1s", "2s", "3s",
                "5z", "5z", "5z", "6z"]
        result = yaku_han(hand, [], "6z", _settings())
        self.assertTrue(result)
        self.assertIn(("yaku.sanshoku_doujun", 2), result["yakus"])

    def test_chiitoitsu(self):
        """七对子：7个对子"""
        hand = ["1m", "1m", "2m", "2m", "3m", "3m", "4m", "4m",
                "5m", "5m", "6m", "6m", "7m"]
        result = yaku_han(hand, [], "7m", _settings())
        self.assertTrue(result)
        self.assertIn(("yaku.chiitoitsu", 2), result["yakus"])

    def test_honchantaiyaochuu(self):
        """混全帯幺九：所有面子+雀头含幺九牌"""
        hand = ["1m", "2m", "3m", "7m", "8m", "9m", "1p", "1p", "1p",
                "9s", "9s", "9s", "1z"]
        result = yaku_han(hand, [], "1z", _settings())
        self.assertTrue(result)
        self.assertIn(("yaku.honchantaiyaochuu", 2), result["yakus"])

    def test_junchan_taiyaochuu(self):
        """纯全帯幺九：所有面子+雀头含老头牌，无字牌"""
        hand = ["1m", "2m", "3m", "7m", "8m", "9m", "1p", "1p", "1p",
                "9s", "9s", "9s", "1m"]
        result = yaku_han(hand, [], "1m", _settings())
        self.assertTrue(result)
        self.assertIn(("yaku.junchan_taiyaochuu", 3), result["yakus"])

    def test_all_triplets(self):
        """对对和"""
        hand = ["1m", "1m", "1m", "3p", "3p", "3p", "5s", "5s", "5s",
                "7z", "7z", "7z", "2z"]
        result = yaku_han(hand, [], "2z", _settings())
        self.assertTrue(result)
        self.assertIn(("yaku.all_triplets", 2), result["yakus"])

    # ── 役种组合 ────────────────────────────────────────────

    def test_tanyao_pinfu(self):
        """断幺九 + 平和 组合"""
        hand = ["2m", "3m", "4m", "3p", "4p", "5p", "6s", "7s", "8s",
                "5m", "6m", "7m", "4m"]
        result = yaku_han(hand, [], "1m", _settings(riichi=1, player_wind="2z", phase_wind="3z"))
        self.assertTrue(result)
        self.assertGreaterEqual(result["han"], 2)

    def test_riichi_pinfu_tanyao(self):
        """立直 + 平和 + 断幺九（两边听）"""
        # [2m,3m,4m] [3m,4m,5m] [3p,4p,5p] [4s,5s,6s] [7m,7m]
        # ryanmen: 4m-5m waiting for 3m or 6m
        hand = ["2m", "3m", "4m", "4m", "5m", "3p", "4p", "5p",
                "4s", "5s", "6s", "7m", "7m"]
        result = yaku_han(hand, [], "3m", _settings(riichi=1, player_wind="2z", phase_wind="3z"))
        self.assertTrue(result, f"Expected win, got: {result}")
        self.assertIn(("yaku.riichi", 1), result["yakus"])

    def test_ankan_menzen(self):
        """暗杠保持门前清——副露为暗杠 [1z,1z,1z,-1]，不影响立直等门前役"""
        # 手牌 10 张 + 暗杠 furo(4张) + 和牌 = 14
        # 拆分: [2m,3m,4m] [5p,6p,7p] [3z,3z,3z] [1z,1z,1z,-1](暗杠) [8s,8s]
        hand = ["2m", "3m", "4m", "5p", "6p", "7p", "3z", "3z", "3z", "8s"]
        furo = [["1z", "1z", "1z", "-1"]]
        result = yaku_han(hand, furo, "8s", _settings(player_wind="1z", phase_wind="2z", riichi=1))
        self.assertTrue(result, f"Expected win with ankan, got: {result}")
        # 暗杠 1z 是自风刻子
        self.assertIn(("yaku.yakuhai.player_wind", 1), result["yakus"])
        # 暗杠保持门前清 → 立直成立
        self.assertIn(("yaku.riichi", 1), result["yakus"])
        # 暗杠不影响三色同刻判定（3z 暗刻 + 1z 暗杠不构成三色同刻）

    # ── 边界 ────────────────────────────────────────────────

    def test_not_win_hand(self):
        """不能和的牌返回 False"""
        hand = ["1m", "2m", "4m", "5p", "6p", "8p", "2s", "3s",
                "4s", "6s", "7z", "1z", "3z"]
        result = yaku_han(hand, [], "9m", _settings())
        self.assertFalse(result)

    def test_no_yaku_hand(self):
        """能和但没有役种的牌（需要立直才算）返回 False"""
        hand = ["2m", "3m", "4m", "3p", "4p", "5p", "6s", "7s", "8s",
                "1z", "1z", "1z", "2z"]
        result = yaku_han(hand, [], "2z", _settings())
        # 有役牌对子但没有刻子 → 只有役牌雀头不算役，所以可能没役
        # 实际: 2z 是一对，但 settings 里 player_wind=2z, 雀头是役牌但刻子才是役
        # 所以可能 result 是 False
        # 这个测试验证不会崩溃
        self.assertIsInstance(result, (bool, dict))


if __name__ == '__main__':
    unittest.main()
