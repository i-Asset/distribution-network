import os
import sys
import json
import time

import pytz
import random
import logging
import requests
from datetime import datetime

# confluent_kafka is based on librdkafka, details in install_kafka_requirements.sh
import confluent_kafka

# confluent_kafka is based on librdkafka, details in requirements.txt
try:
    from .sensorThingsRegisterHelper import SensorThingsRegisterHelper
    # from .type_mappings import type_mappings
except ImportError:
    from client.sensorThingsRegisterHelper import SensorThingsRegisterHelper
    # from client.type_mappings import type_mappings


class DigitalTwinClient:
    """The Digital Twin Client Class that serves to connect an application for data streaming."""

    def __init__(self, client_name, system_name, server_uri, kafka_bootstrap_servers,
                 communicate_via=None, break_on_errors=True):
        """Client library of devices for streaming semantically enriched data.
        :parameter client_name (string): Name of the client device this application runs on.
        :parameter system_name (string): Name of the system this application is dedicated to.
        :parameter server_uri (string): URL of the server to which this application should connect to.
        :parameter kafka_bootstrap_servers (string): If the Kafka servers run on a different cluster it can be
            specified using this argument. The servers are specified using a comma-separated string like:
            kafka1:9092,kafka2:9093,kafka2:9094
        :keyword produce_via (string, None): Choose the protocol to produce to, default: None="kafka"
        :keyword break_on_errors (boolean): Break on errors like an onmatched key, default is True
        """
        # Init logging
        self.logger = logging.getLogger("PR Client Logger")
        self.logger.setLevel(logging.INFO)
        # self.logger.setLevel(logging.DEBUG)
        logging.basicConfig(level='WARNING')
        self.logger.info("init: Initialising Digital Twin Client with name '{}' on '{}'".format(client_name, system_name))

        # Load config
        self.config = {"client_name": client_name,
                       "system_name": system_name,
                       "server_uri": server_uri,
                       "kafka_bootstrap_servers": kafka_bootstrap_servers,
                       # "kafka_rest_server": kafka_rest_server,
                       # Use a randomized hash for an unique consumer id in an client-wide consumer group
                       "kafka_group_id": "{}.{}".format(system_name, client_name),
                       "kafka_consumer_id": "consumer_%04x" % random.getrandbits(16)}
        self.logger.debug("Config for client is: {}".format(self.config))

        # # Check the connection to the SensorThings server
        # self.logger.debug("init: Checking SenorThings server connection")
        # self.check_gost_connection()

        # Create a mapping for each datastream of the client
        self.mapping = dict()
        self.mapping["logging"] = {"name": "logging", "@iot.id": -1,  # TODO logging should not be part of the mapping
                                   "kafka-topic": self.config["system_name"] + ".log"}
        self.subscriptions = set()
        self.break_on_errors = break_on_errors

        # Check the connection to Kafka, note that the connection to the brokers are preferred
        self.logger.debug("init: Checking Kafka connection")
        self.producer = None

        # Init other objects used in later methods
        self.subscribed_datastreams = None
        self.instances = None
        self.consumer = None

        if self.config["kafka_bootstrap_servers"]:
            # Create Kafka Producer
            self.producer = confluent_kafka.Producer({'bootstrap.servers': self.config["kafka_bootstrap_servers"],
                                                      'client.id': self.config["client_name"],
                                                      'request.timeout.ms': 10000,  # wait up to 10 seconds
                                                      'default.topic.config': {'acks': 'all'}})
            # poll some seconds until the producer has processed pending events (not all)
            _ = self.producer.poll(3)

            # Create Kafka Consumer
            conf = {'bootstrap.servers': self.config["kafka_bootstrap_servers"],
                    'session.timeout.ms': 6000,
                    'auto.offset.reset': 'latest',
                    'group.id': self.config["kafka_group_id"]}
            self.consumer = confluent_kafka.Consumer(**conf)

        # select how to produce a datapoint, mqtt and rest could be implemented
        self.produce = self.produce_via_kafka
        self.consume = self.consume_via_bootstrap
        if communicate_via and communicate_via.lower() == "kafka":
            self.produce = self.produce_via_kafka
            self.consume = self.consume_via_bootstrap

        self.check_kafka_connection()  # TODO check if the system already exists, break otherwise (should be efficient)

    # def check_gost_connection(self):
    #     gost_url = "http://" + self.config["gost_servers"]
    #     try:
    #         res = requests.get(gost_url + "/v1.0/Things")
    #         if res.status_code in [200, 201, 202]:
    #             self.logger.info("init: Successfully connected to GOST server {}.".format(gost_url))
    #         else:
    #             self.logger.error("init: Error, couldn't connect to GOST server: {}, status code: {}, result: {}".
    #                               format(gost_url, res.status_code, res.json()))
    #             raise ConnectionError("init: Error, couldn't connect to GOST server: {}, status code: {}, result: {}".
    #                                   format(gost_url, res.status_code, res.json()))
    #     except Exception as e:
    #         self.logger.error("init: Error, couldn't connect to GOST server: {}".format(gost_url))
    #         raise e

    def check_kafka_connection(self):
        # distinguish to connect to the kafka_bootstrap_servers (preferred) or to kafka_rest
        if self.config["kafka_bootstrap_servers"]:
            # poll some seconds until the producer has processed pending events (not all)
            polled_msgs = self.producer.poll(3)
            # print(f"polled {polled_msgs} msgs")
            # if ret_poll != 0:  # unfortunately, polling may return 0 even if the connection is disturbed
            #     self.logger.error(f"init: Error, couldn't connect to kafka bootstrap server "
            #                       f"'{self.config['kafka_bootstrap_servers']}', poll() returns {ret_poll}")
            #     raise Exception(f"init: Error, couldn't connect to kafka bootstrap server.")

        else:
            kafka_rest_url = "http://" + self.config["kafka_rest_server"] + "/topics"
            try:
                res = requests.get(kafka_rest_url, headers=dict({"Accecpt": "application/vnd.kafka.v2+json"}))
                if res.status_code == 200 and self.mapping["logging"]["kafka-topic"] in res.json():
                    self.logger.info("init: Successfully connected to kafka-rest {}.".format(kafka_rest_url))
                else:
                    if res.status_code != 200:
                        self.logger.error("init: Error, couldn't connect to kafka-rest: {}, status code: {}, "
                                          .format(kafka_rest_url, res.status_code))
                    else:
                        self.logger.error("init: Error, topic '{}' doesn't exist in Kafka cluster, stopping client, "
                                          "return code {}".format(self.mapping["logging"]["kafka-topic"],
                                                                  res.status_code))
                    raise ConnectionError(
                        "init: Error, couldn't connect to kafka-rest: {}, status code: {}".format(
                            kafka_rest_url, res.status_code))
            except Exception as e:
                self.logger.error("init: Error, couldn't connect to kafka-rest: {}".format(kafka_rest_url))
                raise e

        self.produce("logging", "Started Digital Twin Client with name '{}' for system '{}'".format(
            self.config["client_name"], self.config["system_name"]))

    # def register_existing(self, mappings_file):
    #     """
    #     Create a mappings between internal and unique quantity ids
    #     :param mappings_file. Stores the mapping between internal and external quantity name
    #     :return:
    #     """
    #     try:
    #         with open(mappings_file) as f:
    #             mappings = json.loads(f.read())
    #     except FileNotFoundError:
    #         self.logger.warning("subscribe: FileNotFound, creating empty mappings file")
    #         mappings = json.loads('{"Datastreams": {}}')
    #     # Make structure pretty
    #     with open(mappings_file, "w") as f:
    #         f.write(json.dumps(mappings, indent=2))
    #     self.logger.debug("register: Loaded the datastream mapping: {}".format(mappings["Datastreams"]))
    #
    #     # Get the datastreams of the form
    #     # {4: {'@iot.id': 4, 'name': 'Machine Temperature', '@iot.selfLink': 'http://...}, 5: {....}, ...}
    #     gost_url = "http://" + self.config["gost_servers"]
    #     # Sort datastreams to pick latest stream datastream in case of duplicates
    #     gost_datastreams = sorted(requests.get(gost_url + "/v1.0/Datastreams?$expand=Thing").json()["value"],
    #                               key=lambda k: k["@iot.id"])
    #
    #     for key, v in mappings["Datastreams"].items():
    #         unique_ds_name = self.config["system_name"] + "." + v["Thing"] + "." + v["name"]
    #         for ds in gost_datastreams:
    #             if unique_ds_name == ds["name"]:
    #                 self.mapping[key] = {"name": ds["name"],
    #                                      "@iot.id": ds["@iot.id"],
    #                                      "Thing": ds["Thing"].get("name", ds["Thing"]),
    #                                      "observationType": ds["observationType"]}
    #
    #     self.logger.debug("register: Successfully loaded mapping: {}".format(self.mapping))
    #     msg = "Found registered instances for Digital Twin Client '{}': {}".format(self.config["client_name"],
    #                                                                                self.mapping)
    #     self.produce("logging", msg)
    #     self.logger.info("register: " + msg)

    def register(self, instance_file):
        self.register_new(instance_file)

    def register_new(self, instance_file):
        """
        Post or path instances using the RegisterHanlder class.
        Create mapping to use the correct kafka topic for each datastream type.
        Create Kafka Producer instance.
        :param instance_file. Stores Things, Sensors and Datastreams+ObservedProperties, it also stores the structure
        :return:
        """
        # # The RegisterHelper class does the whole register workflow
        # register_helper = SensorThingsRegisterHelper(self.logger, self.config)
        # self.instances = register_helper.register(instance_file)
        #
        # Create Mapping to send on the correct data type: Logger and one for each datastream
        # dict_keys(['name', 'shortname', 'description', 'observationType', 'unitOfMeasurement', 'ObservedProperty',
        # 'thing', 'client', 'additional_attributes'])  # thing equals the aas name
        req_keys = {"name", "shortname", "thing", "client"}

        try:
            with open(instance_file) as f:
                datastreams = json.loads(f.read())
        except FileNotFoundError:
            self.logger.warning("register_new: FileNotFound, creating empty datastream file")
            datastreams = json.loads('{"Datastreams": []}')
        with open(instance_file, "w") as f:
            f.write(json.dumps(datastreams, indent=2))

        # Check each entry of the instance file and store into mapping with the shortname as key
        for ds in datastreams["Datastreams"]:
            if not isinstance(ds, dict):
                msg = (f"register_new: Wrong format in {instance_file}, each item must have {req_keys}")
                self.logger.error(msg)
                raise Exception(msg)
            if not req_keys.issubset(ds.keys()):
                msg = (f"register_new: Missing keys {set(ds.keys()).difference(req_keys)} in {instance_file}"
                       f" in instance {ds.items()}")
                self.logger.error(msg)
                raise Exception(msg)
            if ds["shortname"] == "logging":
                msg = f"register_new: The shortname 'logging' is not reserved for datastreams."
                self.logger.error(msg)
                raise Exception(msg)

            self.mapping[ds["shortname"]] = ds
            self.mapping[ds["shortname"]]["kafka-topic"] = self.config["system_name"] + ".int"

        self.logger.debug(f"register_new: Successfully loaded mapping for {len(self.mapping)} datastreams.")
        msg = f'Registered datastreams for Digital Twin Client {self.config["client_name"]}: {self.mapping.keys()}'
        self.produce("logging", msg)
        self.logger.info(f"register_new: {msg}")

    def produce_via_kafka(self, quantity, result, timestamp=None, **kwargs):
        """
        Function that sends data of registered datastreams semantically annotated to the Digital Twin Messaging System
        via the bootstrap_server (preferred) or kafka_rest
        :param quantity: Quantity of the Data
        :param result: The actual value without units. Can be boolean, integer, float, category or an object
        :param timestamp: either ISO 8601 or a 10,13,16 or 19 digit unix epoch format. If not given, it will be created.
        :param kwargs: additional keyword arguments that hold tags or additional quantities to describe the datapoint
        :return:
        """
        # check, if the quantity is registered
        if quantity not in self.mapping.keys():
            self.logger.error("send: Quantity is not registered: {}".format(quantity))
            raise Exception("send: Quantity is not registered: {}".format(quantity))

        # create data record with additional attributes
        if quantity not in self.mapping.keys():
            msg = (f"The quantity with shortname {quantity} is not registered. "
                   f"The following quantities are registered: {self.mapping.keys()}")
            self.logger.error(msg)
            if self.break_on_errors:
                raise Exception(msg)

        data = dict({"phenomenonTime": self.get_iso8601_time(timestamp),
                     "resultTime": datetime.utcnow().replace(tzinfo=pytz.UTC).isoformat(),
                     "datastream": {
                         "quantity": quantity,
                         "client_app": self.config["client_name"]
                     },
                     "result": result
                     })
        dedicated_thing = self.mapping[quantity].get("thing")
        if dedicated_thing:
            data["datastream"]["thing"] = dedicated_thing

        # append the additional attributes are a property of the datastream
        add_attributes = self.mapping[quantity].get("additional_attributes")
        if add_attributes:
            data["attributes"] = dict()
            for key, value in kwargs.items():
                if key in add_attributes:
                    data["attributes"][key] = value

        # # check, if the type of the result is correct
        # try:
        #     data["result"] = type_mappings[self.mapping[quantity]["observationType"]](result)
        # except ValueError as e:
        #     self.logger.error("send: Error, incorrect type was recognized, result: {}, "
        #                       "result.type: {}, dedicated type (as registered): {}"
        #                       "".format(result, type(result), self.mapping[quantity]["observationType"]))
        #     raise e

        # Either send to kafka bootstrap, or to kafka rest endpoint
        self.send_to_kafka_bootstrap(
            # build the kafka-topic that is used
            kafka_topic=self.mapping[quantity]["kafka-topic"],
            # the key is either the name of the observed "thing" or the "client-name" (for logging)
            kafka_key=self.mapping[quantity].get("thing", self.config["client_name"]),
            data=data)  # the payload to send

        # if self.config["kafka_bootstrap_servers"]:
        #     self.send_to_kafka_bootstrap(kafka_topic, kafka_key, data)
        # else:
        #     self.send_to_kafka_rest(kafka_topic, kafka_key, data)

    @staticmethod
    def get_iso8601_time(timestamp):
        """
        This function converts multiple standard timestamps to ISO 8601 UTC datetime.
        The output is strictly in the following style: 2018-12-03T15:55:39.054752+00:00
        :param timestamp: either ISO 8601 or a 10,13,16 or 19 digit unix epoch format.
        :return: ISO 8601 format. e.g. 2018-12-03T15:55:39.054752+00:00
        """
        if timestamp is None:
            return datetime.utcnow().replace(tzinfo=pytz.UTC).isoformat()
        if isinstance(timestamp, str):
            if timestamp.endswith("Z"):  # Expects the timestamp in the form of 2018-11-06T13:57:55.088294Z
                return datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=pytz.UTC).isoformat()
            else:  # Expects the timestamp in the form of  2018-11-06T13:57:55.088294+00:00
                return datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%f+00:00').replace(tzinfo=pytz.UTC).isoformat()

        if isinstance(timestamp, float):  # Expects the timestamp in the form of 1541514377.497349 (s)
            return datetime.utcfromtimestamp(timestamp).replace(tzinfo=pytz.UTC).isoformat()

        if isinstance(timestamp, int):
            if timestamp < 1e12:  # Expects the timestamp in the form of 1541514377 (s)
                return datetime.utcfromtimestamp(timestamp).replace(tzinfo=pytz.UTC).isoformat()
            elif timestamp < 1e15:  # Expects the timestamp in the form of 1541514377497 (ms)
                return datetime.utcfromtimestamp(timestamp / 1e3).replace(tzinfo=pytz.UTC).isoformat()
            elif timestamp < 1e15:  # Expects the timestamp in the form of 1541514377497 (us)
                return datetime.utcfromtimestamp(timestamp / 1e6).replace(tzinfo=pytz.UTC).isoformat()
            else:  # Expects the timestamp in the form of 1541514377497349 (ns)
                return datetime.utcfromtimestamp(timestamp / 1e9).replace(tzinfo=pytz.UTC).isoformat()

    # def delivery_report_connection_check(self, err, msg):
    #     """ Called only once to check the connection to kafka.
    #         Triggered by poll() or flush()."""
    #     if err is not None:
    #         self.logger.error("init: Kafka connection check to brokers '{}' Message delivery failed: {}".format(
    #             self.config["kafka_bootstrap_servers"], err))
    #         raise Exception("init: Kafka connection check to brokers '{}' Message delivery failed: {}".format(
    #             self.config["kafka_bootstrap_servers"], err))
    #     else:
    #         self.logger.info(
    #             "init: Successfully connected to the Kafka bootstrap server: {} with topic: '{}', partitions: [{}]"
    #             "".format(self.config["kafka_bootstrap_servers"], msg.topic(), msg.partition()))

    def delivery_report(self, err, msg):
        """ Called once for each message produced to indicate delivery result.
            Triggered by poll() or flush()."""
        if err is not None:
            self.logger.warning('delivery_report: Message delivery failed: {}'.format(err))
        else:
            self.logger.debug("delivery_report: Message delivered to topic: '{}', partitions: [{}]".format(
                msg.topic(), msg.partition()))

    def send_to_kafka_bootstrap(self, kafka_topic, kafka_key, data):
        """
        Function that sends data to the kafka_bootstrap_servers
        :param kafka_topic: topic to which the data will sent
        :param kafka_key: key for the data
        :param data: data that is sent to the kafka bootstrap server
        :return:
        """
        # Trigger any available delivery report callbacks from previous produce() calls
        self.producer.poll(0)

        # Asynchronously produce a message, the delivery report callback
        # will be triggered from poll() above, or flush() below, when the message has
        # been successfully delivered or failed permanently.
        self.producer.produce(kafka_topic,
                              value=json.dumps(data, separators=(',', ':')).encode('utf-8'),
                              key=json.dumps(kafka_key, separators=(',', ':')).encode('utf-8'),
                              callback=self.delivery_report)
        # Wait for any outstanding messages to be delivered and delivery report
        # callbacks to be triggered.
        self.producer.flush()

    # def send_to_kafka_rest(self, kafka_topic, kafka_key, data):
    #     """
    #     Function that sends data to the kafka_rest_server
    #     :param kafka_topic: topic to which the data will sent
    #     :param kafka_key: key for the data
    #     :param data: data that is sent to the kafka bootstrap server
    #     :return:
    #     """
    #     # Build the payload
    #     data = json.dumps({"records": [{"key": kafka_key, "value": data}]}).encode("utf-8")
    #
    #     # Post the data with headers to kafka-rest
    #     kafka_url = "http://{}/topics/{}".format(self.config["kafka_rest_server"], kafka_topic)
    #     try:
    #         res = requests.post(kafka_url, data=data, headers=dict(
    #             {'Content-type': 'application/vnd.kafka.json.v2+json',
    #              'Accept': 'application/vnd.kafka.v2+json, application/vnd.kafka+json, application/json'}))
    #         if res.status_code == 200:
    #             self.logger.debug("produce: sent message to {}".format(kafka_url))
    #         else:
    #             self.logger.warning(
    #                 "produce: Couldn't post message to {}, status code: {}".format(kafka_url, res.status_code))
    #             raise ConnectionError("Couldn't post message to {}, status code: {}".format(kafka_url, res.status_code))
    #     except ConnectionError as e:
    #         self.logger.error("produce: Couldn't post message to {}".format(kafka_url))
    #         raise e

    def subscribe(self, subscription_file):
        """
        Create a Kafka consumer instance
        Subscribe to datastream names which are stored in the subscription_file. If not subscription file is found,
        and empty one is created
        Load metadata for subscribed datastreams from the GOST server and store in attributes
        :param subscription_file:
        :return:
        """
        self.logger.debug("subscribe: Subscribing on {}, loading instances".format(subscription_file))
        # {"subscribed_datastreams": ["domain.enterprise.work-center.system.shortname", ... ]}
        # Load from subscription_file or create empty one if not exists
        try:
            with open(subscription_file) as f:
                subscriptions = json.loads(f.read())
        except FileNotFoundError:
            self.logger.warning("subscribe: FileNotFound, creating empty subscription file")
            subscriptions = json.loads('{"subscriptions": []}')
        with open(subscription_file, "w") as f:
            f.write(json.dumps(subscriptions, indent=2))
        if not (isinstance(subscriptions, dict) and "subscriptions" in subscriptions.keys() and
                isinstance(subscriptions["subscriptions"], list)):
            msg = (f'subscribe: The subscriptions must contain a list of datastream idenifiers of the form: '
                   f'{{"subscriptions": ["interal_shortname", ..., "domain.enterprise.work-center.system.external_shortname", ...]}} '
                   f'with "*" as placeholder. Provided was {subscriptions}.')
            self.logger.error(msg)
            raise Exception(msg)

        # load the datastreams
        sub_int = sub_ext = False
        for ds in subscriptions["subscriptions"]:
            if ds.count(".") == 0:  # add intra-system datastream name to subscriptions
                sub_int = True
                self.subscriptions.add(ds)
            if ds.count(".") == 4:    # add intra-system datastream name to subscriptions
                if ds.startswith(self.config["system_name"]):  # intra-system datastream with global definition
                    self.subscriptions.add(ds.split(".")[-1])  # cast the definition as local
                    sub_int = True
                else:  # inter-system datastream with global definition
                    self.subscriptions.add(ds)
                    sub_ext = True
            if ds.count(".") not in [0, 4]:
                raise Exception(f"Invalid topic / system name in '{subscription_file}': '{ds}'.")

        self.logger.info("subscribe: Subscribing to datastreams with names: {}".format(self.subscriptions))

        # Either consume from kafka bootstrap, or to kafka rest endpoint
        if self.config["kafka_bootstrap_servers"]:
            # Subscribe to topics that are needed to get the data
            topic_subs = list()
            if sub_int:
                topic_subs.append(self.config["system_name"] + ".int")
            if sub_ext:
                topic_subs.append(self.config["system_name"] + ".ext")
            self.consumer.subscribe(topic_subs)

        else:
            # Create consumer
            data = json.dumps({
                "name": self.config["kafka_consumer_id"],  # consumer name equals consumer group name
                "format": "json",
                "auto.offset.reset": "earliest",
                "auto.commit.enable": "true"}).encode("utf-8")
            kafka_url = "http://{}/consumers/{}".format(self.config["kafka_rest_server"], self.config["kafka_group_id"])
            res = requests.post(kafka_url, data=data, headers=dict({"Content-Type": "application/vnd.kafka.v2+json"}))
            if res.status_code == 200:
                self.logger.debug("subscribe: Created consumer instance '{}'".format(self.config["kafka_consumer_id"]))
            elif res.status_code == 409:
                self.logger.debug("subscribe: already created consumer instance")
            else:
                self.logger.error("subscribe: can't create consumer instance")
                raise Exception("subscribe: can't create consumer instance")

            # Subscribe to topics
            kafka_url = "http://{}/consumers/{}/instances/{}/subscription".format(
                self.config["kafka_rest_server"], self.config["kafka_group_id"], self.config["kafka_consumer_id"])
            data = json.dumps({"topics": [self.config["system_name"] + ".int", self.config["system_name"] + ".ext"]}
                              ).encode("utf-8")
            res = requests.post(kafka_url, data=data,
                                headers=dict({"Content-Type": "application/vnd.kafka.json.v2+json"}))
            if res.status_code == 204:
                self.logger.debug("subscribe: Subscribed on topics: {}".format(json.loads(data)["topics"]))
            else:
                self.logger.error(
                    "subscribe: can't create consumer instance, status code: {}".format(res.status_code))
                raise Exception(
                    "subscribe: can't create consumer instance, status code: {}".format(res.status_code))

        # # Check the subscriptions and create mapping
        # # {4: {'@iot.id': 4, 'name': 'Machine Temperature', '@iot.selfLink': 'http://...}, 5: {....}, ...}
        # gost_url = "http://" + self.config["gost_servers"]
        # # Sort datastreams to pick latest stream datastream in case of duplicates
        # gost_datastreams = sorted(requests.get(gost_url + "/v1.0/Datastreams?$expand=Sensors,Thing,ObservedProperty")
        #                           .json()["value"], key=lambda k: k["@iot.id"])
        # self.subscribed_datastreams = {ds["@iot.id"]: ds for ds in gost_datastreams if ds["name"]
        #                                in subscriptions["subscribed_datastreams"]}
        # if "*" in subscriptions["subscribed_datastreams"]:
        #     self.subscribed_datastreams["*"] = {"name": "*"}
        #
        # for key, value in self.subscribed_datastreams.items():
        #     self.logger.info("subscribe: Subscribed to datastream: id: '{}' and metadata: '{}'".format(key, value))
        # if len(self.subscribed_datastreams.keys()) == 0:
        #     self.logger.warning("subscribe: No subscription matches an existing datastream.")
        # for stream in subscriptions["subscribed_datastreams"]:
        #     if stream not in [subscribed_ds["name"] for subscribed_ds in self.subscribed_datastreams.values()]:
        #         self.logger.warning("subscribe: Couldn't subscribe to {}, datastream is not registered".format(stream))

    def consume_via_bootstrap(self, timeout=1.0, on_error="ignore"):
        """
        Receives data from the Kafka topics. On new data, it checks if it is valid, filters for subscribed datastreams
        and returns the message augmented with datastream metadata.
        :param timeout: duration how long to wait to receive data
        :param on_error: behaviour on invalid consumed data, "ignore" (default) | "warn" | "break"
        :return: either None or data augmented with metadata for each received and subscribed datastream, e.g.:
            {'phenomenonTime': '2018-12-03T16:08:03.366855+00:00', '
             resultTime': '2018-12-03T16:08:03.367045+00:00',
             'result': 5.44982168968592,
             'datastream': {'thing': 4, 'quantity: 'temperature', system: 'dom.comp.work-center.station'},
             'topic': 'dom.comp.work-center.station.ext'
             'partition': 0
            }
        """
        # Waits up to 'session.timeout.ms' for a message, batches of maximal 100 messages are consumed at once
        msgs = self.consumer.consume(num_messages=100, timeout=timeout)
        received_quantities = list()

        for msg in msgs:
            try:
                data = json.loads(msg.value().decode('utf-8', errors='ignore'))
            except json.decoder.JSONDecodeError as e:
                if on_error == "ignore":
                    continue
                elif on_error == "warn":
                    self.logger.warning(e)
                    continue
                else:
                    raise e

            quantity = data.get("datastream", dict()).get("quantity", None)

            if msg.topic().endswith(".int") and (quantity in self.subscriptions or
                                                 self.config["system_name"] + "." + quantity in self.subscriptions):
                data["partition"] = msg.partition()
                data["topic"] = msg.topic()
                received_quantities.append(data)
                # print(f"found '{quantity}' in internal topics")

            elif msg.topic().endswith(".ext"):  # check for matches in each candidate
                data["partition"] = msg.partition()
                data["topic"] = msg.topic()  # system + ".ext"

                if data["topic"].count(".") != 4:
                    raise Exception(f"Invalid topic / system name: '{data['topic']}'.")
                data["datastream"]["system"] = data["topic"].replace(".ext", "")

                domain, company, workcenter, station, topic_type = data["topic"].split(".")
                for can in self.subscriptions:
                    if can.count(".") != 4:
                        continue  # is required for testing
                    c_domain, c_company, c_workcenter, c_station, c_quantity = can.split(".")
                    if (
                            (c_domain == domain or c_domain == "*") and
                            (c_company == company or c_company == "*") and
                            (c_workcenter == workcenter or c_workcenter == "*") and
                            (c_station == station or c_station == "*") and
                            (c_quantity == quantity or c_quantity == "*")
                    ):
                        received_quantities.append(data)
                        break

        return received_quantities

    # def consume_wrapper(self, timeout=1, on_error="ignore"):
    #     """
    #     Receives data from the Kafka topics directly via a bootstrap server (preferred) or via kafka rest.
    #     On new data, it checks if it is valid and filters for subscribed datastreams
    #     and returns a list of messages augmented with datastream metadata.
    #     :param timeout: duration how long to wait to receive data
    #     :return: either None or data in SensorThings format and augmented with metadata for each received and
    #     subscribed datastream. e.g.
    #     [{"topic": "at.srfg.MachineFleet.Machine1.int","key": "at.srfg.MachineFleet.Machine1.Demo Car 1",
    #     "value": {"phenomenonTime": "2019-04-08T09:47:35.408785+00:00","resultTime": "2019-04-08T09:47:35.408950+00:00",
    #     "Datastream": {"@iot.id": 11},"result": 2.9698054997459593},"partition": 0,"offset": 1},...]
    #     """
    #     # msg = self.consumer.poll(timeout)  # Waits up to 'session.timeout.ms' for a message
    #     if self.config["kafka_bootstrap_servers"]:
    #         return self.consume_via_bootstrap(timeout, on_error=on_error)
    #
    #     # Consume data via Kafka Rest
    #     else:
    #         kafka_url = "http://{}/consumers/{}/instances/{}/records?timeout={}&max_bytes=300000".format(
    #             self.config["kafka_rest_server"], self.config["kafka_group_id"],
    #             self.config["kafka_consumer_id"], int(timeout * 1000))
    #
    #         response = requests.get(url=kafka_url, headers=dict({"Accept": "application/vnd.kafka.json.v2+json"}))
    #         if response.status_code != 200:
    #             self.logger.error("consume: can't get messages from {}, status code {}".format(kafka_url,
    #                                                                                            response.status_code))
    #             raise Exception("consume: can't get messages from {}".format(kafka_url))
    #         records = response.json()
    #         if not records:
    #             self.logger.debug("consume: got empty list")
    #             return list()
    #         payload = list()
    #         self.logger.debug("get: got {} new message(s)".format(len(records)))
    #         for record in records:
    #             iot_id = record.get("value", None).get("Datastream", None).get("@iot.id", None)
    #             if iot_id in self.subscribed_datastreams.keys():
    #                 datapoint = record["value"]
    #                 datapoint["Datastream"] = self.subscribed_datastreams[iot_id]
    #                 payload.append(datapoint)
    #                 self.logger.debug("Received new datapoint: '{}'".format(datapoint))
    #         return payload

    def disconnect(self):
        """
        Disconnect and close Kafka Connections
        :return:
        """
        if self.config["kafka_bootstrap_servers"]:
            try:
                self.producer.flush()
            except AttributeError:
                pass
            try:
                self.consumer.close()
            except AttributeError:
                pass
        else:
            kafka_url = "http://{}/consumers/{}/instances/{}".format(
                self.config["kafka_rest_server"], self.config["kafka_group_id"], self.config["kafka_consumer_id"])
            # try:
            res = requests.delete(kafka_url, headers=dict({"Content-Type": "application/vnd.kafka.v2+json"}))
            if res.status_code == 204:
                self.logger.info("disconnect: Removed consumer instance.")
            else:
                self.logger.error(
                    "subscribe: can't remove consumer instance, status code: {}.".format(res.status_code))
            # except Exception as e:
            #     self.logger.error("subscribe: can't remove consumer instance.")
        self.logger.info("disconnect: Digital Twin Client disconnected")
