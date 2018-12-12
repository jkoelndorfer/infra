#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys

import boto3

DNS_TTL = 30
DNS_TAG = "johnk:dns"
REGION = 'us-east-1'
boto3.setup_default_session(region_name=REGION)


def lambda_handler(event, context):
    if event["detail"]["state"] != "running":
        return
    instance_id = event["detail"]["instance-id"]
    desired_dns_name = determine_desired_dns_name(instance_id)
    if desired_dns_name is None:
        return

    r53 = boto3.client("route53")
    zones = r53.list_hosted_zones()["HostedZones"]
    hosted_zone_id = determine_hosted_zone_id_of(desired_dns_name, zones)
    if hosted_zone_id is None:
        print(f"You not determine hosted zone ID of {desired_dns_name}", file=sys.stderr)
        exit(1)

    instance_ip_address = determine_instance_ip_address(instance_id)
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


def determine_desired_dns_name(ec2_instance_id):
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


def determine_instance_ip_address(instance_id):
    ec2 = boto3.client("ec2")
    result = ec2.describe_instances(
        Filters=[{
            "Name": "instance-id",
            "Values": [instance_id]
        }]
    )
    public_ip = result["Reservations"][0]["Instances"][0]["PublicIpAddress"]
    return public_ip


def normalize_dns_name(dns_name):
    return dns_name.rstrip(".")


def main():
    if len(sys.argv) < 2:
        print("You must pass the ID of an EC2 instance to test against, e.g. i-0febee66103987423", file=sys.stderr)
        exit(1)
    ec2_instance_id = sys.argv[1]
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


# For local testing.
if __name__ == "__main__":
    main()
