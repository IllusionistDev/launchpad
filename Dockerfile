FROM python:3.8-slim-buster

ENV PYTHONUNBUFFERED 1
ENV APP /launchpad

# Install system requirements
RUN apt-get update -y && \
    apt-get upgrade -y && \
    apt install -y libpq-dev gcc python3-dev build-essential g++ procps --fix-missing \
    && pip install --upgrade pip \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir $APP
WORKDIR $APP

ADD launchpad/ $APP

RUN pip install --disable-pip-version-check --exists-action w -r requirements/core.txt -r requirements/dev.txt
