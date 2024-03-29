"""
Configuration for the distribution network
Edit and restart to update.
"""

import os
import logging
import subprocess

# Statement for enabling the development environment
DEBUG = True
LOGLEVEL = logging.DEBUG

# set time to wait for other services
DNET_STARTUP_TIME = 0

# extract HOST_IP
try:
    proc = subprocess.Popen("hostname -I | cut -d' ' -f1", shell=True, stdout=subprocess.PIPE)
    DNET_DOCKER_HOST_IP = proc.communicate()[0].decode().strip()
except:
    DNET_DOCKER_HOST_IP = "127.0.0.1"

# Define the database - we are working with
# Set up SQLAlchemy
# SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://iot4cps:iot4cps@localhost/iot4cps'
POSTGRES_HOST = "localhost"
POSTGRES_PORT = "5432"
POSTGRES_USER = "postgres"
POSTGRES_PASSWORD = "postgres"
# DNET_DOCKER_HOST_IP = "localhost"
DNET_SQLALCHEMY_DATABASE_DRIVER = "postgresql+psycopg2"
DNET_SQLALCHEMY_DATABASE_NAME = "distributionnetworkdb"

SQLALCHEMY_TRACK_MODIFICATIONS = False
DB_INSERT_SAMPLE = True

# Secret key for signing cookies
SECRET_KEY = "changeme"

# Bootstrap servers for Kafka: get ip of the local machine, only the first one listed will be used
# HOST_IP = "127.0.0.1"  # in the current setup, localhost should be preferred
DNET_KAFKA_BOOTSTRAP_SERVER = f"{DNET_DOCKER_HOST_IP}:9092,{DNET_DOCKER_HOST_IP}:9093,{DNET_DOCKER_HOST_IP}:9094"
# DNET_KAFKA_BOOTSTRAP_SERVER = "kafka1:19092,kafka2:19093,kafka3:19094"  # will be overwritten by docker-compose envs

DNET_IASSET_SERVER = "https://iasset.salzburgresearch.at"
DNET_IDENTITY_SERVICE = "https://iasset.salzburgresearch.at/identity"

# "https://raw.githubusercontent.com/annexare/Countries/27bdd120d5e928a5683d26c95795459c7ee6fefc/data/countries.json",
# "This must be consistent with the frontend's https://www.npmjs.com/package/countries-list, currently version 2.4.3",
COUNTRY_CODES_URL = "https://github.com/annexare/Countries/blob/4e72556dbbbf8f0e31b2ddd2b0e30b3c2d697805/data/countries.json"

SOURCE_URL = "https://github.com/i-Asset/distribution-network"
