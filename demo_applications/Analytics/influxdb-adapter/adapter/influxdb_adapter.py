#!/usr/bin/env python3
"""
Demo Scenario: Connected Machines
    MachineFleet: at.srfg.MachineFleet.Machine1/Machine2
        Connected machines want to enhance their safety by retrieving temperature, acceleration and position data from
        each other, to warn the drivers on approaching dangerous sections. As each machine measures these quantities by
        themselves, they are shared to others via the distribution-network.
    Analytics: at.srfg.Analytics.MachineAnalytics
        A provider of applied data analytics with the goal to improve the work process and safety. Therefore, data of
        various sources are consumed.
    WeatherService: at.srfg.WeatherService.Stations
        A Weather Service provider that conducts multiple Stations that measure conditions, as well as a
        central service to analyse only this local data. Additionally, the temperature data is of interest for the
        MachineFleet and therefore shared with them.

Message Schema:
{
    "phenomenonTime": ISO-8601 datetime string, "resultTime": ISO-8601 datetime string,
    "datastream": {"quantity": string, "client_app": string, "thing": string},
    "result": bool, integer, double, string, dict, list,
    "attributes": dict of key-values pairs, string: bool, integer, double, string, dict or list (optional)
}
"""
import logging
import os
import sys
import json
import time
import pytz
from datetime import datetime

import requests
from influxdb import InfluxDBClient

if os.path.exists("/src/distribution-network"):
    sys.path.append("/src/distribution-network")
from client.digital_twin_client import DigitalTwinClient

# This config is used to registering a client application on the platform
# Make sure that Kafka and Postgres are up and running before starting the platform
CONFIG = {
    "client_name": os.environ.get("CLIENT_NAME", "analytics-software"),
    "system_name": os.environ.get("SYSTEM_NAME", "at.srfg.Analytics.MachineAnalytics"),
    "server_uri": os.environ.get("SERVER_URI", "localhost:1908"),
    "kafka_bootstrap_servers": os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "iasset.salzburgresearch.at:9092")
    # ,iasset.salzburgresearch.at:9093,iasset.salzburgresearch.at:9094",
}

# load files relative to this file
dirname = os.path.dirname(os.path.abspath(__file__))
# INSTANCES = os.path.join(dirname, "instances.json")
SUBSCRIPTIONS = os.path.join(dirname, "subscriptions.json")

verbose = True
if os.environ.get("VERBOSE_ADAPTER", "True").lower().strip() == "false":
    verbose = False

# InfluxDB host
INFLUXDB_HOST = os.environ.get("ADAPTER_INFLUXDB_HOST", "localhost")  # "192.168.48.71"
INFLUXDB_PORT = os.environ.get("ADAPTER_INFLUXDB_PORT")  # "192.168.48.71"
if not INFLUXDB_PORT:
    INFLUXDB_PORT = os.environ.get("INFLUXDB_PORT", 8086)

# create InfluxDB Connector and create database if not already done
influx_client = InfluxDBClient(INFLUXDB_HOST, INFLUXDB_PORT, 'root', 'root', CONFIG["system_name"])
try:
    influx_client.create_database(CONFIG["system_name"])
except requests.exceptions.ConnectionError as e:
    time.sleep(5)
    raise e

# Set the configs, create a new Digital Twin Instance and register file structure
client = DigitalTwinClient(**CONFIG)
client.logger.info("Main: Starting client.")
client.subscribe(subscription_file=SUBSCRIPTIONS)  # Subscribe to datastreams

# Init logstash logging for data
logging.basicConfig(level='INFO')
logger = logging.getLogger(CONFIG["client_name"])
logger.setLevel(logging.INFO)

logger.info(f"Loaded clients, InfluxDB-Adapter for {CONFIG['system_name']} is ready.")

try:
    while True:
        rows_to_insert = list()
        # Receive all messages of the specified system topic, adapt subscriptions.json to consume a subset
        # commits every timeout
        received_quantities = client.consume(timeout=1.0, on_error="warn")

        for received_quantity in received_quantities:
            if verbose:
                logger.info(f'New data: {received_quantity["datastream"]["thing"]}.'
                            f'{received_quantity["datastream"]["quantity"]} = {received_quantity["result"]}')

            # send to influxdb
            # all tags and the time create together the key and must be unique
            new_row = {
                "measurement": CONFIG["system_name"],
                "tags": {
                    "system": received_quantity["datastream"].get("system", ""),
                    "thing": received_quantity["datastream"].get("thing", ""),
                    "client_app": received_quantity["datastream"].get("client_app", ""),
                    "quantity": received_quantity["datastream"]["quantity"],
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
