IMAGE ?= snaptrade:local
BASE  ?= ghcr.io/open-meridian/plugin-python:0.6.1

image:
	docker build --build-arg BASE=$(BASE) -t $(IMAGE) .
