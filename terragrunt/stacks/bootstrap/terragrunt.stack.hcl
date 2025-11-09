locals {
  unit_paths = {
    aws_infra_mgmt   = "aws_infra_mgmt"
    aws_accounts     = "aws_accounts"
    aws_bootstrap    = "aws_bootstrap"
    budget           = "budget"
    google_bootstrap = "google_bootstrap"
  }
  unit_paths_values = { for k, v in local.unit_paths: k => "../${v}" }
  bootstrap_values = {
    mock_outputs = {
      aws_bootstrap = {
        aws_infra_mgmt_account = {
          arn   = "arn:aws:organizations::000000000000:account/x-xxxxxxxxxx/000000000000"
          email = "aws.infra-mgmt@example.com"
          env   = "bootstrap"
          id    = "000000000000"

          organization_access_role = {
            arn  = "arn:aws:iam::000000000000:role/OrganizationAccountAccessRole"
            name = "OrganizationAccountAccessRole"
          }
        }
      }
      aws_infra_mgmt = {
        infrastate_bucket = {
          arn    = "arn:aws:s3:::infrastate-000000000000"
          bucket = "infrastate-000000000000"
        }
      }
      google_env_folder = {
        name         = "not a real environment folder; use only env attribute"
        display_name = "not a real environment folder; use only env attribute"
        env          = "prod"
        folder_id    = "000000000000"
      }
    }
    env = "prod"
    unit_paths = local.unit_paths_values
  }
}

unit "aws_bootstrap" {
  source = "../..//units/aws_bootstrap"
  path   = local.unit_paths.aws_bootstrap
  values = local.bootstrap_values
}

unit "google_bootstrap" {
  source = "../..//units/google_bootstrap"
  path   = local.unit_paths.google_bootstrap
  values = local.bootstrap_values
}

unit "aws_infra_mgmt" {
  source = "../..//units/aws_infra_mgmt"
  path   = local.unit_paths.aws_infra_mgmt
  values = local.bootstrap_values
}

unit "aws_accounts" {
  source = "../..//units/aws_accounts"
  path   = local.unit_paths.aws_accounts
  values = local.bootstrap_values
}

unit "budget" {
  source = "../..//units/budget"
  path   = local.unit_paths.budget
  values = local.bootstrap_values
}
