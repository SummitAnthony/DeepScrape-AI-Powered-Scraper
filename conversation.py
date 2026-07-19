"""Multi-turn conversation memory with a character budget, for stateful AI chats."""

DEFAULT_MAX_CHARS = 12000


class Conversation:
    """Holds an ordered list of {role, content} turns, trimmed to a char budget.
    Oldest turns are dropped first; the most recent turn is always kept."""

    def __init__(self, max_chars=DEFAULT_MAX_CHARS):
        self.max_chars = max_chars
        self.messages = []

    def add_user(self, content):
        self._add("user", content)

    def add_assistant(self, content):
        self._add("assistant", content)

    def _add(self, role, content):
        self.messages.append({"role": role, "content": content})
        self._trim()

    def _trim(self):
        total = sum(len(m["content"]) for m in self.messages)
        # Drop oldest until within budget, but always keep the most recent turn.
        while total > self.max_chars and len(self.messages) > 1:
            removed = self.messages.pop(0)
            total -= len(removed["content"])

    def render(self):
        """Render turns as 'role: content' lines for inclusion in a prompt."""
        return "\n".join(f"{m['role']}: {m['content']}" for m in self.messages)

    def as_list(self):
        """Return a shallow copy of the message list (safe to mutate)."""
        return list(self.messages)

    def reset(self):
        self.messages = []

    def __len__(self):
        return len(self.messages)
