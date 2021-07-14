# Distribution Network
A layer for easy and structured real-time data exchange between assets.


## Contents

1. [Requirements](#requirements)
1. [Setup](#setup)
   1. [Setup Messaging Layer](#setup-messaging-layer)
   1. [Setup Database](#setup-database)
   1. [Setup Distribution Service](#setup-distribution-service)
1. [Usage](#usage)
   1. [Platform UI](#platform-ui)
   1. [RestAPI](#restapi)

<br>

___

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

<br>

___

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

Make sure `postgres` is available on port `5432` and `postgres` is the owner of the database `distributionnetworkdb`.
```bash
docker-compose -f /server/postgresql/docker-compose.yml up --build -d
```

Then set the environment variable `DOCKER_HOST_IP` and start the main docker compose:

```bash
export DOCKER_HOST_IP=$(hostname -I | cut -d ' ' -f1)
echo $DOCKER_HOST_IP
docker-compose up --build -d
```

Check if everything works using:
```bash
docker ps
docker-compose logs -f
docker-compose logs -f distribution-network
docker inspect distribution-network_distribution-network_1
```


#### Option 2: Setup Distribution Service on Host

Make sure to start a new virtual env for this setup! Then, install the python modules via:

```bash
virtualenv --python=/path/to/python /path/to/new/venv
source /path/to/new/venv/bin/activate  # e.g. /home/chris/anaconda3/envs/venv_iot4cps/bin/activate
pip install -r setup/requirements.txt
```

Additionally, a running Kafka instance is required, e.g.:
```bash
export DOCKER_HOST_IP=$(hostname -I | cut -d ' ' -f1)
echo $DOCKER_HOST_IP
docker-compose -f /server/kafka/docker-compose.yml up --build -d
```

Make sure that the file `server/.env` directs to the correct configuration set, that is 
either `development`, `production`, `docker` or `platform-only` (that doesn't interact with the
Kafka data streaming).
The platform can be started by running:
```bash
export FLASK_APP=$(pwd)/server/app.py
echo $FLASK_APP
python -m flask run --host $(hostname -I | cut -d " " -f1) --port 1908
```

<br>

___

## Usage

### Platform UI

One easy way to check the platform is via the light-weight user interface that comes with the *distribution-network*:

![platform_ui](https://github.com/i-Asset/distribution-network/blob/master/server/extra/platform_ui.png)


### RestAPI

The RestAPI is the preferred user interface and is documented in swagger on 
[server/distributionnetwork/swagger-ui.html](http://localhost:1908/distributionnetwork/swagger-ui.html).


![swagger_ui](https://github.com/i-Asset/distribution-network/blob/master/server/extra/swagger_ui.png)


### Distribution Network - Connection Tester

Execute without parameters and authorization.



### System Requests

#### Create a System (POST or PUT)

Creates the specified system with dependencies and Kafka Topics. Requires that the user and company
exist. In contrast to POST, the PUT method allows an edit of the system.

**i-Asset Server:**

```
453
[bearer-token]

{
    "company_id": 455,
    "description": "Lorem ipsum dolor sit amet, consectetuer adipiscing elit. Aenean commodo ligula eget dolor. \n    Aenean massa. Cum sociis natoque penatibus et magnis dis parturient montes, nascetur ridiculus mus. Donec \n    quam felis, ultricies nec, pellentesque eu, pretium quis, sem. Nulla consequat massa quis enim.",
    "kafka_servers": "localhost:9092",
    "mqtt_broker": {
        "mqtt_server": "mqtt.eclipse.org:1883",
        "mqtt_version": ""
    },
    "workcenter": "labor",
    "station": "testStation"
}
```

```
curl -X POST "https://iasset.salzburgresearch.at/distributionnetwork/systems_by_person/453" -H  "accept: application/json" -H  "Authorization: [bearer-token]" -H  "Content-Type: application/json" -d "{    \"company_id\": 455,    \"description\": \"Lorem ipsum dolor sit amet, consectetuer adipiscing elit. Aenean commodo ligula eget dolor. \    Aenean massa. Cum sociis natoque penatibus et magnis dis parturient montes, nascetur ridiculus mus. Donec \    quam felis, ultricies nec, pellentesque eu, pretium quis, sem. Nulla consequat massa quis enim.\",    \"kafka_servers\": \"localhost:9092\",    \"mqtt_broker\": {        \"mqtt_server\": \"mqtt.eclipse.org:1883\",        \"mqtt_version\": \"\"    },    \"workcenter\": \"labor\",    \"station\": \"testStation\"}"
```

#### Get all Systems (GET)

Get systems by `user_id` and `password` (= `personId` and `bearer_token`)

**Local:**
```
curl -X GET --header 'Accept: application/json'  --header 'Authorization: asdf' 'localhost:1908/distributionnetwork/systems_by_person/-1'
```
or as Python request:
```python
import requests

res = requests.get(url="http://localhost:1908/distributionnetwork/systems_by_person/-2",
            headers={'content-type': 'application/json',
                     'Authorization': "asdf"})
status_code = res.status_code
result = res.json()
```

**i-Asset Server:**

```yaml
persionId = 453
[bearer-token]
```
```
curl -X GET "https://iasset.salzburgresearch.at/distributionnetwork/systems_by_person/453" -H  "accept: application/json" -H  "Authorization: [bearer-token]"
```

#### Delete a System (DELETE)

Get systems by `user_id` and `password` (= `personId` and `bearer_token`)

**i-Asset Server:**

```yaml
persionId = 453
system = ee_455_labor_testStation
[bearer-token]
```
```
curl -X DELETE "https://iasset.salzburgresearch.at/distributionnetwork/delete_system/453/ee.455.puch.testStation" -H  "accept: application/json" -H  "Authorization: [bearer-token]"
```



### Client Applications

#### Get all Client Apps of a system 

Requires `user_id`, `system_name` and `password` (= `personId` and `bearer_token`) in the header as Python request:

**i-Asset Server:**

```yaml
persionId = 453
system = ee_455_labor_testStation
[bearer-token]
```
```
curl -X GET "https://iasset.salzburgresearch.at/distributionnetwork/client_apps/453/ee_455_labor_testStation" -H  "accept: application/json" -H  "Authorization: [bearer-token]"
```

#### Create a Client App for a System

Creates a Client App for a specified system. Requires that the user and system exist.

**i-Asset Server:**

```yaml
persionId = 453
system = ee_455_labor_testStation
[bearer-token]

{
    "name": "client_app_1",
    "resource_uri": "https://iasset.salzburgresearch.at/registry/sec_uuid",
    "on_kafka": true,
    "description": "Lorem ipsum dolor sit amet, consectetuer adipiscing elit."
}
```
```bash
curl -X POST "https://iasset.salzburgresearch.at/distributionnetwork/client_apps/453/ee_455_labor_testStation" -H  "accept: application/json" -H  "Authorization: [bearer-token]" -H  "Content-Type: application/json" -d "{    \"name\": \"client_app_1\",    \"resource_uri\": \"https://iasset.salzburgresearch.at/registry/sec_uuid\",    \"on_kafka\": true,    \"description\": \"Lorem ipsum dolor sit amet, consectetuer adipiscing elit.\"}"
```

#### Get a specific Client App by system name and client name

Requires `user_id`, `system_name`, `client_name` and `password` (= `personId` and `bearer_token`) 
in the header. The `system_name` should use `_` as level separator.

**i-Asset Server:**

```yaml
persionId = 453
system = ee_455_labor_testStation
client_name = client_app_1
[bearer-token]
```
```
curl -X GET "https://iasset.salzburgresearch.at/distributionnetwork/client_apps/453/ee_455_labor_testStation/client_app_1" -H  "accept: application/json" -H  "Authorization: [bearer-token]"
```

#### Delete a Client App 

Deletes the specified Client App within a system.
Requires `user_id`, `system_name`, `client_name` and `password` (= `personId` and `bearer_token`) 
in the header. The `system_name` should use `_` as level separator.

**i-Asset Server:**

```yaml
persionId = 453
system = ee_455_labor_testStation
client_name = client_app_1
[bearer-token]
```
```
curl -X DELETE "https://iasset.salzburgresearch.at/distributionnetwork/delete_client_app/453/ee_455_labor_testStation/client_app_1" -H  "accept: application/json" -H  "Authorization: [bearer-token]"
```



### Thing Connections

A Thing connection is a digital instance that connects the distribution network with a metadata resource of that thing.

#### Get all Things Connections of a system 

Requires `user_id`, `system_name` and `password` (= `personId` and `bearer_token`) in the header as Python request:

**i-Asset Server:**

```yaml
persionId = 453
system = ee_455_labor_testStation
[bearer-token]
```
```
curl -X GET "https://iasset.salzburgresearch.at/distributionnetwork/things/453/ee_455_labor_testStation" -H  "accept: application/json" -H  "Authorization: [bearer-token]"
```

#### Create a Thing Connections for a System

Creates a Thing Connection for a specified system. Requires that the user and system exist.

**i-Asset Server:**

```yaml
persionId = 453
system = ee_455_labor_testStation
[bearer-token]

{
    "name": "thing_1",
    "resource_uri": "https://iasset.salzburgresearch.at/registry/sec_uuid",
    "on_kafka": true,
    "description": "Lorem ipsum dolor sit amet, consectetuer adipiscing elit."
}
```
```bash
curl -X POST "https://iasset.salzburgresearch.at/distributionnetwork/things/453/ee_455_labor_testStation" -H  "accept: application/json" -H  "Authorization: [bearer-token]" -H  "Content-Type: application/json" -d "{    \"name\": \"thing_1\",    \"resource_uri\": \"https://iasset.salzburgresearch.at/registry/sec_uuid\",    \"on_kafka\": true,    \"description\": \"Lorem ipsum dolor sit amet, consectetuer adipiscing elit.\"}"
```

#### Get a specific Thing Connection by system name and thing name

Requires `user_id`, `system_name`, `thing_name` and `password` (= `personId` and `bearer_token`) 
in the header. The `system_name` should use `_` as level separator.

**i-Asset Server:**

```yaml
persionId = 453
system = ee_455_labor_testStation
thing_name = thing_1
[bearer-token]
```
```
curl -X GET "https://iasset.salzburgresearch.at/distributionnetwork/things/453/ee_455_labor_testStation/thing_1" -H  "accept: application/json" -H  "Authorization: [bearer-token]"
```

#### Delete a Thing Connection 

Deletes a specific Thing Connection within the system.

Requires `user_id`, `system_name`, `thing_name` and `password` (= `personId` and `bearer_token`) 
in the header. The `system_name` should use `_` as level separator.

**i-Asset Server:**

```yaml
persionId = 453
system = ee_455_labor_testStation
thing_name = thing_1
[bearer-token]
```
```
curl -X DELETE "https://iasset.salzburgresearch.at/distributionnetwork/delete_thing/453/ee_455_labor_testStation/thing_1" -H  "accept: application/json" -H  "Authorization: [bearer-token]"
```



### API for Datastreams

#### Get datastreams by system_name, aas connection or client app

Requires `user_id`, `system_name` and `password` (= `personId` and `bearer_token`) in the header.
Optionally one can narrow down the number of hits by specifying `thing_name` or `client_name`.
The `system_name` should use `_` as level separator.

**i-Asset Server:**

```yaml
persionId = 453
system = ee_455_labor_testStation
[bearer-token]
client_name = client_app_1
thing_name = thing_1
```

```bash
# For System:
curl -X GET "https://iasset.salzburgresearch.at/distributionnetwork/datastreams/453/ee_455_labor_testStation" -H  "accept: application/json" -H  "Authorization: [bearer-token]"

# For System and Client App:
curl -X GET "https://iasset.salzburgresearch.at/distributionnetwork/datastreams_per_client/453/ee_455_labor_testStation/client_app_1" -H  "accept: application/json" -H  "Authorization: [bearer-token]"

# For System and Thing Connection:
curl -X GET "https://iasset.salzburgresearch.at/distributionnetwork/datastreams_per_thing/453/ee_455_labor_testStation/thing_1" -H  "accept: application/json" -H  "Authorization: [bearer-token]"
```

#### Create new datastreams

Creates datastreams for a specified system, client app and aas connection. Requires that all instances exist.

**i-Asset Server:**

```yaml
persionId = 453
system_name = ee_455_labor_testStation  # note that '.' must be replaced by '_'
[bearer-token]

[
    {
      "name": "Air Temperature",
      "shortname": "temperature",
      "description": "Lorem ipsum",
      "thing_name": "thing_1",
      "client_name": "client_app_1"
    },
    {
      "name": "Air Humidity",
      "shortname": "humidity",
      "description": "Lorem ipsum",
      "thing_name": "thing_1",
      "client_name": "client_app_1"
    }
]
```
```bash
curl -X POST "https://iasset.salzburgresearch.at/distributionnetwork/datastreams/453/ee_455_labor_testStation" -H  "accept: application/json" -H  "Authorization: [bearer-token]" -H  "Content-Type: application/json" -d "[    {      \"name\": \"Air Temperature\",      \"shortname\": \"temperature\",      \"description\": \"Lorem ipsum\",      \"thing_name\": \"thing_1\",      \"client_name\": \"client_app_1\"    },    {      \"name\": \"Air Humidity\",      \"shortname\": \"humidity\",      \"description\": \"Lorem ipsum\",      \"thing_name\": \"thing_1\",      \"client_name\": \"client_app_1\"    }]"
```

**Local:**

```yaml
-2
at.srfg.WeatherService.Stations
asdf
[
    {
      "name": "Air Temperature",
      "shortname": "temperature",
      "description": "Lorem ipsum",
      "thing_name": "Weatherstation_1",
      "client_name": "weatherstation_1"
    },
    {
      "name": "Air Humidity",
      "shortname": "humidity",
      "description": "Lorem ipsum",
      "thing_name": "Weatherstation_1",
      "client_name": "weatherstation_1"
    },
    {
      "name": "Air Temperature",
      "shortname": "temperature",
      "description": "Lorem ipsum",
      "thing_name": "Weatherstation_2",
      "client_name": "weatherstation_2"
    },
    {
      "name": "Air Humidity",
      "shortname": "humidity",
      "description": "Lorem ipsum",
      "thing_name": "Weatherstation_2",
      "client_name": "weatherstation_2"
    }
]
```

#### Delete datastreams

Delete datastreams from a specified system.

```yaml
persionId = 453
system_name = ee_455_labor_testStation  # note that '.' must be replaced by '_'
thing_name = thing_1
[bearer-token]

["temperature"]
```
```bash
curl -X DELETE "http://localhost:1908/distributionnetwork/delete_datastreams/-1/at.srfg.MachineFleet.Machine1" -H  "accept: application/json" -H  "Authorization: asdf" -H "Content-Type: application/json" -d "[\"temperature2\"]"
```



### API for Datastream Subscriptions

#### Get datastream subscriptions by System and Client App

Requires `user_id`, `system_name` and `password` (= `personId` and `bearer_token`) in the header. 
Optionally one can narrow down the number of hits by specifying the `client_name`.
The `system_name` should use `_` as level separator.

**i-Asset Server:**

```yaml
persionId = 453
system = ee_455_labor_testStation
[bearer-token]
client_name = client_app_1
```

```bash
# For System:
curl -X GET "https://iasset.salzburgresearch.at/distributionnetwork/subscriptions/453/ee_455_labor_testStation" -H  "accept: application/json" -H  "Authorization: [bearer-token]"

# For System and Client App:
curl -X GET "https://iasset.salzburgresearch.at/distributionnetwork/subscriptions_per_client/453/ee_455_labor_testStation/client_app_1" -H  "accept: application/json" -H  "Authorization: [bearer-token]"
```

#### Create new datastream subscriptions

Creates datastream subscriptions in specified system for a Client App. Requires that all referred instances exist.

**i-Asset Server:**

```yaml
persionId = 453
system_name = ee_455_labor_testStation  # note that '.' must be replaced by '_'
client_app = client_app_1
[bearer-token]

[
    {
      "shortname": "temperature",
      "thing_name": "thing_1",
      "system_name": "ee.455.labor.testStation"
    },
    {
      "shortname": "humidity",
      "thing_name": "thing_1",
      "system_name": "ee.455.labor.testStation"
    }
]
```

**Local:**

```yaml
-2
at_srfg_WeatherService_Stations
weather_analytics
asdf

[
    {
      "shortname": "temperature",
      "thing_name": "Weatherstation_1",
      "system_name": "at.srfg.WeatherService.Stations"
    },
    {
      "shortname": "humidity",
      "thing_name": "Weatherstation_1",
      "system_name": "at.srfg.WeatherService.Stations"
    },
    {
      "shortname": "temperature",
      "thing_name": "Weatherstation_2",
      "system_name": "at.srfg.WeatherService.Stations"
    },
    {
      "shortname": "humidity",
      "thing_name": "Weatherstation_2",
      "system_name": "at.srfg.WeatherService.Stations"
    }
]
```
```bash
curl -X PUT "http://localhost:1908/distributionnetwork/subscriptions_per_client/-2/at_srfg_WeatherService_Stations/weather_analytics" -H  "accept: application/json" -H  "Authorization: asdf" -H  "Content-Type: application/json" -d "[    {      \"shortname\": \"temperature\",      \"thing_name\": \"Weatherstation_1\",      \"system_name\": \"at.srfg.WeatherService.Stations\"    },    {      \"shortname\": \"humidity\",      \"thing_name\": \"Weatherstation_1\",      \"system_name\": \"at.srfg.WeatherService.Stations\"    },    {      \"shortname\": \"temperature\",      \"thing_name\": \"Weatherstation_2\",      \"system_name\": \"at.srfg.WeatherService.Stations\"    },    {      \"shortname\": \"humidity\",      \"thing_name\": \"Weatherstation_2\",      \"system_name\": \"at.srfg.WeatherService.Stations\"    }]"
```

#### Delete datastream subscriptions

Delete datastream subscriptions from a specified system and client.

**i-Asset Server:**

```yaml
persionId = 453
system_name = ee_455_labor_testStation
client_app = client_app_1
[bearer-token]

[
    {
      "shortname": "humidity",
      "thing_name": "thing_1",
      "system_name": "ee_455_labor_testStation"
    }
]
```
```bash
curl -X DELETE "http://localhost:1908/distributionnetwork/delete_subscriptions/-2/at.srfg.WeatherService.Stations/weather_analytics" -H  "accept: application/json" -H  "Authorization: asdf" -H  "Content-Type: application/json" -d "[    {      \"shortname\": \"humidity\",      \"thing_name\": \"Weatherstation_1\",      \"system_name\": \"at.srfg.WeatherService.Stations\"    }]"
```

**Local:**

```yaml
-2
at_srfg_WeatherService_Stations
weather_analytics
asdf

[
    {
      "shortname": "humidity",
      "thing_name": "Weatherstation_1",
      "system_name": "at.srfg.WeatherService.Stations"
    }
]
```
```bash
curl -X DELETE "http://localhost:1908/distributionnetwork/delete_subscriptions/-2/at.srfg.WeatherService.Stations/weather_analytics" -H  "accept: application/json" -H  "Authorization: asdf" -H  "Content-Type: application/json" -d "[    {      \"shortname\": \"humidity\",      \"thing_name\": \"Weatherstation_1\",      \"system_name\": \"at.srfg.WeatherService.Stations\"    }]"
```



### Stream Application

A Stream Application is rule-based forwarder for datastreams from one system to another.

#### Get all Stream Apps of a system 

Requires `user_id`, `system_name` and `password` (= `personId` and `bearer_token`) in the header as Python request:

**i-Asset Server:**

```yaml
persionId = 453
system = ee_455_labor_testStation
[bearer-token]
```
```
curl -X GET "https://iasset.salzburgresearch.at/distributionnetwork/stream_apps/453/ee_455_labor_testStation" -H  "accept: application/json" -H  "Authorization: [bearer-token]"
```

#### Create a Stream App for a System (POST and PUT)

Creates a Stream App for a specified system. Requires that the user and both systems exist.

**i-Asset Server:**

```yaml
persionId = 453
system = ee_455_labor_testStation
[bearer-token]

{
    "name": "stream_app_1",
    "target_system": "at.srfg.Analytics.MachineAnalytics",
    "logic": "SELECT * FROM * WHERE quantity='temperature' AND result<2.7;",
    "description": "Lorem ipsum dolor sit amet, consectetuer adipiscing elit."
}
```
```bash
curl -X POST "https://iasset.salzburgresearch.at/distributionnetwork/stream_apps/453/ee_455_labor_testStation" -H  "accept: application/json" -H  "Authorization: [bearer-token]" -H  "Content-Type: application/json" -d "{    \"name\": \"stream_app_1\",    \"target_system\": \"at.srfg.Analytics.MachineAnalytics\",    \"logic\": \"SELECT * FROM * WHERE quantity='temperature' AND result<2.7;\",    \"description\": \"Lorem ipsum dolor sit amet, consectetuer adipiscing elit.\"}"
```

#### Get a specific Stream App by system name and stream name

Requires `user_id`, `system_name`, `stream_name` and `password` (= `personId` and `bearer_token`) 
in the header. The `system_name` should use `_` as level separator.

**i-Asset Server:**

```yaml
persionId = 453
system = ee_455_labor_testStation
stream_name = stream_app_1
[bearer-token]
```
```
curl -X GET "https://iasset.salzburgresearch.at/distributionnetwork/stream_apps/453/ee_455_labor_testStation/stream_app_1" -H  "accept: application/json" -H  "Authorization: [bearer-token]"
```

#### Delete a Stream App 

Deletes a specific Stream App within the system.

Requires `user_id`, `system_name`, `stream_name` and `password` (= `personId` and `bearer_token`) 
in the header. The `system_name` should use `_` as level separator.

**i-Asset Server:**

```yaml
persionId = 453
system = ee_455_labor_testStation
stream_name = stream_app_1
[bearer-token]
```
```
curl -X DELETE "https://iasset.salzburgresearch.at/distributionnetwork/delete_thing/453/ee_455_labor_testStation/thing_1" -H  "accept: application/json" -H  "Authorization: [bearer-token]"
```



### Stream App Controller

#### Get statistics of a Stream App

Requires `user_id`, `system_name`, `stream_name` and `password` (= `personId` and `bearer_token`) 
in the header as Python request.
Some of the statistics are only available for a running Stream App.

**i-Asset Server:**

```yaml
persionId = 453
system = ee_455_labor_testStation
stream_name = stream_app_1
[bearer-token]
statistic is a string and one of 'status' (default), 'is_running', 'stats', 'short_stats', 'logs_{number_of_logs}' or 'config'.
```
```
curl -X GET "https://iasset.salzburgresearch.at/distributionnetwork/stream_app_statistic/453/ee_455_labor_testStation/stream_app_1?statistic=config" -H  "accept: application/json" -H  "Authorization: [bearer-token]"
```

**Local:**

```
-2
at_srfg_WeatherService_Stations
weather2analytics
asdf

statistic is a string and one of 'status' (default), 'is_running', 'stats', 'short_stats', 'logs_{number_of_logs}' or 'config'.
```

#### Deploy a Stream App (POST and PUT)

Requires `user_id`, `system_name`, `stream_name` and `password` (= `personId` and `bearer_token`) 
in the header as Python request:

**i-Asset Server:**

```yaml
persionId = 453
system = ee_455_labor_testStation
stream_name = stream_app_1
[bearer-token]
```
```
curl -X POST "https://iasset.salzburgresearch.at/distributionnetwork/stream_app_deploy/453/ee_455_labor_testStation/stream_app_1" -H  "accept: application/json" -H  "Authorization: [bearer-token]" -H  "Content-Type: application/json" -d "{}"
```

**Local:**

```
-2
at_srfg_WeatherService_Stations
weather2analytics
asdf

{}
```

#### Stop a Stream App (POST)

Requires `user_id`, `system_name`, `stream_name` and `password` (= `personId` and `bearer_token`) 
in the header as Python request:

**i-Asset Server:**

```yaml
persionId = 453
system = ee_455_labor_testStation
stream_name = stream_app_1
[bearer-token]
```
```
curl -X POST "https://iasset.salzburgresearch.at/distributionnetwork/stream_app_deploy/453/ee_455_labor_testStation/stream_app_1" -H  "accept: application/json" -H  "Authorization: [bearer-token]" -H  "Content-Type: application/json" -d "{}"
```

**Local:**

```
-2
at_srfg_WeatherService_Stations
weather2analytics
asdf

{}
```

