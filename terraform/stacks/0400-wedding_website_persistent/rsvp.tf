# See https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.NamingRulesDataTypes.html#HowItWorks.DataTypeDescriptors
# for information about DynamoDB attribute types.
resource "aws_dynamodb_table" "wedding_invite" {
  billing_mode = "PAY_PER_REQUEST"
  name         = "WeddingInvite-${local.env.name}"
  hash_key     = "InviteId"

  attribute {
    name = "InviteId"
    type = "S"  # string
  }
}
