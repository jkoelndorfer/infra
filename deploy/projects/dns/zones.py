"""
projects.dns.zones
==================

This module contains an InfrastructureProject that configures DNS zones.
"""

import re
from typing import Any, Self, Tuple

from pulumi import export, Output, InvokeOptions, ResourceOptions
import pulumi_aws as aws

from infralib import (
    DeploymentContext,
    DeploymentTarget,
    Environment,
    exportable_resource,
    InfrastructureProject,
    InfrastructureStack,
)
from infralib.config.domain import Domain

from ..aws.accounts import AWSAccount, AWSAccountsProject


class DNSZone:
    """
    Object representing a DNS zone created by the dns.zones project.
    """

    def __init__(
        self,
        aws_account: AWSAccount,
        arn: str,
        name: str,
        name_servers: list[str],
        primary_name_server: str,
        zone_id: str,
    ) -> None:
        self.aws_account = aws_account
        self.arn = arn
        self.name = name
        self.name_servers = name_servers
        self.primary_name_server = primary_name_server
        self.zone_id = zone_id

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Self:
        return cls(
            aws_account=AWSAccount.from_dict(d["aws_account"]),
            arn=d["arn"],
            name=d["name"],
            name_servers=d["name_servers"],
            primary_name_server=d["primary_name_server"],
            zone_id=d["zone_id"],
        )


