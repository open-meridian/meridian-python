# The plugin's image, built on the base image for the SDK this plugin pins.
ARG BASE=ghcr.io/open-meridian/plugin-python:0.35.0
FROM ${BASE}
WORKDIR /plugin
RUN --mount=type=bind,target=/tmp/src,rw pip install --no-cache-dir /tmp/src
USER 65532
