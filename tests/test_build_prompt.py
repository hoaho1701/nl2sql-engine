"""Tests for build_prompt's build_messages()."""

from app.build_prompt import build_messages


def test_returns_exactly_two_messages():
    messages = build_messages("How many orders?", "some context")
    assert len(messages) == 2


def test_first_message_is_system_role():
    messages = build_messages("How many orders?", "some context")
    assert messages[0]["role"] == "system"


def test_second_message_is_user_role_with_the_question():
    messages = build_messages("How many orders?", "some context")
    assert messages[1] == {"role": "user", "content": "How many orders?"}


def test_context_is_included_in_system_message():
    context = "Table orders: order_status is one of approved, canceled..."
    messages = build_messages("How many orders?", context)
    assert context in messages[0]["content"]


def test_system_message_instructs_raw_sql_only():
    messages = build_messages("How many orders?", "some context")
    assert "raw SQL" in messages[0]["content"]
