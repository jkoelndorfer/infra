#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

import boto3

DNS_TTL = 30
ENV_TAG = "johnk:env"
DNS_TAG = "johnk:dns"
REGION = 'us-east-1'
boto3.setup_default_session(region_name=REGION)


def lambda_handler(event, context):
    if event.get("detail-type", None) == "EC2 Instance State-change Notification":
        # A CloudWatch event fired indicating an EC2 instance state has changed.
        #
        # We should handle updating instance DNS records.
        return handle_ec2_instance_dyndns(event, context)
    else:
        log("Unable to determine how to handle event; quitting")
        return


def handle_ec2_instance_dyndns(event, context):
    if not handle_ec2_instance_event(event):
        log("Event will not be handled; quitting")
        return

    instance_id = event_ec2_instance_id(event)
    log(f"Got event for instance {instance_id}")

    desired_dns_name = determine_ec2_instance_desired_dns_name(instance_id)
    if desired_dns_name is None:
        log(f"Could not determine desired DNS name for {instance_id}; quitting")
        return

    r53 = boto3.client("route53")
    zones = r53.list_hosted_zones()["HostedZones"]
    hosted_zone_id = determine_hosted_zone_id_of(desired_dns_name, zones)
    if hosted_zone_id is None:
        log(f"Could not determine hosted zone ID of {desired_dns_name}")
        exit(1)

    instance_ip_address = determine_ec2_instance_ip_address(instance_id)
    log(f"IP address for instance {instance_id} is {instance_ip_address}; updating")
    r53.change_resource_record_sets(
        HostedZoneId=hosted_zone_id,
        ChangeBatch={
            "Comment": "dyndns update",
            "Changes": [{
                "Action": "UPSERT",
                "ResourceRecordSet": {
                    "Name": desired_dns_name,
                    "Type": "A",
                    "TTL": DNS_TTL,
                    "ResourceRecords": [{"Value": instance_ip_address}]
                }
            }]
        }
    )


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


def event_ec2_instance_id(event):
    return event["detail"]["instance-id"]


def handle_ec2_instance_event(event):
    if event["detail"]["state"] != "running":
        log(f"Instance state is not 'running'; event will not be handled")
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
        log(f"Could not find tag {ENV_TAG} on instance {ec2_instance_id}; assuming 'prod'")
        return lambda_fn_env == "prod"
    if instance_env == lambda_fn_env:
        log("Instance environment matches")
        return True
    else:
        log("Instance environment does not match")
        return False


def log(msg):
    print(msg, file=sys.stderr)


def normalize_dns_name(dns_name):
    return dns_name.rstrip(".")


def main(argv) -> int:
    event_type = argv[0]
    if event_type == "ec2":
        # Handles EC2 instance state change events, updating the record in the instance's
        # "johnk:dns" tag with the instance's public IP address.
        return main_ec2_instance(argv[1:])
    else:
        log(f"Unknown event_type {event_type}")
        sys.exit(1)


def main_ec2_instance(argv) -> int:
    if len(argv) < 1:
        print("You must pass the ID of an EC2 instance to test against, e.g. i-0febee66103987423", file=sys.stderr)
        return 1
    os.environ["env_name"] = "dev"
    ec2_instance_id = argv[0]
    sts_client = boto3.client("sts")
    account_id = sts_client.get_caller_identity()["Account"]
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


if __name__ == "__main__":
    log("Running in local testing mode.")
    main(sys.argv[1:])
