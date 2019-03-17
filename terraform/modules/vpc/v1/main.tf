resource "aws_vpc" "vpc" {
  cidr_block = "${var.cidr_block}"
  tags {
    "Name"           = "${var.env}-${var.name}"
    "johnk:env"      = "${var.env}"
    "johnk:category" = "${var.category}"
  }
}

resource "aws_internet_gateway" "default_gateway" {
  vpc_id = "${aws_vpc.vpc.id}"
  tags = {
    "Name"           = "${var.env}-${var.name}-default-gateway"
    "johnk:env"      = "${var.env}"
    "johnk:category" = "${var.category}"
  }
}

resource "aws_route" "default_route" {
  route_table_id         = "${aws_vpc.vpc.main_route_table_id}"
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = "${aws_internet_gateway.default_gateway.id}"
}

resource "aws_security_group" "default_sg" {
  name        = "${var.env}-${var.name}-default-sg"
  description = "Provides default traffic rules, including egress traffic and management via ssh"
  vpc_id      = "${aws_vpc.vpc.id}"

  ingress {
    cidr_blocks = ["0.0.0.0/0"]
    from_port   = "${var.ssh_port}"
    to_port     = "${var.ssh_port}"
    protocol    = "tcp"
  }

  egress {
    cidr_blocks = ["0.0.0.0/0"]
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
  }

  tags = {
    "Name"           = "${var.env}-${var.name}-default-sg"
    "johnk:env"      = "${var.env}"
    "johnk:category" = "${var.category}"
  }
}
