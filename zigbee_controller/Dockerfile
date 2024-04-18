FROM python:slim

ENV CONTAINER_HOME=/app

WORKDIR $CONTAINER_HOME
ADD requirements.txt $CONTAINER_HOME

RUN apt-get update -y && apt-get install -y gcc build-essential

RUN pip install --no-cache --upgrade pip setuptools
RUN pip install --no-cache-dir -r requirements.txt
