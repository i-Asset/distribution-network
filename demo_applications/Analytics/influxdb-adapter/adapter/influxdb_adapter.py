#!/usr/bin/env python3
"""
Demo Scenario: Connected Cars
    CarFleet: cz.icecars.iot4cps-wp5-CarFleet.Car1/Car2
        Connected cars want to enhance their safety by retrieving temperature, acceleration and position data from each
        other, to warn the drivers on approaching dangerous road sections. As each car measures these quantities by
        themselves, they are shared to others via the platform.
    Analytics: at.datahouse.Analytics.RoadAnalytics
        A provider of applied data analytics with the goal to improve the road quality. Therefore, data of various
         sources are consumed.
    WeatherService:
        A Weather Service provider that conducts multiple Stations that measure weather conditions, as well as a
        central service to forecast the Weather. Additionally, the temperature data is of interest for the CarFleet and
        therefore shared with them.

Message Schema:
{
    "phenomenonTime": ISO-8601, "resultTime": ISO-8601,
    "datastream": {"quantity": string, "client_app": string, "thing": string},
    "result": bool, integer, double, string, dict, list,
    "attributes": dict of string: bool, integer, double, string, dict or list (optional)
}
"""

import os
import sys
import json
import time
import pytz
from datetime import datetime
from influxdb import InfluxDBClient

if os.path.exists("/src/distribution-network"):
    sys.path.append("/src/distribution-network")
from client.digital_twin_client import DigitalTwinClient

# This config is used to registering a client application on the platform
# Make sure that Kafka and Postgres are up and running before starting the platform
CONFIG = {
    "client_name": os.environ.get("CLIENT_NAME", "analytics"),
    "system_name": os.environ.get("SYSTEM_NAME", "cz.icecars.iot4cps-wp5-CarFleet.Car1"),
    "server_uri": os.environ.get("SERVER_URI", "localhost:1908"),
    "kafka_bootstrap_servers": os.environ.get("KAFKA_BOOTSTRAP_SERVERS", ":9092")  # , "iasset.salzburgresearch.at:9092"
    # ,iasset.salzburgresearch.at:9093,iasset.salzburgresearch.at:9094",
}

# load files relative to this file
dirname = os.path.dirname(os.path.abspath(__file__))
# INSTANCES = os.path.join(dirname, "instances.json")
SUBSCRIPTIONS = os.path.join(dirname, "subscriptions.json")

verbose = os.environ.get("VERBOSE_ADAPTER", "True")
if verbose.lower().strip() == "false":
    verbose = False
else:
    verbose = True

# InfluxDB host
INFLUXDB_HOST = os.environ.get("INFLUXDB_HOST", "localhost")  # "192.168.48.71"
# create InfluxDB Connector and create database if not already done
influx_client = InfluxDBClient(INFLUXDB_HOST, 8086, 'root', 'root', CONFIG["system_name"])
influx_client.create_database(CONFIG["system_name"])

# Set the configs, create a new Digital Twin Instance and register file structure
client = DigitalTwinClient(**CONFIG)
client.logger.info("Main: Starting client.")
client.subscribe(subscription_file=SUBSCRIPTIONS)  # Subscribe to datastreams

# # Init logstash logging for data
# logging.basicConfig(level='WARNING')
# loggername_metric = 'influxdb-adapter'
# logger_metric = logging.getLogger(loggername_metric)
# logger_metric.setLevel(logging.INFO)


print("Loaded clients, InfluxDB-Adapter is ready.")
try:
    while True:
        rows_to_insert = list()
        # Receive all messages of the specified system topic, adapt subscriptions.json to consume a subset
        # commits every timeout
        received_quantities = client.consume(timeout=1.0, on_error="warn")

        for received_quantity in received_quantities:
            if verbose:
                print(f'New data: {received_quantity["datastream"]["quantity"]} = {received_quantity["result"]}')

            # send to influxdb
            # all tags and the time create together the key and must be unique
            new_row = {
                "measurement": CONFIG["system_name"],
                "tags": {
                    "quantity": received_quantity["datastream"]["quantity"],
                    "thing": received_quantity["datastream"].get("thing", ""),
                    "client_app": received_quantity["datastream"].get("client_app", ""),
                },
                "time": received_quantity["phenomenonTime"],
                "fields": {
                    "result": received_quantity["result"]
                }
            }
            for att, value in received_quantity.get("attributes", {}).items():
                new_row["fields"][att] = value

            rows_to_insert.append(new_row)

        influx_client.write_points(rows_to_insert)

except KeyboardInterrupt:
    client.disconnect()
