import logging
import json
import os
from urllib.parse import quote

from dotenv import load_dotenv
import requests
import pika
from retry import retry

load_dotenv()

host = os.environ.get("AMQP_HOST", False)
if not host:
    print("No AMQP host specified.")
    exit(1)

port = os.environ.get("AMQP_PORT", False)
if not port:
    print("No AMQP port specified.")
    exit(1)

user = os.environ.get("AMQP_USER", False)
if not user:
    print("No AMQP user specified.")
    exit(1)

pwd = os.environ.get("AMQP_PWD", False)
if not pwd:
    print("No AMQP password specified.")
    exit(1)

vhost = os.environ.get("AMQP_VHOST", False)
if not vhost:
    print("No AMQP_VHOST specified.")
    exit(1)

exchange = os.environ.get("AMQP_EXCHANGE", False)
if not exchange:
    print("No AMQP exchange specified.")
    exit(1)

queue = os.environ.get("AMQP_QUEUE", False)
if not queue:
    print("No AMQP queue specified.")
    exit(1)

RESULT_API = "http://svc-tam-result-api"
if os.environ.get("RESULT_API", False):
    RESULT_API = os.environ["RESULT_API"]

# Add Authentication=ActiveDirectoryPassword to use active directory user instead.
conn_string = f"amqp://{user}:{quote(pwd)}@{host}:{port}/{vhost}"


params = pika.URLParameters(conn_string)
connection = pika.BlockingConnection(params)
channel = connection.channel()  # start a channel

channel.exchange_declare(exchange=exchange, exchange_type="fanout", durable=True)
channel.queue_declare(
    queue=queue, durable=True, arguments={"x-queue-type": "quorum"}
)  # Declare a queue
channel.queue_bind(exchange=exchange, queue=queue)


@retry(tries=3, delay=2, logger=logging.getLogger())
def post_msg(body):
    """
    Post message to tam-result-api

    """
    url = f"{RESULT_API}"
    data = json.loads(body)

    post_data = {
        "add_date": data.get("date", ""),
        "filename": data.get("file", ""),
        "integration": data.get("integration", ""),
        "share": data.get("share", ""),
        "host": data.get("host", ""),
        "environment": data.get("environment", ""),
        "platform": data.get("platform", ""),
        "is_source": "1" if data.get("is_source") else "0",
        "owner": data.get("owner", "")
    }

    try:
        r = requests.post(url=url, json=post_data)  # auth=auth?
        r.raise_for_status()
    except requests.HTTPError as http_err:
        raise Exception(f"Error posting to RESULT_API: HTTP error {http_err}")
    except Exception as err:
        raise Exception(f"Error posting to RESULT_API: {err}")
    return True


def on_message(current_channel, method_frame, header_frame, body):
    if post_msg(body):
        current_channel.basic_ack(delivery_tag=method_frame.delivery_tag)
    else:
        logging.error(f"Could not post message to API. Body: {body}")


# set up subscription on the queue
channel.basic_consume(queue, on_message)

# start consuming (blocks)
channel.start_consuming()
# Close the channel and the connection
channel.close()
connection.close()
