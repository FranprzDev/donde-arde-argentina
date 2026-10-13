"""Beat registry. Import a module here to make its @register-ed beat types available to story.yaml."""
from ..errors import StoryError
from .base import REGISTRY, Beat, register  # noqa: F401
from . import globe_intro, timeline, cards, ranking, imagery  # noqa: F401


def make_beat(story, cfg, index):
    t = cfg["type"]
    if t not in REGISTRY:
        raise StoryError(f"beat #{index + 1}: unknown type '{t}'. Available: {sorted(REGISTRY)}")
    return REGISTRY[t](story, cfg, index)
