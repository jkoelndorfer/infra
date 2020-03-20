data "terraform_remote_state" "core" {
  backend   = "s3"
  workspace = terraform.workspace
  config = {
    bucket               = "310987624463-prod-tfstate"
    key                  = "core.tfstate"
    region               = "us-east-1"
    workspace_key_prefix = "workspaces"
  }
}

module "user_data" {
  source = "../../aws-ec2-user-data/v1"

  asg_name = "${var.env}-${var.name}"
  category = var.category
  role     = var.role
  dns      = var.dns
  env      = var.env
  name     = "${var.env}-${var.name}"
}

resource "aws_launch_template" "launch_template" {
  name          = "${var.env}-${var.name}"
  image_id      = var.image_id
  instance_type = var.instance_type
  key_name      = data.terraform_remote_state.core.outputs.ec2_default_keypair
  user_data     = base64encode(module.user_data.user_data)
  iam_instance_profile {
    name = var.iam_instance_profile == "" ? data.terraform_remote_state.core.outputs.ec2_default_instance_profile : var.iam_instance_profile
  }
  tags = {
    "Name"           = "${var.env}-${var.name}"
    "johnk:category" = "${var.category}"
    "johnk:env"      = "${var.env}"
  }
  tag_specifications {
    resource_type = "instance"
    tags = {
      "Name"           = "${var.env}-${var.name}"
      "johnk:category" = var.category
      "johnk:role"     = var.role
      "johnk:dns"      = var.dns
      "johnk:env"      = var.env
    }
  }
  tag_specifications {
    resource_type = "volume"
    tags = {
      "Name"           = "${var.env}-${var.name}"
      "johnk:category" = var.category
      "johnk:role"     = var.role
      "johnk:env"      = var.env
    }
  }
  network_interfaces {
    associate_public_ip_address = var.associate_public_ip_address
    security_groups             = concat(
        var.security_groups,
        list(data.terraform_remote_state.core.outputs.vpc_default_sg)
    )
    delete_on_termination       = true
  }
}

resource "aws_autoscaling_group" "autoscaling_group" {
  name = "${var.env}-${var.name}"
  launch_template {
    id      = aws_launch_template.launch_template.id
    version = "$Latest"
  }
  min_size         = var.min_size
  desired_capacity = var.desired_capacity
  max_size         = var.max_size
  tags = [
    {
      key = "johnk:category"
      value = var.category
      propagate_at_launch = false
    },
    {
      key = "johnk:role"
      value = var.role
      propagate_at_launch = false
    },
    {
      key = "johnk:dns"
      value = var.dns
      propagate_at_launch = false
    },
    {
      key = "johnk:env"
      value = var.env
      propagate_at_launch = false
    }
  ]
  vpc_zone_identifier = var.subnet_ids

  lifecycle {
    ignore_changes = [desired_capacity]
  }
}
