from conversation import Conversation


class TestAppend:
    def test_append_turns(self):
        c = Conversation()
        c.add_user("hi")
        c.add_assistant("hello")
        assert c.messages == [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]

    def test_len(self):
        c = Conversation()
        c.add_user("a")
        c.add_assistant("b")
        assert len(c) == 2


class TestTrim:
    def test_trims_to_char_budget_keeping_recent(self):
        c = Conversation(max_chars=20)
        c.add_user("1111111111")   # 10
        c.add_assistant("2222222222")  # 10
        c.add_user("3333333333")   # 10 -> total would be 30, must drop oldest
        # oldest ("1111111111") dropped to fit budget
        contents = [m["content"] for m in c.messages]
        assert "1111111111" not in contents
        assert "3333333333" in contents
        assert sum(len(m["content"]) for m in c.messages) <= 20

    def test_never_empties_when_last_message_over_budget(self):
        c = Conversation(max_chars=5)
        c.add_user("this is a very long message exceeding budget")
        assert len(c) == 1  # keeps at least the most recent


class TestRender:
    def test_render_includes_roles_and_content(self):
        c = Conversation()
        c.add_user("What is X?")
        c.add_assistant("X is a thing.")
        rendered = c.render()
        assert "What is X?" in rendered
        assert "X is a thing." in rendered

    def test_render_empty(self):
        assert Conversation().render() == ""

    def test_as_list_returns_copy(self):
        c = Conversation()
        c.add_user("a")
        lst = c.as_list()
        lst.append({"role": "user", "content": "mutation"})
        assert len(c) == 1  # internal state unchanged


class TestReset:
    def test_reset_clears(self):
        c = Conversation()
        c.add_user("a")
        c.reset()
        assert len(c) == 0
