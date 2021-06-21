# Panta Rhei - InfluxDB - Adapter

#### This is the Adapter for the [Distribution-Network](https://github.com/i-Asset/distribution-network) and a DataStack with InfluxDB and Grafana.

The adapter is based on the Panta Rhei (or Digital Twin) client which allows the multi-tenant streaming of data easily.

```python3
from client.digital_twin_client import DigitalTwinClient
config = {
    "client_name": "demo_app1", 
    "system_name": "at.srfg.WeatherService.Stations",
    "kafka_bootstrap_servers": "localhost:9092", 
    "server_uri": "localhost:1908"
}
client = DigitalTwinClient(**config)
client.register(instance_file="digital_twin_mapping/instances.json")
client.subscribe(subscription_file="digital_twin_mapping/subscriptions.json")
client.produce(quantity="temperature", result=23.4)
```


## Contents

1. [Requirements](#requirements)
2. [Quickstart](#quickstart)
3. [Deploy on a Cluster](#deployment)


## Requirements

* A running instance of InfluxDB, set it up is described [here](../README.md).
* A running [Distribution-Network](https://github.com/i-Asset/distribution-network) with streaming data.

    
## Quickstart

This is an instruction on how to set up a demo scenario on your own hardware.
Here, we use Ubuntu 18.04.

```bash
cd influxdb-adapter
```

Configure the adapter in the `docker-compose.yml`:

```yaml
version: '3.4'
services:
  datastore-adapter:
    image: 127.0.0.1:5001/datastore-adapter
    build: .
    container_name: "at.srfg.WeatherService.Stations_datastore-adapter"
    network_mode: host
    environment:
      VERBOSE_ADAPTER: "true"
      # InfluxDB configuration
      INFLUXDB_HOST: "localhost"
      INFLUXDB_PORT: 8087
      # Panta Rhei configuration
      CLIENT_NAME: "weather_analytics"
      SYSTEM_NAME: "at.srfg.WeatherService.Stations"
      SERVER_URI: "localhost:1908"
      KAFKA_BOOTSTRAP_SERVERS: ":9092"
      # "192.168.48.71:9092,192.168.48.71:9093,192.168.48.71:9094"
    restart: always
```
 
To start the adapter, run the following command:


```bash
python3 influxdb-adapter/adapter/influxdb_adapter.py
```
This step requires a reachable InfluxDB endpoint on [localhost:8086](localhost:8086).
In this connector, the package [influxdb-python](https://influxdb-python.readthedocs.io/en/latest/include-readme.html)
was used. The used InfluxDB table is called `at.srfg.iot.dtz`.


Check if data is stored in `InfluxDB` using this script
 (it counts the number of rows in a set database):
 
 ```bash
# using curl
curl -G 'http://localhost:8086/query?db=at.srfg.iot.dtz' --data-urlencode 'q=SELECT * FROM "at.srfg.iot.dtz"'
#> {"results":[{"statement_id":1234}]}

# using a python script:
python3 InfluxDB_Grafana/db_interface.py
#> {'time': '1970-01-01T00:00:00Z', 'count_result': 321825}
```
 


## Deployment

Deploy the adapter in Docker with:

```bash
docker-compose up --build -d
```

Now, data from the **Distribution-Network** will be streamed into **InfluxDB**.
