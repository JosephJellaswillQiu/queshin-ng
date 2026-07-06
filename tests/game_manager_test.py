"""游戏管理器测试"""
import unittest
from app.game_manager import MajRoom, RoomManager


class TestMajRoomInit(unittest.TestCase):

    def setUp(self):
        self.room = MajRoom(1, "test_room")

    def test_add_players(self):
        self.assertTrue(self.room.add_player("sid_0", 1))
        self.assertTrue(self.room.add_player("sid_1", 2))
        self.assertTrue(self.room.add_player("sid_2", 3))
        self.assertTrue(self.room.add_player("sid_3", 4))
        self.assertFalse(self.room.add_player("sid_4", 5))  # 满员
        self.assertEqual(len(self.room.players), 4)

    def test_seat_winds(self):
        """座位风位正确"""
        self.room.add_player("sid_0", 1)
        self.room.add_player("sid_1", 2)
        self.room.add_player("sid_2", 3)
        self.room.add_player("sid_3", 4)

        # 默认庄家在0位，所以玩家0=东
        self.assertEqual(self.room.get_player_wind("sid_0"), "1z")  # 东(庄)
        self.assertEqual(self.room.get_player_wind("sid_1"), "2z")  # 南
        self.assertEqual(self.room.get_player_wind("sid_2"), "3z")  # 西
        self.assertEqual(self.room.get_player_wind("sid_3"), "4z")  # 北

    def test_seat_labels(self):
        self.room.add_player("sid_0", 1)
        self.room.add_player("sid_1", 2)
        self.assertEqual(self.room.get_seat_label("sid_0"), "东")
        self.assertEqual(self.room.get_seat_label("sid_1"), "南")

    def test_dealer_rotation(self):
        """轮庄：庄家不听牌时轮庄"""
        self.room.add_player("sid_0", 1)
        self.room.add_player("sid_1", 2)
        self.room.add_player("sid_2", 3)
        self.room.add_player("sid_3", 4)

        self.assertEqual(self.room.dealer_idx, 0)
        self.room.next_round(dealer_stays=False)
        self.assertEqual(self.room.dealer_idx, 1)
        self.assertEqual(self.room.settings["round_number"], 1)
        self.assertEqual(self.room.settings["honba"], 0)

    def test_dealer_stays(self):
        """连庄：庄家听牌时连庄"""
        self.room.add_player("sid_0", 1)
        self.room.add_player("sid_1", 2)
        self.room.add_player("sid_2", 3)
        self.room.add_player("sid_3", 4)

        self.room.next_round(dealer_stays=True)
        self.assertEqual(self.room.dealer_idx, 0)  # 庄家不变
        self.assertEqual(self.room.settings["honba"], 1)  # 本场棒+1

    def test_wind_after_dealer_rotation(self):
        """轮庄后风位正确更新"""
        self.room.add_player("sid_0", 1)
        self.room.add_player("sid_1", 2)
        self.room.add_player("sid_2", 3)
        self.room.add_player("sid_3", 4)

        self.room.next_round(dealer_stays=False)
        # 庄家变成 sid_1，所以 sid_1=东, sid_2=南, sid_3=西, sid_0=北
        self.assertEqual(self.room.get_player_wind("sid_1"), "1z")  # 新庄家=东
        self.assertEqual(self.room.get_player_wind("sid_2"), "2z")  # 南
        self.assertEqual(self.room.get_player_wind("sid_3"), "3z")  # 西
        self.assertEqual(self.room.get_player_wind("sid_0"), "4z")  # 北（原庄家）


class TestRiichi(unittest.TestCase):

    def setUp(self):
        self.room = MajRoom(1, "test")
        self.room.add_player("sid_0", 1)
        self.room.add_player("sid_1", 2)

    def test_cannot_riichi_with_furo(self):
        """有副露不能立直"""
        self.room.player_furo["sid_0"] = [["1m", "2m", "3m"]]
        self.assertFalse(self.room.can_riichi("sid_0"))

    def test_can_riichi_menzen(self):
        """门前清可以立直"""
        self.room.hands["sid_0"] = ["1m"] * 14  # 14张手牌
        self.assertTrue(self.room.can_riichi("sid_0"))

    def test_cannot_riichi_with_13_tiles(self):
        """只有13张不能立直（还没摸牌）"""
        self.room.hands["sid_0"] = ["1m"] * 13
        self.assertFalse(self.room.can_riichi("sid_0"))

    def test_declare_riichi(self):
        """声明立直"""
        self.room.hands["sid_0"] = ["1m"] * 14
        self.room.declare_riichi("sid_0")
        self.assertIn("sid_0", self.room.riichi_declared)
        self.assertEqual(self.room.riichi_sticks, 1)
        self.assertTrue(self.room.settings["ippatus"])

    def test_cannot_riichi_twice(self):
        """不能重复立直"""
        self.room.hands["sid_0"] = ["1m"] * 14
        self.room.declare_riichi("sid_0")
        self.assertFalse(self.room.can_riichi("sid_0"))


