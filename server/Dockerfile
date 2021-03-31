FROM python:3.6
# not using onbuild, because changed code results in installation time

MAINTAINER Christoph Schranz <christoph.schranz@salzburgresearch.at>

# test internet connection and dns settings. If apt-get update fails, restart
# docker service, check internet connection and dns settings in /etc/docker/daemon.json
#RUN apt-get update

# install the official librdkafka client written in C
ENV LIBRDKAFKA_VERSION 0.11.1
RUN apt-get update && \
    git clone https://github.com/edenhill/librdkafka && cd librdkafka && \
    git checkout v${LIBRDKAFKA_VERSION} && \
    ./configure && make && make install && ldconfig

# install confluent-kafka-client
ENV CONFLUENT_KAFKA_VERSION 0.11.5
RUN pip install confluent-kafka==${CONFLUENT_KAFKA_VERSION}

# First, only copy the requirements and install them, to avoid reinstallation on changed config files
ADD requirements.txt .
RUN pip install -r requirements.txt

# Copy the content of this folder into the hosts home directory
RUN mkdir -p /src/server
ADD . /src/server

# load the docker-compose environment variables to the container environment
RUN export $(cat Dockerfile.env | xargs)
ARG IASSET_SERVER
ENV IASSET_SERVER $IASSET_SERVER
ARG SQLALCHEMY_DATABASE_URI
ENV SQLALCHEMY_DATABASE_URI $SQLALCHEMY_DATABASE_URI
ARG KAFKA_BOOTSTRAP_SERVER
ENV KAFKA_BOOTSTRAP_SERVER $KAFKA_BOOTSTRAP_SERVER

# set configuration file
RUN echo "\nAPP_CONFIG_FILE=config/docker.py" >> /src/server/.env

# set environment
ENV PYTHONPATH /src/server
WORKDIR /src/server
ENV FLASK_APP=/src/server/app.py

EXPOSE 1908
CMD ["flask", "run", "-h", "0.0.0.0", "-p", "1908"]
