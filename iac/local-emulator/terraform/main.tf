terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.3"
    }
  }
}

provider "aws" {
  region                      = "us-east-2"
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_region_validation      = true
  skip_requesting_account_id  = true

  endpoints {
    ec2 = "http://127.0.0.1:5000"
    sts = "http://127.0.0.1:5000"
  }
}

variable "test_name" {
  type = string
}

module "aws_network" {
  source      = "../../modules/aws_network"
  name_prefix = var.test_name
  vpc_cidr    = "10.10.0.0/16"
  tags        = { EmulatorRun = var.test_name }
}
