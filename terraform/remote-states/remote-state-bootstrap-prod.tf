data "terraform_remote_state" "bootstrap" {
  backend = "local"
  config = {
    path = "../0100-bootstrap/terraform.tfstate.d/prod/terraform.tfstate"
  }
}
