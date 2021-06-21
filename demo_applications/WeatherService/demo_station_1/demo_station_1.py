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
import time
import pytz
import threading
from datetime import datetime

from client.digital_twin_client import DigitalTwinClient
from demo_applications.simulator.SimulateTemperatures import SimulateTemperatures

# This config is used to registering a client application on the platform
# Make sure that Kafka and Postgres are up and running before starting the platform
CONFIG = {
    "client_name": "weatherstation_1",
    "system_name": "at.srfg.WeatherService.Stations",
    "server_uri": "localhost:1908",
    "kafka_bootstrap_servers": ":9092"  # , "iasset.salzburgresearch.at:9092"
    # ,iasset.salzburgresearch.at:9093,iasset.salzburgresearch.at:9094",
}
INTERVAL = 5  # interval at which to produce (s)

# load files relative to this file
dirname = os.path.dirname(os.path.abspath(__file__))
INSTANCES = os.path.join(dirname, "instances.json")
SUBSCRIPTIONS = os.path.join(dirname, "subscriptions.json")

client = DigitalTwinClient(**CONFIG)
client.register(instance_file=INSTANCES)

randomised_temp = SimulateTemperatures(time_factor=100, day_amplitude=5, year_amplitude=-5, average=2.5)

try:
    while True:
        # epoch and ISO 8601 UTC are both valid
        timestamp = time.time()

        # Measure the demo temperature
        temperature = randomised_temp.get_temp()

        # Send the demo temperature
        client.produce(quantity="temperature_1", result=temperature, timestamp=timestamp)

        # Print the temperature with the corresponding timestamp in ISO format
        print(f"The air temperature at the demo station 1 is {temperature} °C at "
              f"{datetime.utcnow().replace(tzinfo=pytz.UTC).isoformat()}")
        time.sleep(INTERVAL)

except KeyboardInterrupt:
    client.disconnect()
