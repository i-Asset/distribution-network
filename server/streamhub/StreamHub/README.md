# StreamAppEngine

## Deployment Notes

### Testing the filter logic

Testing the stream engine with `NodeTester.java`. 
Many filtering examples are in the code.


### Testing with Streams

In `StreamAppEngine` an the environment variables are passed.
This are the variables:
```
STREAM_NAME="test-stream"
SOURCE_SYSTEM=at.srfg.WeatherService.Stations
TARGET_SYSTEM=at.srfg.Analytics.MachineAnalytics
KAFKA_BOOTSTRAP_SERVERS=127.0.0.1:9092
SERVER_URI=127.0.0.1:1908
FILTER_LOGIC="SELECT * FROM * WHERE (quantity = 'temperature_1' AND result < 4) OR (quantity = 'acceleration' AND result > 0.8)"
```

Using them, the Application can be started.


### Deploying the jar file

To build a *jar* file, open the **Maven** sidebar and run in `Lifecycle` the commands
`clean` and `install`. Both should exit with the info `BUILD SUCCESS`.

Afterwards, the **jar** file can be executed using:
```bash
java -jar target/streamApp-1.2-jar-with-dependencies.jar --STREAM_NAME test-jar --SOURCE_SYSTEM at.srfg.WeatherService.Stations --TARGET_SYSTEM at.srfg.Analytics.MachineAnalytics --KAFKA_BOOTSTRAP_SERVERS 127.0.0.1:9092 --SERVER_URI 127.0.0.1:1908 --FILTER_LOGIC "SELECT * FROM * WHERE (quantity = 'temperature_1' AND result < 4) OR (quantity = 'acceleration' AND result > 0.8)"
```

### Deploying inside a Docker Container

The most practical way to deploy the application is to build a docker container for the jar file.
In order to work correctly, the Kafka config needs an additional line:

```
advertised.listeners=PLAINTEXT://[your-ip]:9092
```
where `[your-ip]` is the IP Address of your Kafka Bootstrap server that is accessible from other nodes,
i.e., not `localhost`. The parameter `listeners` can stay on `localhost`, if wished. 

It has been shown, that the advertised listeners don't have to be configured. Localhost suffices if the parameter
`network_mode: host` is given in the `docker-compose.yml`.

```bash
docker-compose up --build -d
docker-compose logs -f
```

### Testing via the GUI

This step requires a running platform as explained in the `server` directory.
Then, copy the jar file from `demo_applications/stream_apps/target` to `server/views`.
Restart the platform and go to *streams* and click on *start stream*.

