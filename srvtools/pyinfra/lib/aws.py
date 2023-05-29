"""
lib/aws
-------

This module contains code for working with AWS.
"""

_boto_session = None
_boto_credentials = None
_ssm_client = None


def _init_boto3():
    """
    Initializes boto3.

    Because initializing boto3 is expensive, we only do it when needed.
    """
    import boto3
    import boto3.session
    global _boto_session
    global _boto_credentials
    if _boto_session is None:
        _boto_session = boto3.session.Session()
        _boto_credentials = _boto_session.get_credentials()


# TODO: Use service-specific AWS credentials.
def aws_access_key_id():
    """
    Returns an AWS access key ID that can be used for interacting with AWS.
    """
    _init_boto3()
    assert _boto_credentials is not None
    return _boto_credentials.access_key


def aws_secret_access_key():
    """
    Returns an AWS access secret access key that can be used for interacting with AWS.
    The returned secret access key will correspond to the access key ID returned by
    aws_secret_access_key.
    """
    _init_boto3()
    assert _boto_credentials is not None
    return _boto_credentials.secret_key


# TODO: Support StringList? I don't use StringList anywhere.
def ssm_parameter_value(name: str) -> str:
    """
    Gets the value of an AWS SSM Parameter with the given name.
    """
    import boto3

    # boto3 clients are expensive to create, so only create it if we need to.
    global _ssm_client
    if _ssm_client is None:
        _ssm_client = boto3.client("ssm")
    response = _ssm_client.get_parameter(Name=name, WithDecryption=True)
    return response["Parameter"]["Value"]
