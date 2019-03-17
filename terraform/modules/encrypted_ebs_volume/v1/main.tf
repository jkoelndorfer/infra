resource "aws_ebs_volume" "ebs_volume" {
  availability_zone = "${var.availability_zone}"
  size              = "${var.size}"
  type              = "${var.type}"
  encrypted         = true
  kms_key_id        = "${var.kms_key_arn}"
  tags              = {
    "Name"           = "${var.env}-${var.name}"
    "johnk:category" = "${var.category}"
    "johnk:class"    = "${var.class}"
    "johnk:env"      = "${var.env}"
  }
}