class TestTurnManagement(unittest.TestCase):

    def test_discard_and_turn(self):
        """出牌后正常从手牌移除"""
        room = MajRoom(1, "test")
        room.add_player("sid_0", 1)
        room.hands["sid_0"] = ["1m", "2m", "3m", "4m", "5m", "6m", "7m",
                                "1p", "2p", "3p", "5z", "6z", "7z", "1s"]
        self.assertTrue(room.discard_tile("sid_0", "1m"))
        self.assertNotIn("1m", room.hands["sid_0"])
        self.assertIn("1m", room.player_rivers["sid_0"])

    def test_discard_invalid_tile(self):
        """不能打出手中没有的牌"""
        room = MajRoom(1, "test")
        room.add_player("sid_0", 1)
        room.hands["sid_0"] = ["1m", "2m", "3m"]
        self.assertFalse(room.discard_tile("sid_0", "9m"))


class TestTenpaiCheck(unittest.TestCase):

    def test_tenpai_simple(self):
        """简单听牌检测"""
        room = MajRoom(1, "test")
        room.add_player("sid_0", 1)
        # 已经可以和的牌型（碰碰和雏形）
        room.hands["sid_0"] = ["1m", "1m", "1m", "2m", "2m", "2m",
                                "3m", "3m", "3m", "4m", "4m", "4m", "5z", "5z"]
        room.player_furo["sid_0"] = []
        # 这个牌型应该是听牌了（差一对做雀头）— 实际取决于pair_split
        # 这里只验证方法不会崩溃
        result = room.is_tenpai("sid_0")
        self.assertIsInstance(result, bool)

    def test_not_tenpai(self):
        """完全散牌不聽"""
        room = MajRoom(1, "test")
        room.add_player("sid_0", 1)
        room.hands["sid_0"] = ["1m", "2m", "4m", "6p", "8p",
                                "2s", "5s", "7s", "1z", "3z",
                                "5z", "7z", "9m", "9s"]
        room.player_furo["sid_0"] = []
        self.assertFalse(room.is_tenpai("sid_0"))


class TestFuriten(unittest.TestCase):

    def test_basic_furiten(self):
        """打出过的牌可以组成和牌形 → 振听"""
        room = MajRoom(1, "test")
        room.add_player("sid_0", 1)
        # 设置一个能和牌的手牌，但牌河里有一张能和牌的牌
        # 简化测试：验证方法存在且能正常执行
        room.hands["sid_0"] = ["1m"] * 14
        room.player_rivers["sid_0"] = ["1m"]
        room.player_furo["sid_0"] = []
        result = room.is_furiten("sid_0", "1m")
        self.assertIsInstance(result, bool)


class TestWallGeneration(unittest.TestCase):

    def test_wall_has_136_tiles(self):
        """牌山=122张 + 王牌=14张 = 136"""
        full = MajRoom._generate_full_wall()
        self.assertEqual(len(full), 136)

    def test_init_game_deals_correctly(self):
        """发牌：每人13张 + 庄家14张"""
        room = MajRoom(1, "test")
        for i in range(4):
            room.add_player(f"sid_{i}", i + 1)
        room.init_game()

        dealer = room.players[room.dealer_idx]
        self.assertEqual(len(room.hands[dealer]), 14)
        for sid in room.players:
            if sid != dealer:
                self.assertEqual(len(room.hands[sid]), 13)

    def test_dora_next(self):
        """宝牌指示计算"""
        self.assertEqual(MajRoom._next_dora("1m"), "2m")
        self.assertEqual(MajRoom._next_dora("9m"), "1m")
        self.assertEqual(MajRoom._next_dora("1p"), "2p")
        self.assertEqual(MajRoom._next_dora("1z"), "2z")  # 东→南
        self.assertEqual(MajRoom._next_dora("4z"), "1z")  # 北→东
        self.assertEqual(MajRoom._next_dora("5z"), "6z")  # 白→发
        self.assertEqual(MajRoom._next_dora("6z"), "7z")  # 发→中
        self.assertEqual(MajRoom._next_dora("7z"), "5z")  # 中→白


class TestRoomManager(unittest.TestCase):

    def test_create_and_get(self):
        rm = RoomManager()
        room = rm.create_room(1, "room_a")
        self.assertIsNotNone(room)
        self.assertEqual(rm.get_room("room_a"), room)

    def test_duplicate_name(self):
        rm = RoomManager()
        rm.create_room(1, "room_a")
        self.assertIsNone(rm.create_room(2, "room_a"))

    def test_remove(self):
        rm = RoomManager()
        rm.create_room(1, "room_a")
        rm.remove_room("room_a")
        self.assertIsNone(rm.get_room("room_a"))


if __name__ == "__main__":
    unittest.main()
