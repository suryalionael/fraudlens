# ── CloudWatch Log Groups ──

resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/${local.name_prefix}-api"
  retention_in_days = var.log_retention_days
  tags              = { Name = "${local.name_prefix}-api-logs" }
}

resource "aws_cloudwatch_log_group" "dashboard" {
  name              = "/ecs/${local.name_prefix}-dashboard"
  retention_in_days = var.log_retention_days
  tags              = { Name = "${local.name_prefix}-dashboard-logs" }
}
