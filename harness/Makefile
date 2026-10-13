# make video STORY=stories/sismos-argentina/story.yaml   (WORKERS=4, PREVIEW=1 for half size)
PY ?= python3
STORY ?= stories/sismos-argentina/story.yaml
WORKERS ?=
PREVIEW ?=
_W := $(if $(WORKERS),--workers $(WORKERS),)
_P := $(if $(PREVIEW),--preview,)

.PHONY: video check qa facts new test beats clean
video:
	$(PY) -m harness render $(STORY) $(_W) $(_P)
check:
	$(PY) -m harness check $(STORY)
qa:
	$(PY) -m harness qa $(STORY) $(_P)
facts:
	$(PY) -m harness facts $(STORY)
new:
	$(PY) -m harness new "$(NAME)"
beats:
	$(PY) -m harness beats
test:
	$(PY) -m pytest -q
clean:
	rm -rf $(dir $(STORY))build
