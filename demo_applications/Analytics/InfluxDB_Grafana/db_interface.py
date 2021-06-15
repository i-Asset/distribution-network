import json
from influxdb import InfluxDBClient

system_name = "at.datahouse.Analytics.RoadAnalytics"

# create InfluxDB Connector and create database if not already done
client = InfluxDBClient('localhost', 8086, 'root', 'root', system_name)
client.create_database(system_name)
print(client.get_list_database())

result = client.query(f'select count(*) from "{system_name}";')

for res in result.get_points():
    print(res)
