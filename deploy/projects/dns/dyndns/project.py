"""
projects.dns.dyndns.project
===========================

This module contains the InfrastructureProject for dynamic DNS.
"""

from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path

from pulumi import AssetArchive, export, FileAsset, Output, ResourceOptions
import pulumi_aws as aws
import pulumi_random as random

from infralib import (
    DeploymentTarget,
    Environment,
    InfrastructureProject,
    InfrastructureStack,
    StackOutputResolver,
)

from ..zones import DNSZonesProject

_FUNCTION_DIR = Path(__file__).parent / "function"


@dataclass(frozen=True)
class DynDNSClient:
    """
    Everything a client needs to keep the dynamic DNS record up to date.
    """

    # The fully-qualified name of the record the client updates.
    hostname: str

    # A name server that is authoritative for the record. Clients query it to
    # find out whether an update is needed, bypassing any caching or split-horizon
    # resolvers.
    name_server: str

    # The URL of the update endpoint, without query parameters.
    url: str

    # The credentials the client authenticates to the update endpoint with.
    username: str
    password: str = field(repr=False)


class DNSDynDNSProject(InfrastructureProject):
    """
    Project that provides dynamic DNS for the apex of the homelab domain.

    A Lambda function in the account that owns the domain's zone is exposed through
    a function URL. The homelab router calls it with the dyndns2 protocol whenever
    its public address changes.

    The A record itself is not managed by Pulumi. The function creates it on its
    first update, and Pulumi would otherwise revert every update.
    """

    name = "dns.dyndns"
    domain_id = "homelab"
    username = "homelab-router"
    ttl = 60

    @classmethod
    def dependencies(cls, target: DeploymentTarget) -> list[InfrastructureStack]:
        return [DNSZonesProject.stack(DeploymentTarget(Environment.PROD, None))]

    @classmethod
    def deployment_targets(cls) -> list[DeploymentTarget]:
        # dns.zones only provisions a zone for the homelab domain in production.
        return [DeploymentTarget(Environment.PROD, None)]

    @classmethod
    def client(cls, outputs: StackOutputResolver) -> DynDNSClient:
        """
        Returns the configuration a client needs to update the record, given a
        function that resolves stack outputs.
        """
        o = outputs(cls.stack(DeploymentTarget(Environment.PROD, None)))
        return DynDNSClient(
            hostname=o["hostname"].value,
            name_server=o["name_server"].value,
            url=o["url"].value,
            username=o["username"].value,
            password=o["password"].value,
        )

    def pulumi_program(self) -> None:
        env = self.dctx.target.environment
        hostname = self.dctx.config.domains[self.domain_id].domain_for(self.dctx.target)

        # The function is deployed into whichever account owns the zone, so its
        # role never needs to cross an account boundary.
        zone, provider = DNSZonesProject.lookup_zone(self.dctx, hostname)
        aws_opts = ResourceOptions(provider=provider)

        password = random.RandomPassword(
            "password",
            length=48,
            lower=True,
            upper=True,
            numeric=True,
            special=False,
            opts=ResourceOptions(provider=self.dctx.provider_factory.random_provider()),
        )

        log_group = aws.cloudwatch.LogGroup(
            "dyndns",
            name=f"/aws/lambda/{env}-dyndns",
            retention_in_days=90,
            opts=aws_opts,
        )
        role = aws.iam.Role(
            "dyndns",
            name=f"{env}-dyndns",
            description="Permits the dyndns function to update one DNS record.",
            assume_role_policy=Output.json_dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"Service": "lambda.amazonaws.com"},
                            "Action": "sts:AssumeRole",
                        }
                    ],
                }
            ),
            opts=aws_opts,
        )
        role_policy = aws.iam.RolePolicy(
            "dyndns",
            name="dyndns",
            role=role.id,
            policy=Output.json_dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        self._record_update_statement(zone.zone_id, hostname),
                        {
                            "Sid": "WriteLogs",
                            "Effect": "Allow",
                            "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
                            "Resource": Output.concat(log_group.arn, ":*"),
                        },
                    ],
                }
            ),
            opts=aws_opts,
        )

        function = aws.lambda_.Function(
            "dyndns",
            name=f"{env}-dyndns",
            description=f"Dynamic DNS for {hostname}",
            runtime=aws.lambda_.Runtime.PYTHON3D14,
            architectures=["arm64"],
            handler="dyndns.lambda_handler",
            code=AssetArchive(
                {"dyndns.py": FileAsset(str(_FUNCTION_DIR / "dyndns.py"))}
            ),
            role=role.arn,
            memory_size=128,
            timeout=10,
            environment=aws.lambda_.FunctionEnvironmentArgs(
                variables={
                    "DYNDNS_HOSTNAME": hostname,
                    "DYNDNS_ZONE_ID": zone.zone_id,
                    "DYNDNS_TTL": str(self.ttl),
                    "DYNDNS_USERNAME": self.username,
                    "DYNDNS_PASSWORD_SHA256": password.result.apply(
                        lambda p: sha256(p.encode("utf-8")).hexdigest()
                    ),
                },
            ),
            logging_config=aws.lambda_.FunctionLoggingConfigArgs(
                log_format="JSON",
                log_group=log_group.name,
                application_log_level="INFO",
                system_log_level="WARN",
            ),
            opts=aws_opts.merge(ResourceOptions(depends_on=[role_policy])),
        )

        # The function authenticates requests itself, because routers speak HTTP
        # Basic authentication, not SigV4.
        function_url = aws.lambda_.FunctionUrl(
            "dyndns",
            function_name=function.name,
            authorization_type="NONE",
            opts=aws_opts,
        )

        # Public function URLs need both permissions [1].
        #
        # [1]: https://docs.aws.amazon.com/lambda/latest/dg/urls-auth.html#urls-auth-none
        aws.lambda_.Permission(
            "dyndns_url",
            function=function.name,
            action="lambda:InvokeFunctionUrl",
            principal="*",
            function_url_auth_type="NONE",
            statement_id="FunctionURLAllowPublicAccess",
            opts=aws_opts,
        )
        aws.lambda_.Permission(
            "dyndns_url_invoke",
            function=function.name,
            action="lambda:InvokeFunction",
            principal="*",
            invoked_via_function_url=True,
            statement_id="FunctionURLAllowInvokeAction",
            opts=aws_opts,
        )

        export("hostname", hostname)
        export("name_server", zone.primary_name_server)
        export("url", function_url.function_url)
        export("username", self.username)
        export("password", password.result)

    @classmethod
    def _record_update_statement(cls, zone_id: str, hostname: str) -> dict[str, object]:
        """
        Returns an IAM policy statement permitting only UPSERTs of the A record at
        hostname [1].

        [1]: https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/specifying-rrset-conditions.html
        """
        # Route 53 normalizes names to lowercase without a trailing dot before
        # evaluating the condition.
        normalized = hostname.strip(".").casefold()
        multivalued_keys = {
            "route53:ChangeResourceRecordSetsNormalizedRecordNames": [normalized],
            "route53:ChangeResourceRecordSetsRecordTypes": ["A"],
            "route53:ChangeResourceRecordSetsActions": ["UPSERT"],
        }
        return {
            "Sid": "UpdateDynDNSRecord",
            "Effect": "Allow",
            "Action": "route53:ChangeResourceRecordSets",
            "Resource": f"arn:aws:route53:::hostedzone/{zone_id}",
            "Condition": {
                "ForAllValues:StringEquals": multivalued_keys,
                # ForAllValues is also satisfied when a key is missing, so require
                # each one to be present.
                "Null": {k: "false" for k in multivalued_keys},
            },
        }
