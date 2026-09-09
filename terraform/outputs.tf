output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "alb_dns_name" {
  description = "ALB DNS name"
  value       = aws_alb.main.dns_name
}

output "api_url" {
  description = "API URL"
  value       = "http://${aws_alb.main.dns_name}/api"
}

output "dashboard_url" {
  description = "Dashboard URL"
  value       = "http://${aws_alb.main.dns_name}/dashboard"
}

output "rds_endpoint" {
  description = "RDS endpoint"
  value       = aws_db_instance.postgres.endpoint
  sensitive   = true
}

output "ecr_api_repository_url" {
  description = "ECR API repository URL"
  value       = aws_ecr_repository.api.repository_url
}

output "ecr_dashboard_repository_url" {
  description = "ECR Dashboard repository URL"
  value       = aws_ecr_repository.dashboard.repository_url
}

output "s3_artifacts_bucket" {
  description = "S3 bucket for model artifacts"
  value       = aws_s3_bucket.artifacts.id
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.main.name
}

output "ecs_service_api" {
  description = "ECS API service name"
  value       = aws_ecs_service.api.name
}

output "ecs_service_dashboard" {
  description = "ECS Dashboard service name"
  value       = aws_ecs_service.dashboard.name
}
