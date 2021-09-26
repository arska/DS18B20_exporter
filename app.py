import argparse
import logging
import os
import time

from dotenv import load_dotenv
from prometheus_client import REGISTRY, Gauge, pushadd_to_gateway, start_http_server
from w1thermsensor import W1ThermSensor

"""Parse arguments from command line"""
PARSER = argparse.ArgumentParser(description="Export DS18B20 temperature to prometheus")
PARSER.add_argument(
    "-n",
    "--noop",
    help="dont actually post/change anything, just log what would have been posted. "
    "Mostly relevant with --pushgateway",
    action="store_true",
    default=False,
)
PARSER.add_argument(
    "-v", "--verbose", help="set logging to debug", action="store_true", default=False,
)
PARSER.add_argument(
    "-p",
    "--pushgateway",
    help="send metrics prometheus pushgateway and exit. Can also be defined in "
    "PROM_GATEWAY env variable",
    default=False,
)
# PARSER.add_argument("sensors", help="DS18B20 1wire bus IDs to query (or from "
#                                   "PROM_SENSORS env variable or all if "
#                                   "empty)",
#                     nargs="*")
ARGS = PARSER.parse_args()

LOGFORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

if ARGS.verbose:
    logging.basicConfig(level=logging.DEBUG, format=LOGFORMAT)
else:
    logging.basicConfig(level=logging.INFO, format=LOGFORMAT)
    logging.getLogger("requests.packages.urllib3.connectionpool").setLevel(
        logging.WARNING
    )

logging.debug("starting with arguments: %s", ARGS)

load_dotenv()
gauges = {}
# sensors = ARGS.sensors if ARGS.sensors else os.environ.get("PROM_SENSORS").split() if \
#     os.environ.get("PROM_SENSORS", False) else W1ThermSensor.get_available_sensors()
for sensor in W1ThermSensor.get_available_sensors():
    helptext = "DS18B20 sensor with id " + sensor.id + " temperature degC"
    valuefunc = lambda a=sensor: a.get_temperature()
    if not gauges.get(sensor.id, False):
        gauges[sensor.id] = Gauge(
            "DS18B20_temperature", helptext, ["id"], registry=REGISTRY
        )
    gauges[sensor.id].labels(id=sensor.id).set_function(valuefunc)


if ARGS.pushgateway or os.environ.get("PROM_GATEWAY", False):
    gateway = ARGS.pushgateway if ARGS.pushgateway else os.environ.get("PROM_GATEWAY")
    if not ARGS.noop:
        pushadd_to_gateway(gateway, registry=REGISTRY, job="DS18B20_exporter")
else:
    start_http_server(os.environ.get("listenport", 8080), registry=REGISTRY)
    while True:
        time.sleep(1)
