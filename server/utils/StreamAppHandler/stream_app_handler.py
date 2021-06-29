#!/usr/bin/env python3
"""API Handler for Stream Apps."""

import os
import time
import logging

import docker
import docker.errors

WAIT_TIME = 3


class SimpleStreamApp:
    def __init__(self, system_name, stream_name, source_system, target_system, kafka_bootstrap_servers, server_uri,
                 filter_logic, verbose):
        self.system_name = system_name
        self.stream_name = stream_name
        self.source_system = source_system
        self.target_system = target_system
        self.kafka_bootstrap_servers = kafka_bootstrap_servers
        self.server_uri = server_uri
        self.filter_logic = filter_logic
        self.verbose = verbose

        # create unique name for container
        self.container_name = f"stream-app_{self.system_name}_{self.stream_name}"
        logging.basicConfig(format='%(asctime)-15s %(levelname)s: %(message)s')
        self.logger = logging.getLogger(self.container_name)
        self.logger.setLevel(logging.INFO)
        self.logger.info(f"Created SimpleStreamApp with name {self.container_name}")

        # Init container, None or docker container id
        self.container = None
        self.client = None

        # Create a docker-py client
        self.client = create_client()

    def get_name(self):
        return self.container_name

    def get_config(self):
        return dict({
            "system_name": self.system_name,
            "stream_name": self.stream_name,
            "source_system": self.source_system,
            "target_system": self.target_system,
            "kafka_bootstrap_servers": self.kafka_bootstrap_servers,
            "server_uri": self.server_uri,
            "filter_logic": self.filter_logic,
            "verbose": self.verbose
        })

    def deploy(self):
        """Deploys the stream as sibling container"""
        try:
            self.container = self.client.containers.run(
                image="streamhub_stream-app", detach=True, name=self.container_name,
                environment={"STREAM_NAME": self.stream_name,
                             "SOURCE_SYSTEM": self.source_system,
                             "TARGET_SYSTEM": self.target_system,
                             "KAFKA_BOOTSTRAP_SERVERS": self.kafka_bootstrap_servers,
                             "SERVER_URI": self.server_uri,
                             "FILTER_LOGIC": self.filter_logic,
                             "VERBOSE": self.verbose},
                network_mode="host",  # may be deprecated in case of sibling container
                restart_policy={"name": "always"})
            time.sleep(WAIT_TIME)
            self.logger.info(f"Container '{self.container_name}' was deployed, status: {self.container.status}")

        except docker.errors.APIError:
            self.logger.info(f"Container '{self.container_name}' already running. Stop and deploy again.")
            self.stop()
            time.sleep(WAIT_TIME)
            self.deploy()

    def stop(self):
        """Stop the container. Use the container id if possible, otherwise stop by container name"""
        if not self.container:
            if not self.client:
                # Create a docker-py client
                self.client = create_client()
            try:
                self.container = self.client.containers.get(self.container_name)
            except docker.errors.NotFound:
                self.logger.info(f"Container '{self.container_name}' doesn't run.")
                return
        self.container.stop()
        self.container.remove()
        self.logger.info(f"Stopped container '{self.container_name}'")

    def get_status(self):
        """Get the status of the container.
        Within created|running|exited|not_found"""
        try:
            self.container.reload()
            return self.container.attrs["State"].get("Status")
        except docker.errors.NotFound:
            return "not_found"

    def is_running(self):
        """Get the status of the container.
        Within created|running|exited|not_found"""
        try:
            if not self.container:
                self.container = self.client.containers.get(self.container_name)
            self.container.reload()
            return not self.container.attrs["State"].get("Restarting")  # request restarting as restart_policy is always
        except docker.errors.NotFound:
            return False

    def get_logs(self, last_n=None):
        """Return the current logs from the container."""
        try:
            if not self.container:
                self.container = self.client.containers.get(self.container_name)
            if last_n:
                return self.container.logs(tail=last_n)
            else:
                return self.container.logs()
        except docker.errors.NotFound:
            return None

    def get_stats(self):
        """Get the statistics of the container"""
        try:
            if not self.container:
                self.container = self.client.containers.get(self.container_name)
            self.container.reload()
            return self.container.attrs
        except docker.errors.NotFound:
            return None

    def get_short_stats(self):
        """Get short statistics of the container"""
        try:
            if not self.container:
                self.container = self.client.containers.get(self.container_name)
            self.container.reload()
            return dict({
                "Running": self.container.attrs.get("State", {}).get("Running"),
                "Restarting": self.container.attrs.get("State", {}).get("Restarting"),
                "StartedAt": self.container.attrs.get("State", {}).get("StartedAt"),
                "FinishedAt": self.container.attrs.get("State", {}).get("FinishedAt"),
                "ExitCode": self.container.attrs.get("State", {}).get("ExitCode"),
            })
        except docker.errors.NotFound:
            return None

    @staticmethod
    def get_all_streams():
        client = create_client()
        all_containers = list()
        for con in client.containers.list():
            try:
                con.reload()
                _ = con.attrs
            except:
                pass
            c = dict()
            c["CONTAINER ID"] = con.attrs["Id"]
            c["IMAGE"] = con.image.tags[0]
            c["CREATED"] = con.attrs["Created"]
            c["STATUS"] = con.attrs["State"].get("Restarting")
            c["Name"] = con.attrs["Name"]
            all_containers.append(c)
        return all_containers


