import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "bot.py"

spec = importlib.util.spec_from_file_location("bot_module", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_dm_prompt_is_only_requested_once_per_user():
    pending = set()

    assert module.should_prompt_for_ticket_details(42, pending) is True
    module.mark_dm_prompt_seen(42, pending)
    assert module.should_prompt_for_ticket_details(42, pending) is False


def test_followup_message_after_prompt_is_treated_as_ticket_body():
    pending = {42}

    assert module.should_use_followup_as_ticket_body(42, pending) is True
    module.clear_dm_prompt(42, pending)
    assert module.should_use_followup_as_ticket_body(42, pending) is False
