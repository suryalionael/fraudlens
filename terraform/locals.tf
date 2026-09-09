locals {
  name_prefix = "${var.project}-${var.environment}"
  account_id  = data.aws_caller_identity.current.account_id
  region      = data.aws_region.current.name

  # Container ports
  api_port        = 8000
  dashboard_port  = 8501
  db_port         = 5432

  # Common tags
  common_tags = {
    Project     = var.project
    Environment = var.environment
  }
}