# @task(default=True)
# def local_deploy_multi(system_name="0000", stream_name="test-stream", stream=None, logger=None):
#     """
#     Deploys a stream with the given parameters locally
#     :param system_name: Name of the system - unique RAMI 4.0 station
#     :param stream_name: name of the stream app
#     :param stream: attribute dictionary for stream with keys SOURCE_SYSTEM, TARGET_SYSTEM,
#     KAFKA_BOOTSTRAP_SERVERS, GOST_SERVER, and FILTER_LOGIC
#     :return:
#     """
#     # run('git clone https://git-service.ait.ac.at/im-IoT4CPS/WP5-lifecycle-mgmt.git /WP5-lifecycle-mgmt')
#     import pdb
#     # pdb.set_trace()
#     with cd(""):
#         # image name is 'iot4cps/streamapp', container_name is the container name
#         with hide('output', 'running'), settings(warn_only=True):
#             cur_frame = inspect.currentframe()
#             s = f"(Re-)building Dockerfile named 'iot4cps/multi-source-stream'. " \
#                 f"Method was called from: {inspect.getouterframes(cur_frame, 2)[-1].filename}" \
#                 f" in the directory {os.path.realpath(os.path.curdir)}"
#             if logger:
#                 logger.info(s)
#             else:
#                 print(s)
#
#             # Build the Dockerfile dependent of the caller's directory
#             if inspect.getouterframes(cur_frame, 2)[-1].filename.endswith("views/StreamHandler/stream_tester.py"):
#                 local('docker build -t iot4cps/multi-source-stream ../../TimeSeriesJoiner')
#             else:
#                 local('docker build -t iot4cps/multi-source-stream TimeSeriesJoiner')
#
#         container_name = build_name(system_name, stream_name)
#         if stream is None:  # fill with test values if emptystream = dict()
#             print("WARNING, no parameter given.")
#             stream = dict()
#             stream["SOURCE_SYSTEM"] = "cz.icecars.iot4cps-wp5-CarFleet.Car1"
#             stream["TARGET_SYSTEM"] = "cz.icecars.iot4cps-wp5-CarFleet.Car2"
#             stream["KAFKA_BOOTSTRAP_SERVERS"] = "127.0.0.1:9092"
#             stream["GOST_SERVER"] = "127.0.0.1:8082"
#             stream["FILTER_LOGIC"] = None
#         else:
#             # execute the filter logic to load the variables and functions into the memory
#             if stream.get("FILTER_LOGIC"):
#                 exec(stream.get("FILTER_LOGIC"))
#                 s = f"Loaded custom FILTER_LOGIC: {locals()['ADDITIONAL_ATTRIBUTES']}"
#
#             else:
#                 s = f"No filter logic given, using default."
#                 stream["FILTER_LOGIC"] = ""
#             if logger:
#                 logger.info(s)
#             else:
#                 print(s)
#
#         # stop old container if it exists
#         with hide('output', 'running'), settings(warn_only=True):
#             local(f'docker rm -f {container_name} > /dev/null 2>&1 && echo "Removed container" || true', capture=True)
#
#         # start new container
#         with shell_env(STREAM_NAME=stream_name, SOURCE_SYSTEM=stream["SOURCE_SYSTEM"],
#                        TARGET_SYSTEM=stream["TARGET_SYSTEM"], GOST_SERVER=stream["GOST_SERVER"],
#                        KAFKA_BOOTSTRAP_SERVERS=stream["KAFKA_BOOTSTRAP_SERVERS"], FILTER_LOGIC=stream["FILTER_LOGIC"]):
#             # TODO pass the configs into the blueprint joiner
#             with hide('output', 'running'), settings(warn_only=True):
#                 return local('docker run '
#                              '-dit '
#                              '--network host '
#                              '--restart always '
#                              '-e "STREAM_NAME=$STREAM_NAME" '
#                              '-e "SOURCE_SYSTEM=$SOURCE_SYSTEM" '
#                              '-e "TARGET_SYSTEM=$TARGET_SYSTEM" '
#                              '-e "KAFKA_BOOTSTRAP_SERVERS=$KAFKA_BOOTSTRAP_SERVERS" '
#                              '-e "GOST_SERVER=$GOST_SERVER" '
#                              '-e "FILTER_LOGIC=$FILTER_LOGIC" '
#                              f'--name {container_name} '
#                              'iot4cps/multi-source-stream '
#                              '|| true', capture=True).stdout

def create_client():
    # Try this if it doesn't work within a container
    # https://docker-py.readthedocs.io/en/stable/client.html#client-reference
    # >>> client = docker.DockerClient(base_url='unix://var/run/docker.sock')
    return docker.from_env()


if __name__ == "__main__":
    simple_stream_app = SimpleStreamApp(
        system_name="at.srfg.WeatherService.Stations",
        stream_name="test-stream",
        source_system="at.srfg.WeatherService.Stations",
        target_system="at.srfg.Analytics.MachineAnalytics",
        kafka_bootstrap_servers="127.0.0.1:9092",
        server_uri="127.0.0.1:1908",
        filter_logic="SELECT * FROM * WHERE (quantity = 'temperature_1' AND result < 4) OR (quantity = 'acceleration' AND result > 0.8)",
        verbose=True)
    simple_stream_app.deploy()
    time.sleep(10)
    print(f"simple_stream_app.is_running(): \n{simple_stream_app.is_running()}")
    print(f"simple_stream_app.get_status(): \n{simple_stream_app.get_status()}")
    print(f"simple_stream_app.get_stats(): \n{simple_stream_app.get_stats()}")
    print(f"simple_stream_app.get_logs(20): \n{simple_stream_app.get_logs(20)}")
    simple_stream_app.stop()
