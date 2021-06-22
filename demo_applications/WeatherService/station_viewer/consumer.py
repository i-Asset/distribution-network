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
from client.digital_twin_client import DigitalTwinClient


# This config is used to registering a client application on the platform
# Make sure that Kafka and Postgres are up and running before starting the platform
CONFIG = {
    "client_name": "consumer",
    "system_name": "at.srfg.WeatherService.Stations",
    "server_uri": "localhost:1908",
    "kafka_bootstrap_servers": ":9092"  # , "iasset.salzburgresearch.at:9092"
    # ,iasset.salzburgresearch.at:9093,iasset.salzburgresearch.at:9094",
}

# load files relative to this file
dirname = os.path.dirname(os.path.abspath(__file__))
INSTANCES = os.path.join(dirname, "instances.json")
SUBSCRIPTIONS = os.path.join(dirname, "subscriptions.json")

client = DigitalTwinClient(**CONFIG)
# client.register(instance_file=INSTANCES)
client.subscribe(subscription_file=SUBSCRIPTIONS)

fan_status = False
try:
    while True:
        # Receive all queued messages of the weather-service
        # Data is consumed via the client, commits automatically on return
        received_quantities = client.consume(timeout=1.0, on_error="warn")

        for received_quantity in received_quantities:
            # The resolves the all meta-data for an received data-point
            print(f"  -> Received new external data-point from {received_quantity['phenomenonTime']}: "
                  f"'{received_quantity['datastream']}' = {received_quantity['result']}.")

        # To view the whole data-point in a pretty format, uncomment:
        # print("Received new data: {}".format(json.dumps(received_quantity, indent=2)))

except KeyboardInterrupt:
    client.disconnect()
