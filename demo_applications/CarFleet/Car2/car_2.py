#!/usr/bin/env python3
"""
Demo Scenario: Connected Cars
    CarFleet:
        Connected cars want to enhance their safety by retrieving temperature, acceleration and position data from each
        other, to warn the drivers on approaching dangerous road sections. As each car measures these quantities by
        themselves, they are shared to others via the platform.
    Analytics:
        A provider of applied data analytics with the goal to improve the road quality. Therefore, data of various
         sources are consumed.
    WeatherService:
        A Weather Service provider that conducts multiple Stations that measure weather conditions, as well as a
        central service to forecast the Weather. Additionally, the temperature data is of interest for the CarFleet and
        therefore shared with them.
"""

import os
import time
import pytz
import threading
from datetime import datetime

from client.digital_twin_client import DigitalTwinClient
from demo_applications.simulator.CarSimulator import CarSimulator

# load files relative to this file
dirname = os.path.dirname(os.path.abspath(__file__))
INSTANCES = os.path.join(dirname, "instances.json")
SUBSCRIPTIONS = os.path.join(dirname, "subscriptions.json")


def produce_metrics(interval=10):
    while not halt_event.is_set():
        # unix epoch and ISO 8601 UTC are both valid
        timestamp = datetime.utcnow().replace(tzinfo=pytz.UTC).isoformat()

        # Measure metrics
        temperature = car.temp.get_temp()
        acceleration = car.get_acceleration()
        latitude = car.get_latitude()
        longitude = car.get_longitude()
        attitude = car.get_attitude()

        # Print the temperature with the corresponding timestamp in ISO format
        print(f"The demo car 2 is at [{latitude}, {longitude}],   \twith the temp.: {temperature} °C  \tand had a " +
              f"maximal acceleration of {acceleration} m/s²  \tat {timestamp}")

        # Send the metrics via the client, it is suggested to use the same timestamp for later analytics
        client.produce(quantity="temperature", result=temperature, timestamp=timestamp,
                       longitude=longitude, latitude=latitude, attitude=attitude)
        client.produce(quantity="acceleration", result=acceleration, timestamp=timestamp,
                       longitude=longitude, latitude=latitude, attitude=attitude)

        time.sleep(interval)


# Receive all temperatures of the weather-service and other cars and check whether they are subzero
def consume_metrics():
    while not halt_event.is_set():
        # In this list, each datapoint is stored that is below zero degC.
        subzero_temp = list()

        # Data of the same instance can be consumed directly via the class method
        temperature = car.temp.get_temp()
        if temperature < 0:
            subzero_temp.append({"origin": config["system"], "temperature": temperature})

        # Data of other instances (and also the same one) can be consumed via the client, commits very timeout
        received_quantities = client.consume(timeout=1.0)
        for received_quantity in received_quantities:
            # The resolves the all meta-data for an received data-point
            if received_quantity['Datastream'].get('unitOfMeasurement'):
                print(f"  -> Received new external data-point from {received_quantity['phenomenonTime']}: "
                      f"'{received_quantity['Datastream']['name']}' = {received_quantity['result']} "
                      f"{received_quantity['Datastream'].get('unitOfMeasurement').get('symbol')}.")
            elif received_quantity.get('rel_distance'):
                print(f"  -> Received new external data-point from a nearby car {received_quantity['phenomenonTime']}: "
                      f"'temperature' = {received_quantity['result']} degC"
                      f", measured {received_quantity.get('rel_distance'):.2f} km away.")

            # To view the whole data-point in a pretty format, uncomment:
            # print("Received new data: {}".format(json.dumps(received_quantity, indent=2)))
            if received_quantity['Datastream'].get('unitOfMeasurement', {}).get('symbol', '') == "degC" \
                    and received_quantity["result"] < 0:
                subzero_temp.append(
                    {"origin": received_quantity["Datastream"]["name"], "temperature": received_quantity["result"]})

        # Check whether there are temperatures are subzero
        if subzero_temp != list():
            print("    WARNING, the road could be slippery, see: {}".format(subzero_temp))


if __name__ == "__main__":
    # Set the configs, create a new Digital Twin Instance and register file structure
    # This config is generated when registering a client application on the platform
    # Make sure that Kafka and GOST are up and running before starting the platform
    config = {"client_name": "client",
              "system": "cz.icecars.iot4cps-wp5-CarFleet.Car2",
              "gost_servers": "localhost:8082",
              "kafka_bootstrap_servers": "localhost:9092",
              "additional_attributes": "longitude,latitude,attitude"}
    client = DigitalTwinClient(**config)
    client.logger.info("Main: Starting client.")
    client.register(instance_file=INSTANCES)  # Register new instances could be outsourced to the platform
    client.subscribe(subscription_file=SUBSCRIPTIONS)  # Subscribe to datastreams

    # Create an instance of the CarSimulator that simulates a car driving on different tracks through Salzburg
    car = CarSimulator(track_id=2, time_factor=100, speed=35, cautiousness=1.3,
                       temp_day_amplitude=5, temp_year_amplitude=-6, temp_average=3.5, seed=1)
    client.logger.info("Main: Created instance of CarSimulator.")

    client.logger.info("Main: Starting producer and consumer threads.")
    halt_event = threading.Event()

    # Create and start the receiver Thread that consumes data via the client
    consumer = threading.Thread(target=consume_metrics)
    consumer.start()
    # Create and start the receiver Thread that publishes data via the client
    producer = threading.Thread(target=produce_metrics, kwargs=({"interval": 5}))
    producer.start()

    # set halt signal to stop the threads if a KeyboardInterrupt occurs
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        client.logger.info("Main: Sent halt signal to producer and consumer.")
        halt_event.set()
        # wait for the threads to get finished (can take about the timeout duration)
        producer.join()
        consumer.join()
        client.logger.info("Main: Stopped the demo applications.")
        client.disconnect()
