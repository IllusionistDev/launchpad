FROM python:3.9-slim-buster

ENV PYTHONUNBUFFERED 1
ENV APP /launchpad

# Install system requirements
RUN apt-get update -y && \
    apt-get upgrade -y && \
    # Global requirements
    apt-get install -y build-essential \
    git gcc gfortran curl python3-pip libpq-dev python3-tk \
    libffi-dev libxslt-dev python3-dev python3-setuptools netcat --fix-missing

RUN mkdir $APP
WORKDIR $APP

ADD launchpad/ $APP

RUN pip install --disable-pip-version-check --exists-action w -r requirements.txt
