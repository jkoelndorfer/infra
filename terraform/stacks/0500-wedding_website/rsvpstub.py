#!/usr/bin/python3

# This script is a *stub* to deploy the RSVP Lambda function.

def lambda_handler(event, context):
    return {
        "statusCode": 500,
        "body": {
            "error": {
                "code": "error_function_stub",
                "message": "This is a stub function deployed by Terraform.",
            },
            "response": {},
        },
        "headers": {
            "Content-Type": "application/json",
        },
    }
