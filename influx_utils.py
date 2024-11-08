import os

from influxdb_client import InfluxDBClient, Point, WriteOptions, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# Configuration InfluxDB
# token = os.getenv('INFLUXDB_TOKEN')
token = "Pv1-IbSbvfs5U2_JuPWUGiESke9WU1foTIQ6u03Yk07Vh9d17gQvGwX-bHgWua7LAszYVWrRyv9ubnCTcCE-HA=="
# org = os.getenv('ORG')
org = "Musashi"
# bucket = os.getenv('BUCKET')
bucket = "tradingbot"
# url = os.getenv('URL')
url = "https://192.168.6.98:8086"

client = InfluxDBClient(url=url, token=token, org=org, verify_ssl=False)

def write_to_influx(measurement, fields, tags=None, timestamp=None):
    write_api = client.write_api(write_options=WriteOptions(batch_size=1000, flush_interval=10_000))
    point = Point(measurement)
    if tags:
        for key, value in tags.items():
            point = point.tag(key, value)
    for key, value in fields.items():
        point = point.field(key, value)
    if timestamp:
        point = point.time(timestamp)
    write_api.write(bucket=bucket, record=point)