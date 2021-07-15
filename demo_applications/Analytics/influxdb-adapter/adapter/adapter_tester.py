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

import os
import sys

if os.path.exists("/src/distribution-network"):
    sys.path.append("/src/distribution-network")
from client.digital_twin_client import DigitalTwinClient

# This config is used to registering a client application on the platform
# Make sure that Kafka and Postgres are up and running before starting the platform
CONFIG = {
    "client_name": "analytics-software",
    "system_name": "at.srfg.Analytics.MachineAnalytics",
    "server_uri": "iasset.salzburgresearch.at",
    "kafka_bootstrap_servers": "iasset.salzburgresearch.at:9092"
    #,iasset.salzburgresearch.at:9093,iasset.salzburgresearch.at:9094"
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

# Set the configs, create a new Digital Twin Instance and register file structure
client = DigitalTwinClient(**CONFIG)
client.logger.info("Main: Starting client.")
client.subscribe(subscription_file=SUBSCRIPTIONS)  # Subscribe to datastreams


print("Loaded client, the adapter is ready.")
try:
    while True:
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
            print(f" -> Received new data: {new_row}")

except KeyboardInterrupt:
    client.disconnect()
