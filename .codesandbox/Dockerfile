FROM python:3.10.12

RUN apt-get update && apt-get install -y npm fish graphviz && \
    pip install -U pip && \
    pip install poetry && \
    poetry config virtualenvs.create false && \
    chsh -s /usr/bin/fish
