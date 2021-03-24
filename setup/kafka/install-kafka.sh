#!/usr/bin/env bash
cd $(cd -P -- "$(dirname -- "$0")" && pwd -P)

sudo apt-get update && sudo apt-get install openjdk-8-jre wget -y
export kafka_version=2.7.0
export scala_version=2.13
wget https://archive.apache.org/dist/kafka/${kafka_version}/kafka_${scala_version}-${kafka_version}.tgz
tar -xvzf kafka_${scala_version}-${kafka_version}.tgz
rm kafka_${scala_version}-${kafka_version}.tgz

sudo rm -R /kafka > /dev/null 2>&1 || true
sudo mv kafka_${scala_version}-${kafka_version} /kafka
sudo chmod +x /kafka/bin/*
