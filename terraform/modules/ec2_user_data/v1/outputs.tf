output "user_data" {
  value = <<EOF
#!/bin/bash
cat <<EOM > /etc/metadata
INSTANCE_ASG_NAME='${var.asg_name}'
INSTANCE_CATEGORY='${var.category}'
INSTANCE_CLASS='${var.class}'
INSTANCE_DNS='${var.dns}'
INSTANCE_ENV='${var.env}'
INSTANCE_NAME='${var.name}'
EOM
/opt/cloud-tools/aws/provision
EOF
}