class DNSZonesProject(InfrastructureProject):
    """
    Project that configures DNS zones.
    """

    name = "dns.zones"

    @classmethod
    def dependencies(cls, target: DeploymentTarget) -> list[InfrastructureStack]:
        deps = [AWSAccountsProject.stack(target)]

        # The prod stack will delegate "dev." zones to dev. To do this, prod
        # needs to look up the dev zones that are produced. Additionally, prod
        # is responsible for creating credentials that can access both dev and
        # prod.
        if target.environment == Environment.PROD:
            this_project_dev = cls.stack(DeploymentTarget(Environment.DEV, None))
            deps.append(this_project_dev)

        return deps

    @classmethod
    def deployment_targets(cls) -> list[DeploymentTarget]:
        return [
            DeploymentTarget(Environment.DEV, None),
            DeploymentTarget(Environment.PROD, None),
        ]

    def pulumi_program(self) -> None:
        self.dns_account = AWSAccountsProject.lookup_account(
            "dns", self.dctx.target.environment, self.dctx.outputs
        )
        self.aws_provider = self.dctx.provider_factory.aws_provider(
            "aws",
            assume_role_arn=self.dns_account.role_arn,
        )
        self.domains = self.dctx.config.domains
        self.default_iopts = InvokeOptions(provider=self.aws_provider)
        self.default_ropts = ResourceOptions(provider=self.aws_provider)
        self.domain_zones: dict[str, dict[str, Any]] = dict()
        self.zones_by_id: dict[str, dict[str, Any]] = dict()

        self._configure_zones()
        self._configure_zone_delegation()

        export("domain_zones", self.domain_zones)
        export("zones", self.zones_by_id)

    @classmethod
    def lookup_zone(
        cls, dctx: DeploymentContext, fqdn: str
    ) -> Tuple[DNSZone, aws.Provider]:
        """
        Given a deployment context and a fully-qualified domain name, returns
        the DNS zone that the domain name should be provisioned in, and an
        appropriate AWS provider to provision in that zone.

        The calling project should provide its own deployment context.
        """
        prod = DeploymentTarget(Environment.PROD, None)
        prod_outputs = dctx.outputs(cls.stack(prod))
        domain_zones = {
            k: DNSZone.from_dict(v)
            for k, v in prod_outputs["domain_zones"].value.items()
        }

        def normalized(d: str) -> str:
            """
            Normalize a domain name to remove whitespace and leading or trailing dots.
            """
            return d.strip().strip(".").casefold()

        def zone_can_manage(zone: DNSZone, fqdn: str) -> bool:
            """
            Returns True if a zone can manage records for the given
            fully-qualified domain name.
            """
            # In order for an FQDN to be "managed" by a zone, the FQDN must
            # end with the candidate zone (plus a leading dot). Otherwise,
            # the FQDN and zone name must match (this supports the apex case).
            #
            # Take "my.test.example.com". It can be managed by any of the following
            # zones:
            #
            # * my.test.example.com (zone name matches FQDN exactly)
            # * test.example.com (".test.example.com" must be in FQDN)
            # * example.com (".example.com" must be in FQDN)
            #
            # Note that a zone named "notmy.test.example.com" is not permitted. That
            # is why a simple check that the FQDN ends with the zone name is not
            # sufficient.
            regex = re.compile(r"(^|\.)" + normalized(zone.name) + r"$")
            return bool(regex.search(normalized(fqdn)))

        candidate_zones = [z for z in domain_zones.values() if zone_can_manage(z, fqdn)]
        if not candidate_zones:
            raise ValueError(f"could not find zone for {fqdn}")

        # Once we get the list of candidate zones, the correct zone to is the
        # one with the longest name. Zones with shorter names would delegate
        # to zones with longer names via NS records. Continuing from the
        # previous example:
        #
        # "example.com" delegates to "test.example.com". This means that the
        # record for "my.test.example.com" should be provisioned in the
        # "test.example.com" zone, not the "example.com" zone.
        zone = max(candidate_zones, key=lambda z: len(z.name))
        cache_key = f"dns.provider/{zone.aws_account.id}"
        provider = dctx.kv_get(cls, cache_key, None)
        if provider is None:
            provider = dctx.provider_factory.aws_provider(
                name=f"dns.{zone.aws_account.id}",
                assume_role_arn=zone.aws_account.role_arn,
            )
            dctx.kv_set(cls, cache_key, provider)

        return (zone, provider)

    def _configure_zones(self) -> None:
        """
        Configures DNS zones.
        """
        for domain_id in self._zoned_domains(self.dctx.target):
            domain_name, zone = self._zone(domain_id)
            exportable_zone = exportable_resource(
                resource=zone,
                attrs=["arn", "name", "name_servers", "primary_name_server", "zone_id"],
                addl={
                    "aws_account": self.dns_account.to_dict(),
                },
            )

            self.zones_by_id[domain_id] = exportable_zone
            self.domain_zones[domain_name] = exportable_zone

    def _configure_zone_delegation(self) -> None:
        """
        Configures delegation of zones. That is, sets an NS record for a
        subdomain so that another zone is authoritative for the subdomain.
        """
        # Only prod needs to delegate to dev zones. Dev never delegates to prod.
        if self.dctx.target.environment != Environment.PROD:
            return

        dev = DeploymentTarget(Environment.DEV, None)
        dev_outputs = self.dctx.outputs(self.stack(dev))
        dev_zones = dev_outputs["zones"].value
        for delegated_zone in self._zoned_domains(dev):
            domain_obj = self.dctx.config.domains[delegated_zone]
            dev_domain = self._domain_for(domain_obj, dev)
            self.domain_zones[dev_domain] = dev_zones[delegated_zone]
            prod_zone_id = self.zones_by_id[delegated_zone]["zone_id"]
            aws.route53.Record(
                f"{delegated_zone}.delegate.{dev.environment}",
                zone_id=prod_zone_id,
                name=dev_domain,
                records=dev_zones[delegated_zone]["name_servers"],
                ttl=1800,
                type=aws.route53.RecordType.NS,
                opts=self.default_ropts,
            )

    @classmethod
    def _domain_for(cls, domain: Domain, target: DeploymentTarget) -> str:
        """
        Given a domain and deployment target, returns the full "apex domain"
        for that target.

        If the domain name is "example.com", the returned domain is "example.com"
        for prod and "dev.example.com" for dev.
        """
        domain_name = domain.domain
        if target.environment != Environment.PROD:
            domain_name = f"{target.environment}.{domain_name}"

        if target.region is not None:
            domain_name = f"{target.region}.{domain_name}"

        return domain_name

    @classmethod
    def _zoned_domains(cls, target: DeploymentTarget) -> list[str]:
        """
        Returns a list of domain IDs that will have their own DNS zone provisioned.

        If a domain's ID does not appear in this list, it will not have a zone
        provisioned. DNS records for the domain must be provisioned into an
        already existing zone.
        """
        zones: list[str]
        match target.environment:
            case Environment.PROD:
                zones = ["primary", "anon", "homelab"]
            case Environment.DEV:
                zones = ["primary"]
            case _:
                raise ValueError(f"unsupported environment: {target.environment}")

        return zones

    def _zone(self, domain_id: str) -> Tuple[str, Output[aws.route53.GetZoneResult]]:
        """
        Provisions the DNS zone with the given ID.
        """
        domain = self.dctx.config.domains[domain_id]
        domain_name = self._domain_for(
            self.dctx.config.domains[domain_id],
            self.dctx.target,
        )
        zone = aws.route53.Zone(
            f"{domain_id}",
            name=domain_name,
            comment=f"{domain.description} ({self.dctx.target.environment}/{domain_id})",
            opts=self.default_ropts,
        )
        # We need to get the zone after creation so that the name server list for
        # the zone is not sorted. The resource sorts name_servers, while the data
        # does not. This appears to be an unfixed bug in the underlying Terraform
        # provider. See:
        #
        # * https://github.com/hashicorp/terraform-provider-aws/issues/28430
        # * https://github.com/hashicorp/terraform-provider-aws/issues/21965#issuecomment-1282636430
        zone_data = aws.route53.get_zone_output(
            zone_id=zone.zone_id,
            opts=self.default_iopts,
        )
        aws.route53.Record(
            f"{domain_id}.ns",
            zone_id=zone_data.zone_id,
            name=zone_data.name,
            records=zone_data.name_servers,
            ttl=(60 * 60 * 2),
            type=aws.route53.RecordType.NS,
            allow_overwrite=True,
            opts=self.default_ropts,
        )
        return (domain_name, zone_data)
