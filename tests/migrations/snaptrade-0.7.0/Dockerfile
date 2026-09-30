# The plugin's image, built on the base image for the SDK this plugin pins.
#
# BASE is for building against a base made locally rather than a released one.
ARG BASE=ghcr.io/open-meridian/plugin-python:0.7.0
FROM ${BASE}
WORKDIR /plugin
# Installed from a mount rather than copied, so the image holds the installed
# package and no source beside it.
RUN --mount=type=bind,target=/tmp/src,rw pip install --no-cache-dir /tmp/src
USER 65532
CMD ["snaptrade"]
