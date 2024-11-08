FROM ubuntu:latest
LABEL authors="gabriel.cerioni"

ENTRYPOINT ["top", "-b"]