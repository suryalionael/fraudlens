terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Remote state — uncomment after first apply creates the S3 bucket
  # backend "s3" {
  #   bucket         = "fraudlens-terraform-state"
  #   key            = "terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "fraudlens-terraform-locks"
  #   encrypt        = true
  # }
}
