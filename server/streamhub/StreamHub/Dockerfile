# FROM anapsix/alpine-java:8u202b08_jdk
FROM java:8
MAINTAINER Christoph Schranz <christoph.schranz@salzburgresearch.at>

ADD target/StreamApp-1.2-jar-with-dependencies.jar /streamApp.jar

# Load environment variables that differs Stream Apps
ENV STREAM_NAME $STREAM_NAME
ENV SOURCE_SYSTEM $SOURCE_SYSTEM
ENV TARGET_SYSTEM $TARGET_SYSTEM
ENV SERVER_URI $SERVER_URI
ENV KAFKA_BOOTSTRAP_SERVERS $KAFKA_BOOTSTRAP_SERVERS
ENV FILTER_LOGIC $FILTER_LOGIC
ENV VERBOSE $VERBOSE

ENTRYPOINT ["java", "-jar", "/streamApp.jar"]
