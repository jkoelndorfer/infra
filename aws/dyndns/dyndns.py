#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from base64 import b64decode, b64encode
from datetime import datetime, timezone
from http import HTTPStatus
import json
import logging
import os
import random
import string
import sys
from traceback import format_exception

import boto3


def make_logger():
    logger = logging.getLogger("dyndns")
    handler = logging.StreamHandler()
    handler.setFormatter(JSONLogFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    return logger


class JSONLogFormatter(logging.Formatter):

    @classmethod
    def _timestamp(cls) -> str:
        now = datetime.now(tz=timezone.utc)
        return now.isoformat(timespec="seconds")

    def format(self, record: logging.LogRecord) -> str:
        json_log = {
            "@timestamp": self._timestamp(),
            "level": record.levelname,
            "filename": record.pathname,
            "lineno": record.lineno,
            "msg": record.getMessage(),
        }
        record_exc = record.exc_info
        if record_exc is not None:
            json_log["exc"] = "".join(format_exception(*record_exc))
        return json.dumps(json_log)


def lambda_handler(event, context):
    if event.get("detail-type", None) == "EC2 Instance State-change Notification":
        # A CloudWatch event fired indicating an EC2 instance state has changed.
        #
        # We should handle updating instance DNS records.
        return handle_ec2_instance_dyndns(event, context)
    elif event.get("requestContext", {}).get("httpMethod", None) is not None:
        # We got an event from API Gateway. We should handle this event as
        # a client-invoked "dyndns2" protocol request. For more information, see:
        # https://sourceforge.net/p/ddclient/wiki/protocols/#dyndns2
        try:
            return handle_dyndns2(event, context)
        except Exception as e:
            logger.exception(str(e))
            return api_gw_response(HTTPStatus.INTERNAL_SERVER_ERROR, "internal server error")
    else:
        logger.error("Unable to determine how to handle event; quitting")
        return


def handle_ec2_instance_dyndns(event, context):
    if not handle_ec2_instance_event(event):
        logger.info("Event will not be handled; quitting")
        return

    instance_id = event_ec2_instance_id(event)
    logger.info(f"Got event for instance {instance_id}")

    desired_dns_name = determine_ec2_instance_desired_dns_name(instance_id)
    if desired_dns_name is None:
        logger.error(f"Could not determine desired DNS name for {instance_id}; quitting")
        return

    instance_ip_address = determine_ec2_instance_ip_address(instance_id)
    logger.info(f"IP address for instance {instance_id} is {instance_ip_address}; updating")
    update_dns("ec2", desired_dns_name, instance_ip_address)


def handle_dyndns2(event, context):
    query_params = event.get("queryStringParameters", None) or {}

    hostname = query_params.get("hostname", None)
    ip = query_params.get("myip", None)

    err_msg = None
    if hostname is None and ip is None:
        err_msg = "hostname and myip must be specified in query parameters"
    elif hostname is None:
        err_msg = "hostname must be specified in query parameters"
    elif ip is None:
        err_msg = "myip must be specified in query parameters"
    if err_msg is not None:
        return api_gw_response(HTTPStatus.BAD_REQUEST, err_msg)

    headers = event.get("headers", None) or {}  # API Gateway sets headers to `null` if there are none. Why?
    try:
        auth_header_key = [i for i in headers.keys() if i.lower() == "authorization"][0]
        auth_header = headers[auth_header_key]
    except IndexError:
        auth_header = None
    authorized = dyndns2_authorized(auth_header, hostname)
    if not authorized:
        return api_gw_response(HTTPStatus.UNAUTHORIZED, "not authorized")
    try:
        update_dns("dyndns", hostname, ip)
    except Exception as e:
        logger.exception(str(e))
        return api_gw_response(HTTPStatus.INTERNAL_SERVER_ERROR, "internal server error")
    return api_gw_response(HTTPStatus.OK, "dns update successful")


def api_gw_response(code, message):
    return {
        "statusCode": code.value,
        "body": json.dumps({"code": code, "message": message, "source": "dyndns.py"}),
        "headers": {"Content-Type": "application/json"},
    }


def determine_ec2_instance_desired_dns_name(ec2_instance_id):
    ec2 = boto3.client("ec2")
    result = ec2.describe_tags(
        Filters=[
            {"Name": "key", "Values": [DNS_TAG]},
            {"Name": "resource-id", "Values": [ec2_instance_id]}
        ],
    )
    try:
        dns_name = result["Tags"][0]["Value"]
    except IndexError:
        # Didn't find the tag. The instance probably isn't tagged properly.
        dns_name = None
    return dns_name


def determine_hosted_zone_id_of(dns_name, hosted_zones):
    dns_name = normalize_dns_name(dns_name)
    dns_name_parts = dns_name.split(".")
    for i in range(0, len(dns_name_parts)):
        tested_name = ".".join(dns_name_parts[i:])
        for z in hosted_zones:
            if tested_name == normalize_dns_name(z["Name"]):
                return z["Id"].split("/")[-1]
    return None


def determine_ec2_instance_ip_address(instance_id):
    ec2 = boto3.client("ec2")
    result = ec2.describe_instances(
        Filters=[{
            "Name": "instance-id",
            "Values": [instance_id]
        }]
    )
    public_ip = result["Reservations"][0]["Instances"][0]["PublicIpAddress"]
    return public_ip


def dyndns2_authorized(auth_header, hostname):
    if auth_header is None:
        return False

    logger.debug(f"auth header is '{auth_header}'")
    try:
        auth_type, auth_b64 = auth_header.strip().split(" ")
        if auth_type != "Basic":
            logger.debug("Authorization header not of type 'Basic'")
            return False

        auth = b64decode(auth_b64.encode("ascii")).decode("utf-8")
        username, password = auth.split(":", 2)
    except Exception:
        # Authorization header is probably invalid.
        logger.exception("Failed parsing authorization header")
        return False

    if username is None or password is None:
        return False

    # TODO: Store the password more securely.
    authorization_cfg = json.loads(os.environ["DYNDNS_AUTHORIZATION"])
    user_auth_cfg = authorization_cfg.get(username, {})
    if user_auth_cfg.get("password", None) != password:
        return False

    if hostname not in user_auth_cfg.get("dns_names", []):
        return False

    return True


def event_ec2_instance_id(event):
    return event["detail"]["instance-id"]


def handle_ec2_instance_event(event):
    if event["detail"]["state"] != "running":
        logger.info(f"Instance state is not 'running'; event will not be handled")
        return False
    ec2_instance_id = event_ec2_instance_id(event)
    lambda_fn_env = os.environ["env_name"]
    ec2 = boto3.client("ec2")
    result = ec2.describe_tags(
        Filters=[
            {"Name": "key", "Values": [ENV_TAG]},
            {"Name": "resource-id", "Values": [ec2_instance_id]}
        ],
    )
    try:
        instance_env = result["Tags"][0]["Value"]
    except IndexError:
        logger.info(f"Could not find tag {ENV_TAG} on instance {ec2_instance_id}; assuming 'prod'")
        return lambda_fn_env == "prod"
    if instance_env == lambda_fn_env:
        logger.debug("Instance environment matches")
        return True
    else:
        logger.debug("Instance environment does not match")
        return False


def normalize_dns_name(dns_name):
    return dns_name.rstrip(".")


def main(argv) -> int:
    event_type = argv[0]
    if event_type == "ec2":
        # Handles EC2 instance state change events, updating the record in the instance's
        # "johnk:dns" tag with the instance's public IP address.
        return main_ec2_instance(argv[1:])
    elif event_type == "dyndns2":
        return main_dyndns2(argv[1:])
    else:
        logger.error(f"Unknown event_type {event_type}")
        sys.exit(1)


def main_dyndns2(argv) -> int:
    # See https://docs.aws.amazon.com/lambda/latest/dg/services-apigateway.html
    # for documentation showing an example API Gateway event.
    #
    # The mock event below is missing a bunch of stuff, but should be everything
    # that is needed to fill a dynamic DNS request.
    hostname, ip = argv
    api_id = "deadbeef"
    pw_chars = string.ascii_letters + string.digits
    localtest_user = "localtest"
    localtest_password = ''.join(random.choice(pw_chars) for i in range(20))

    localtest_http_auth = "Basic " + b64encode(
        localtest_user.encode("ascii") + b":" + localtest_password.encode("ascii")
    ).decode("ascii")

    os.environ["DYNDNS_AUTHORIZATION"] = json.dumps({
        "localtest": {
            "password": localtest_password,
            "dns_names": ["dyndns-localtest.johnk.io"]
        }
    })
    mock_api_gw_event = {
        "path": "/dyndns",
        "headers": {
            "Accept": "application/json",
            "Authorization": localtest_http_auth,
            "Host": f"{api_id}.execute-api.{REGION}.amazonaws.com",
        },
        "requestContext": {
            "accountId": account_id,
            "requestId": "41b45ea3-70b5-11e6-b7bd-69b5aaebc7d9",
            "httpMethod": "GET",
            "apiId": f"{api_id}",
        },
        "queryStringParameters": {
            "hostname": hostname,
            "myip": ip,
        },
    }
    lambda_handler(mock_api_gw_event, None)
    return 0


def main_ec2_instance(argv) -> int:
    if len(argv) < 1:
        print("You must pass the ID of an EC2 instance to test against, e.g. i-0febee66103987423", file=sys.stderr)
        return 1
    os.environ["env_name"] = "dev"
    ec2_instance_id = argv[0]
    mock_cloudwatch_event = {
        "id": "7bf73129-1428-4cd3-a780-95db273d1602",
        "detail-type": "EC2 Instance State-change Notification",
        "source": "aws.ec2",
        "account": account_id,
        "time": "2015-11-11T21:29:54Z",
        "region": REGION,
        "resources": [
            f"arn:aws:ec2:{REGION}:{account_id}:instance/{ec2_instance_id}"
        ],
        "detail": {
            "instance-id": ec2_instance_id,
            "state": "running"
        }
    }
    lambda_handler(mock_cloudwatch_event, None)
    return 0


def update_dns(update_type, dns_name, ip):
    zones = r53.list_hosted_zones()["HostedZones"]
    hosted_zone_id = determine_hosted_zone_id_of(dns_name, zones)
    if hosted_zone_id is None:
        logger.error(f"Could not determine hosted zone ID of {dns_name}")
        raise Exception(f"Could not determine hosted zone ID of {dns_name}")

    logger.info(f"Updating record {dns_name} of zone ID {hosted_zone_id} -> {ip}")
    r53.change_resource_record_sets(
        HostedZoneId=hosted_zone_id,
        ChangeBatch={
            "Comment": f"dyndns update -- {update_type}",
            "Changes": [{
                "Action": "UPSERT",
                "ResourceRecordSet": {
                    "Name": dns_name,
                    "Type": "A",
                    "TTL": DNS_TTL,
                    "ResourceRecords": [{"Value": ip}]
                }
            }]
        }
    )


DNS_TTL = 30
ENV_TAG = "johnk:env"
DNS_TAG = "johnk:dns"
REGION = 'us-east-1'
boto3.setup_default_session(region_name=REGION)

r53 = boto3.client("route53")
sts_client = boto3.client("sts")
account_id = sts_client.get_caller_identity()["Account"]
logger = make_logger()

if __name__ == "__main__":
    logger.info("Running in local testing mode.")
    main(sys.argv[1:])
