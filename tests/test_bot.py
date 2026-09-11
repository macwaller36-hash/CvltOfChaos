import importlib.util
import pathlib
import sys
import unittest
from unittest.mock import patch
from types import SimpleNamespace

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

spec = importlib.util.spec_from_file_location("bot_module", ROOT / "bot.py")
bot_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bot_module)


class BotScaffoldTests(unittest.TestCase):
    def test_bot_module_loads(self):
        self.assertTrue(hasattr(bot_module, "bot"))
        self.assertTrue(hasattr(bot_module, "main"))

    def test_ping_command_exists(self):
        self.assertIn("ping", bot_module.bot.all_commands)
        self.assertIn("8ball", bot_module.bot.all_commands)
        self.assertIn("coinflip", bot_module.bot.all_commands)
        self.assertIn("roll", bot_module.bot.all_commands)
        self.assertIn("choose", bot_module.bot.all_commands)
        self.assertIn("rps", bot_module.bot.all_commands)
        self.assertIn("blackjack", bot_module.bot.all_commands)
        self.assertIn("coins", bot_module.bot.all_commands)
        self.assertIn("slot", bot_module.bot.all_commands)
        self.assertIn("roulette", bot_module.bot.all_commands)
        self.assertIn("send", bot_module.bot.all_commands)

    def test_blackjack_total_handles_aces(self):
        self.assertEqual(bot_module.get_blackjack_total(["A", "K"]), 21)
        self.assertEqual(bot_module.get_blackjack_total(["A", "9", "A"]), 21)
        self.assertEqual(bot_module.get_blackjack_total(["A", "9", "A", "5"]), 16)

    def test_rps_round_supports_forced_user_win(self):
        with patch.object(bot_module.random, "random", return_value=0.1):
            bot_pick, result = bot_module.get_rps_round("rock")
        self.assertEqual(bot_pick, "scissors")
        self.assertEqual(result, "You win.")

    def test_rps_round_supports_forced_bot_win(self):
        with patch.object(bot_module.random, "random", return_value=0.9):
            bot_pick, result = bot_module.get_rps_round("rock")
        self.assertEqual(bot_pick, "paper")
        self.assertEqual(result, "You lose.")

    def test_slot_multiplier_rules(self):
        self.assertEqual(bot_module.get_slot_multiplier(["🍒", "🍒", "🍒"]), 5)
        self.assertEqual(bot_module.get_slot_multiplier(["🍒", "🍒", "🍋"]), 2)
        self.assertEqual(bot_module.get_slot_multiplier(["🍒", "🍋", "⭐"]), 0)

    def test_roulette_color_mapping(self):
        self.assertEqual(bot_module.get_roulette_color(0), "green")
        self.assertEqual(bot_module.get_roulette_color(1), "red")
        self.assertEqual(bot_module.get_roulette_color(2), "black")

    def test_parse_bet_supports_all_and_limits(self):
        user_id = 777
        bot_module.coin_balances.clear()
        bot_module.set_balance(user_id, 120)
        self.assertEqual(bot_module.parse_bet("all", user_id), 120)
        self.assertEqual(bot_module.parse_bet("max", user_id), 120)
        self.assertEqual(bot_module.parse_bet("50", user_id), 50)
        self.assertIsNone(bot_module.parse_bet("500", user_id))
        self.assertIsNone(bot_module.parse_bet("zero", user_id))

    def test_dm_intro_lists_supported_options(self):
        text = bot_module.get_dm_intro_text().lower()
        for option in ("support", "issue", "suggestion", "application", "partnership"):
            self.assertIn(option, text)

    def test_message_only_mode_enabled(self):
        self.assertTrue(bot_module.MESSAGE_ONLY_MODE)

    def test_category_detection(self):
        self.assertEqual(bot_module.get_category("application"), "Application")
        self.assertEqual(bot_module.get_category("partnership"), "Partnership")
        self.assertEqual(bot_module.get_category("support"), "Support")
        self.assertIsNone(bot_module.get_category("random"))

    def test_hi_greeting_detection(self):
        self.assertTrue(bot_module.should_reply_with_hey("hi"))
        self.assertTrue(bot_module.should_reply_with_hey("  HI  "))
        self.assertFalse(bot_module.should_reply_with_hey("this is hidden"))

    def test_cheeseburger_noise_detection(self):
        self.assertTrue(bot_module.should_play_cheeseburger_noise("cheese burger"))
        self.assertTrue(bot_module.should_play_cheeseburger_noise("I want a cheeseburger"))
        self.assertFalse(bot_module.should_play_cheeseburger_noise("burger only"))

    def test_staff_proxy_message_parsing(self):
        self.assertEqual(bot_module.get_staff_proxy_message(".suppp"), "suppp")
        self.assertEqual(bot_module.get_staff_proxy_message(". hello there"), "hello there")
        self.assertIsNone(bot_module.get_staff_proxy_message("."))
        self.assertIsNone(bot_module.get_staff_proxy_message("hello"))

    def test_command_prefix_detection(self):
        self.assertTrue(bot_module.has_command_prefix("!ping"))
        self.assertTrue(bot_module.has_command_prefix("c!send hello"))
        self.assertFalse(bot_module.has_command_prefix(".hello"))

    def test_explicit_staff_user_id_is_allowed(self):
        member = SimpleNamespace(
            id=1322411501381877872,
            guild_permissions=SimpleNamespace(manage_messages=False),
            roles=[],
        )
        self.assertTrue(bot_module.is_staff(member))

    def test_manage_messages_is_staff_even_with_role_list_configured(self):
        original_role_ids = bot_module.STAFF_ROLE_IDS
        try:
            bot_module.STAFF_ROLE_IDS = [999999999999999999]
            member = SimpleNamespace(
                id=555555555555555555,
                guild_permissions=SimpleNamespace(manage_messages=True),
                roles=[],
            )
            self.assertTrue(bot_module.is_staff(member))
        finally:
            bot_module.STAFF_ROLE_IDS = original_role_ids


if __name__ == "__main__":
    unittest.main()
