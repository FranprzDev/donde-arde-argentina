"""Readability rules, enforced in code. A build FAILS (ReadabilityError) when any of these is broken:

  1. min_font_px        every font requested while rendering is >= this size (design px at 1080p). Checked by
                        Theme.font() on every frame, and statically for each beat's declared sizes.
  2. max_words_per_beat the words on screen at the same moment within one beat (overlapping text blocks add up)
                        are <= this.
  3. hold time          each text block stays on screen >= max(min_hold, sec_per_word * words + base_hold)
                        (default 0.35 s/word + 1 s, never under 2.5 s).
  4. max_duration       the whole video is <= video.max_duration seconds.

Words are counted as whitespace-separated tokens with at least one letter or digit ("·", "=", "%" alone do not
count; "12,5" counts as one word). Beats of type `sources` are exempt from 2 and 3 (they are a credits card meant to
be paused) but not from 1."""
from dataclasses import dataclass, field

from .errors import ReadabilityError

DEFAULTS = dict(min_font_px=48, max_words_per_beat=12, sec_per_word=0.35, base_hold=1.0, min_hold=2.5)


def words(s):
    return len([w for w in str(s).replace("·", " ").replace("=", " ").split() if any(ch.isalnum() for ch in w)])


@dataclass
class TextBlock:
    lines: list
    t0: float
    t1: float
    beat: str = ""
    count: bool = True               # False for labels that are not read as prose (axis years, legends)
    sizes: list = field(default_factory=list)

    @property
    def nwords(self):
        return sum(words(x) for x in self.lines) if self.count else 0


class Rules:
    def __init__(self, cfg=None):
        c = dict(DEFAULTS); c.update(cfg or {})
        self.__dict__.update(c)

    def need(self, n_words):
        return max(self.min_hold, self.sec_per_word * n_words + self.base_hold)

    def check(self, beats, total, max_duration, tol=0.01):
        probs = []
        for b in beats:
            if b.exempt_readability:
                for blk in b.blocks:
                    for s in blk.sizes:
                        if s < self.min_font_px:
                            probs.append(f"beat '{b.id}': text size {s}px < min {self.min_font_px}px")
                continue
            nw = self.max_words_at_once(b)
            if nw > self.max_words_per_beat:
                probs.append(f"beat '{b.id}' ({b.type}): {nw} words on screen > max {self.max_words_per_beat}. "
                             f"Cut words or split it into two beats: {[l for blk in b.blocks for l in blk.lines]}")
            for blk in b.blocks:
                for s in blk.sizes:
                    if s < self.min_font_px:
                        probs.append(f"beat '{b.id}': text size {s}px < min {self.min_font_px}px")
                if not blk.count:
                    continue
                hold = blk.t1 - blk.t0; need = self.need(blk.nwords)
                if hold + tol < need:
                    probs.append(f"beat '{b.id}': {blk.lines} is on screen {hold:.2f}s but needs {need:.2f}s "
                                 f"({blk.nwords} words x {self.sec_per_word}s + {self.base_hold}s, min {self.min_hold}s). "
                                 f"Make the beat longer (duration: auto) or use fewer words.")
        if total > max_duration + 1e-6:
            probs.append(f"total duration {total:.2f}s > max {max_duration}s. Remove a beat or words; do not speed up text.")
        if probs:
            raise ReadabilityError(probs)

    @staticmethod
    def max_words_at_once(b):
        """most words of this beat visible at the same moment (blocks that overlap in time add up)"""
        best = 0
        for blk in b.blocks:
            if blk.t0 is None:
                continue
            best = max(best, sum(o.nwords for o in b.blocks if o.t0 is not None and o.t0 <= blk.t0 < o.t1))
        return best

    def report_rows(self, beats):
        rows = []
        for b in beats:
            for blk in b.blocks:
                need = self.need(blk.nwords) if (blk.count and not b.exempt_readability) else None
                rows.append(dict(beat=b.id, type=b.type, start=b.start, end=b.end, text=" / ".join(blk.lines), words=blk.nwords,
                                 t0=blk.t0, t1=blk.t1, hold=blk.t1 - blk.t0, need=need,
                                 ok=(need is None or blk.t1 - blk.t0 + 0.01 >= need)))
            if not b.blocks:
                rows.append(dict(beat=b.id, type=b.type, start=b.start, end=b.end, text="—", words=0, t0=None, t1=None,
                                 hold=None, need=None, ok=True))
        return rows
