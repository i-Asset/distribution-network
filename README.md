# Distribution Network
A layer for easy and structured real-time data exchange between assets.


## Contents

1. [Requirements](#requirements)
1. [Setup](#setup)
   1. [Setup Messaging Layer](#setup-messaging-layer)
   1. [Setup Database](#setup-database)
   1. [Setup Distribution Service](#setup-distribution-service)
1. [Platform UI](#platform-ui)


## Requirements
The setup is based on the following requirements:

* Install [Docker](https://www.docker.com/community-edition#/download) version **1.10.0+** 
* Install [Docker Compose](https://docs.docker.com/compose/install/) version **1.6.0+** 
* Clone this Repository:

    ```bash
    git clone https://github.com/i-Asset/distribution-network.git
    cd distribution-network
    git checkout staging
    ```

## Setup

### Setup Messaging Layer

[Apache Kafka](https://kafka.apache.org/) is used as Core delivery framework.
The easiest way to set up a Kafka cluster, is with Docker Compose.

```bash
docker-compose -f setup/kafka/docker-compose.yml up --build -d
docker-compose -f setup/kafka/docker-compose.yml ps  # for stati of the services
docker-compose -f setup/kafka/docker-compose.yml logs -f  # for continuous logs
docker-compose -f setup/kafka/docker-compose.yml down  # shut down the cluster, remove data with -v flag
```

To test the Kafka setup, list, create and delete topics, Kafka binaries are required 
(see the next subsection [(optional) Install Kafka binaries](#optional-install-kafka-binaries) for that).
For information to set up a Kafka cluster on multiple nodes without Docker (which is suggested)
for production, check [this](https://github.com/iot-salzburg/panta_rhei/blob/master/setup/README-Deployment.md) guide.


### (optional) Install Kafka binaries

This step is only required for developing the Distribution Network, because the service is
run on the host. For the productive mode, the service runs within a Docker container and
therefore doesn't need Kafka binaries on the host. It is also important to note, 
that it is hard to install Kafka on Windows. 

The following lines installs Kafka version 2.7 locally in the directory `/kafka`:

```bash
sudo apt-get update
sh setup/kafka/install-kafka.sh
sh setup/kafka/install-kafka-libs.sh
```

With the Kafka binaries topics can be listed, created and deleted. Moreover, messages can 
be produced and consumed.

```bash
/kafka/bin/kafka-topics.sh --zookeeper :2181 --list
/kafka/bin/kafka-topics.sh --zookeeper :2181 --create --topic test_single --replication-factor 1 --partitions 1
/kafka/bin/kafka-topics.sh --zookeeper :2181 --create --topic test --replication-factor 3 --partitions 3 --config cleanup.policy=compact --config retention.ms=3628800000 --config retention.bytes=-1
/kafka/bin/kafka-topics.sh --zookeeper :2181 --delete --topic test_single
/kafka/bin/kafka-topics.sh --zookeeper :2181 --list

/kafka/bin/kafka-console-producer.sh --broker-list :9092 --topic test
>Hello Kafka
> [Ctrl]+C
/kafka/bin/kafka-console-consumer.sh --bootstrap-server :9092 --topic test --from-beginning
Hello Kafka
```


### Setup Database

[PostgreSQL](https://www.postgresql.org/) is used as relational database for static data within
the Distribution Network.

#### Option 1: Docker

The easiest way to setup PostgreSQL is via Docker Compose:

```bash
docker-compose -f setup/postgresql/docker-compose.yml up --build -d
docker-compose -f setup/postgresql/docker-compose.yml ps  # status of postgres
docker-compose -f setup/postgresql/docker-compose.yml logs -f  # for continuous logs
docker-compose -f setup/postgresql/docker-compose.yml down  # shut down, remove data with -v flag
```

#### Option 2: On the Host
As an alternative, e.g., one can also setup postgreSQL directly on the host.
There are various instructions on how to install postgres, this one works for Ubuntu 20.04:

```bash
sudo apt install libpq-dev
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt-get update
sudo apt-get install postgresql

sudo -u postgres psql -c "CREATE ROLE postgres LOGIN PASSWORD 'postgres';"
sudo -u postgres psql -c "CREATE DATABASE distributionnetworkdb OWNER postgres;"
sudo -u postgres psql -f setup/postgresql/initdb/db_init.sql
```

#### Create Database

The database `distributionnetworkdb` is created and filled with demo-data automatically 
with the startup, as configured in `setup/postgresql/initdb/db_init.sql`. 
Check the entries in the tables using commands like:

```bash
docker exec -it postgresql_postgresdb_1 psql -U postgres -d distributionnetworkdb -c "select * from users;"
```

Note that dummy users and companies have negative ids, real entries have always non-negative entries.


### Setup Distribution Service

The Distribution Service depends can be set up either on the host (preferred for development) 
or within a Docker container (easier to set up). Select the appropriate option below.

In both cases, the **Distribution Service** depends on the Delivery Framework Apache Kafka
and the Database Postgres. 
The respective dependency-variables have to be valid and are required to set up the 
**Distribution Service**.


#### Option 1: Setup Distribution Service on Docker

```bash
docker-compose -f server/docker-compose.yml up --build -d
```

#### Option 2: Setup Distribution Service on Host

Make sure to start a new virtual env for this setup! Then, install the python modules via:

```bash
virtualenv --python=/path/to/python /path/to/new/venv
source /path/to/new/venv/bin/activate  # e.g. /home/chris/anaconda3/envs/venv_iot4cps/bin/activate
pip install -r setup/requirements.txt
```

