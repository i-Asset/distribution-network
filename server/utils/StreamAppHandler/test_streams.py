import time

try:
    from stream_app_handler import SimpleStreamApp
except ImportError:
    from .stream_app_handler import SimpleStreamApp

def simple_stream_app():
    print(f"\n################# Simple Stream App #################\n")
    stream = {
        "system_name": "at.srfg.WeatherService.Stations",
        "stream_name": "test-stream",
        "source_system": "at.srfg.WeatherService.Stations",
        "target_system": "at.srfg.Analytics.MachineAnalytics",
        "kafka_bootstrap_servers": "127.0.0.1:9092",
        "server_uri": "127.0.0.1:1908",
        "filter_logic": "SELECT * FROM * WHERE (quantity = 'temperature_1' AND result < 4) OR (quantity = 'acceleration' AND result > 0.8)",
        "verbose": True
    }
    simple_stream_app = SimpleStreamApp(**stream)
    print(f"simple_stream_app.deploy(): Deploy stream-app and wait to settle.")
    simple_stream_app.deploy()
    time.sleep(15)
    print(f"simple_stream_app.is_running(): \n{simple_stream_app.is_running()}")
    assert simple_stream_app.is_running()
    print(f"simple_stream_app.get_status(): \n{simple_stream_app.get_status()}")
    print(f"simple_stream_app.get_stats(): \n{simple_stream_app.get_stats()}")
    print(f"simple_stream_app.get_logs(20): \n{simple_stream_app.get_logs(20)}")

    print(f"simple_stream_app.stop(): Stop stream-app and wait to settle.")
    simple_stream_app.stop()
    time.sleep(5)
    print(f"simple_stream_app.is_running(): \n{simple_stream_app.is_running()}")
    assert not simple_stream_app.is_running()


def multi_source_stream_app():
    print(f"\n############### Multi-Source Stream App ###############\n")

    stream = dict()
    stream["KAFKA_BOOTSTRAP_SERVERS"] = "127.0.0.1:9094"
    stream["GOST_SERVER"] = "127.0.0.1:8082"


    print("Testing a multi-source stream app with default filter logic")
    stream["SOURCE_SYSTEM"] = "cz.icecars.iot4cps-wp5-CarFleet.Car1,cz.icecars.iot4cps-wp5-CarFleet.Car2"
    stream["TARGET_SYSTEM"] = "cz.icecars.iot4cps-wp5-CarFleet.Car2"
    stream["FILTER_LOGIC"] = None

    print(fab_streams.local_deploy_multi(system_uuid="1234", stream_name="another-stream", stream=stream))
    time.sleep(5)
    print(fab_streams.local_is_deployed(system_uuid="1234", stream_name="another-stream"))
    response1 = fab_streams.local_logs(system_uuid="1234", stream_name="another-stream")
    response2 = fab_streams.local_stats(system_uuid="1234", stream_name="another-stream")
    print(response1)
    print(response2)
    print(fab_streams.local_down(system_uuid="1234", stream_name="another-stream"))
    print(fab_streams.local_is_deployed(system_uuid="1234", stream_name="another-stream"))


if __name__ == "__main__":
    simple_stream_app()
