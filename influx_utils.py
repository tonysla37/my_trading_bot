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
trades_measurement = "trades"
bt_trades_measurement = "bt_trades"
indicators_measurement = "indicators"

###################### GENERIC FUNCTIONS ######################
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

###################### TESTS FUNCTIONS ######################
def test_write():
    write_api = client.write_api(write_options=WriteOptions(batch_size=1, flush_interval=1_000))
    point = Point("trades").tag("type", "test").field("crypto_amount", 1.0).field("fiat_amount", 1000.0).time(int(time.time() * 1e9))
    try:
        write_api.write(bucket=bucket, record=point)
        print("Test write successful")
    except Exception as e:
        print(f"Error during test write: {e}")

###################### TRADES FUNCTIONS ######################
def write_bt_trade_to_influx(price, wallet, fiat_amount, crypto_amount, close, trade_type, timestamp):
    tags = {"type": trade_type}
    fields = {
                "price": price,
                "wallet": wallet,
                "fiat_amount": fiat_amount,
                "crypto_amount": crypto_amount,
                "close": close
    }
    write_to_influx(bt_trades_measurement, fields, tags, timestamp)

def get_bt_trades(start_time, end_time):
    query = f'''
    from(bucket: "{bucket}")
    |> range(start: {start_time.isoformat()}..{end_time.isoformat()})
    |> filter(fn: (r) => r._measurement == "{bt_trades_measurement}")
    '''
    
    result = client.query_api().query(query, org=org)
    
    # Convertir le résultat en DataFrame
    trades = []
    for table in result:
        for record in table.records:
            trades.append({
                "time": record.get_time(),
                "type": record.values.get("type"),
                "price": record.get_value_by_key("price"),
                "wallet": record.get_value_by_key("wallet"),
                "fiat_amount": record.get_value_by_key("fiat_amount"),
                "crypto_amount": record.get_value_by_key("crypto_amount"),
                "close": record.get_value_by_key("close"),
            })

    return pd.DataFrame(trades)

### UTILISATION ###
# Obtenir des données d'un intervalle
# start_time = datetime.utcnow() - timedelta(hours=1)
# end_time = datetime.utcnow()
# trades_df = get_bt_trades(start_time, end_time)

# # Afficher les transactions récupérées
# print(trades_df)

def write_trade_to_influx(fields, trade_type, timestamp):
    write_to_influx(measurement=trades_measurement, fields=fields, tags={"type": trade_type}, timestamp=timestamp)

def get_trades(start_time, end_time):
    query = f'''
    from(bucket: "{bucket}")
    |> range(start: {start_time.isoformat()}..{end_time.isoformat()})
    |> filter(fn: (r) => r._measurement == "{trades_measurement}")
    '''
    
    result = client.query_api().query(query, org=org)
    
    # Convertir le résultat en DataFrame
    trades = []
    for table in result:
        for record in table.records:
            trades.append({
                "time": record.get_time(),
                "type": record.values.get("type"),
                "price": record.get_value_by_key("price"),
                "wallet": record.get_value_by_key("wallet"),
                "fiat_amount": record.get_value_by_key("fiat_amount"),
                "crypto_amount": record.get_value_by_key("crypto_amount"),
                "close": record.get_value_by_key("close"),
            })

    return pd.DataFrame(trades)


###################### INDICATORS FUNCTIONS ######################
def write_indicator_to_influx(fields, indicator, timestamp):
    write_to_influx(measurement=indicators_measurement, fields=fields, tags={"type": indicator}, timestamp=timestamp)