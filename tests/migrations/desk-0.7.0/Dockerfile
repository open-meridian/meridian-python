# The plugin's image, built on the base image for the SDK this plugin pins.
ARG BASE=ghcr.io/open-meridian/plugin-python:0.7.0
FROM ${BASE}
WORKDIR /plugin
COPY . .
RUN pip install .
USER 65532
CMD ["desk"]
