import datetime
import logging
import os
import pandas as pd
import time
import urllib3

from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point, WriteOptions, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# Désactiver les avertissements InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv()  # Charge les variables d'environnement à partir du fichier .env

# Configuration InfluxDB
token = os.getenv('INFLUXDB_TOKEN')
org = os.getenv('ORG')
bucket = os.getenv('BUCKET')
url = os.getenv('URL')

client = InfluxDBClient(url=url, token=token, org=org, verify_ssl=False)

def round_fields(fields, decimals=2):
    for key, value in fields.items():
        if isinstance(value, float):  # Vérifie que c'est bien un float
            fields[key] = round(value, decimals)
    return fields

def write_to_influx(measurement, fields, tags=None, timestamp=None):
    fields = round_fields(fields)  # Arrondir les valeurs des champs
    # write_api = client.write_api(write_options=WriteOptions(batch_size=1000, flush_interval=10_000))
    write_api = client.write_api(write_options=SYNCHRONOUS)
    # Convert timestamp from pandas Timestamp to nanoseconds
    if isinstance(timestamp, pd.Timestamp):
        timestamp_ns = int(timestamp.timestamp() * 1e9)
    else:
        timestamp_ns = int(pd.to_datetime(timestamp).timestamp() * 1e9)

    point = Point(measurement)
    if tags:
        for key, value in tags.items():
            point = point.tag(key, value)
    for key, value in fields.items():
        point = point.field(key, value)
    if timestamp:
        point = point.time(timestamp_ns)
    # logging.info(f"Writing to InfluxDB: {point}")
    try:
        write_api.write(bucket=bucket, record=point)
        # logging.info("Write successful")
    except Exception as e:
        logging.error(f"Error writing to InfluxDB: {e}")

def get_influx_data(database, measurement, start_time, end_time):
    # Connect to InfluxDB
    client_db = InfluxDBClient(url=url, token=token, org=org, verify_ssl=False, database=database)

    # Construct your query
    query = f'SELECT * FROM "{measurement}" WHERE time >= \'{start_time}\' AND time <= \'{end_time}\''

    # Execute the query
    result = client_db.query(query)

    # Convert the result to pandas DataFrame
    df = pd.DataFrame(list(result.get_points()))
    
    # Return the DataFrame
    if not df.empty:
        df['time'] = pd.to_datetime(df['time'])
        df.set_index('time', inplace=True)
    return df

def get_historical_compare_data(database, measurement, days=30):
    # Calculer les dates de début et de fin
    end_time = datetime.datetime.utcnow()
    start_time = end_time - datetime.timedelta(days=days)

    df = get_influx_data(database, measurement, start_time, end_time)
    return df

def test_write():
    write_api = client.write_api(write_options=WriteOptions(batch_size=1, flush_interval=1_000))
    point = Point("trades").tag("type", "test").field("crypto_amount", 1.0).field("fiat_amount", 1000.0).time(int(time.time() * 1e9))
    try:
        write_api.write(bucket=bucket, record=point)
        print("Test write successful")
    except Exception as e:
        print(f"Error during test write: {e}")