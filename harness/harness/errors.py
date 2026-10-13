"""Errors raised by the harness. Every failure that should stop a build is one of these, with a message a human (or an
agent) can act on without reading the code."""


class HarnessError(Exception):
    """Base class: the build stops and the message is printed as-is."""


class StoryError(HarnessError):
    """story.yaml is malformed or references something that does not exist."""


class FactsError(HarnessError):
    """A fact could not be computed, an assert failed, or a number on screen is not backed by facts.json."""


class ReadabilityError(HarnessError):
    """A readability rule was broken (font too small, too many words, text not held long enough, video too long)."""

    def __init__(self, problems):
        self.problems = list(problems) if isinstance(problems, (list, tuple)) else [problems]
        msg = "Readability rules failed:\n" + "\n".join(f"  - {p}" for p in self.problems)
        super().__init__(msg)
