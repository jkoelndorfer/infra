# This provides access for local infrastructure to perform
# validation for Let's Encrypt (or similar) using the DNS-01
# challenge type [1].
#
# [1]: https://letsencrypt.org/docs/challenge-types/#dns-01-challenge

data "aws_iam_policy_document" "miniserv_dns_01" {
  statement {
    sid = "AllowListHostedZones"

    actions = [
      "route53:ListHostedZones",
    ]

    resources = ["*"]
  }

  statement {
    sid = "AllowGetChange"

    actions = [
      "route53:GetChange",
    ]

    # TODO: Is it possible to limit this access to particular resources?
    # IAM supports limiting to change resources [1] but it's unclear if
    # we can make this work with SWAG's route53 DNS plugin.
    #
    # [1]: https://docs.aws.amazon.com/service-authorization/latest/reference/list_amazonroute53.html#amazonroute53-change
    resources = ["*"]
  }

  statement {
    sid = "AllowDNS01ZoneUpdate"

    actions = [
      "route53:ChangeResourceRecordSets",
    ]

    resources = [
      data.aws_route53_zone.zone.arn,
    ]

    condition {
      test     = "StringEquals"
      variable = "route53:ChangeResourceRecordSetsNormalizedRecordNames"
      values = [
        for d in local.env.miniserv_private_records :
        lower("_acme-challenge.${d}.${local.env.dns_zone}")
      ]
    }

    condition {
      test     = "StringEquals"
      variable = "route53:ChangeResourceRecordSetsRecordTypes"
      values   = ["TXT"]
    }
  }
}

resource "aws_iam_policy" "miniserv_dns_01" {
  name        = "miniserv-dns-01"
  description = "Policy permitting updates to DNS zone to satisfy the DNS-01 challenge type."
  policy      = data.aws_iam_policy_document.miniserv_dns_01.json
}

resource "aws_iam_user" "miniserv_dns_01" {
  name = "miniserv-dns-01"
}

resource "aws_iam_user_policy_attachment" "miniserv_dns_01" {
  user       = aws_iam_user.miniserv_dns_01.name
  policy_arn = aws_iam_policy.miniserv_dns_01.arn
}

resource "aws_iam_access_key" "miniserv_dns_01" {
  user = aws_iam_user.miniserv_dns_01.name
}

resource "aws_ssm_parameter" "miniserv_dns_01_access_key_id" {
  name        = "/${local.env.name}/local_ssl/aws_iam_access_key_id"
  type        = "String"
  description = "Access key ID used by local infrastructure to pass DNS-01 challenges."
  value       = aws_iam_access_key.miniserv_dns_01.id
}

resource "aws_ssm_parameter" "miniserv_dns_01_secret_access_key" {
  name        = "/${local.env.name}/local_ssl/aws_iam_secret_access_key"
  type        = "SecureString"
  description = "Secret access key used by local infrastructure to pass DNS-01 challenges."
  value       = aws_iam_access_key.miniserv_dns_01.secret
}
