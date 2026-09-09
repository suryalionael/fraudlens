# ── ALB ──

resource "aws_alb" "main" {
  name               = "${local.name_prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = [aws_subnet.public_a.id, aws_subnet.public_b.id]

  tags = { Name = "${local.name_prefix}-alb" }
}

# ── Target Groups ──

resource "aws_alb_target_group" "api" {
  name        = "${local.name_prefix}-api"
  port        = local.api_port
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    path                = "/health"
    protocol            = "HTTP"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    matcher             = "200"
  }

  tags = { Name = "${local.name_prefix}-api-tg" }
}

resource "aws_alb_target_group" "dashboard" {
  name        = "${local.name_prefix}-dashboard"
  port        = local.dashboard_port
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    path                = "/"
    protocol            = "HTTP"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    matcher             = "200"
  }

  tags = { Name = "${local.name_prefix}-dashboard-tg" }
}

# ── Listener ──

resource "aws_alb_listener" "http" {
  load_balancer_arn = aws_alb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "fixed-response"

    fixed_response {
      content_type = "text/plain"
      message_body = "FraudLens — not found"
      status_code  = "404"
    }
  }
}

# ── Listener Rules ──

resource "aws_alb_listener_rule" "api" {
  listener_arn = aws_alb_listener.http.arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_alb_target_group.api.arn
  }

  condition {
    path_pattern {
      values = ["/api", "/api/*", "/health", "/ready", "/docs", "/redoc", "/openapi.json"]
    }
  }
}

resource "aws_alb_listener_rule" "dashboard" {
  listener_arn = aws_alb_listener.http.arn
  priority     = 200

  action {
    type             = "forward"
    target_group_arn = aws_alb_target_group.dashboard.arn
  }

  condition {
    path_pattern {
      values = ["/dashboard", "/dashboard/*", "/"]
    }
  }
}
