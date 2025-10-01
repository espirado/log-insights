terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

resource "aws_cloudwatch_log_group" "bench" {
  name              = var.log_group_name
  retention_in_days = 7
}

data "aws_iam_policy_document" "ec2_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ec2_role" {
  name               = "log-insights-ec2-role"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume.json
}

data "aws_iam_policy_document" "logs_access" {
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "logs:DescribeLogStreams",
      "logs:DescribeLogGroups"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "logs_policy" {
  name   = "log-insights-logs-policy"
  policy = data.aws_iam_policy_document.logs_access.json
}

resource "aws_iam_role_policy_attachment" "attach_logs" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = aws_iam_policy.logs_policy.arn
}

resource "aws_iam_instance_profile" "ec2_profile" {
  name = "log-insights-ec2-instance-profile"
  role = aws_iam_role.ec2_role.name
}

resource "aws_security_group" "bench_sg" {
  name        = "log-insights-bench-sg"
  description = "Allow SSH and app ports"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["137112412989"] # Amazon
  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }
}

data "aws_vpc" "default" {
  default = true
}

resource "aws_instance" "bench" {
  ami                    = data.aws_ami.al2023.id
  instance_type          = var.instance_type
  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name
  key_name               = var.key_name
  vpc_security_group_ids = [aws_security_group.bench_sg.id]

  user_data = templatefile("${path.module}/user_data.sh", {
    log_group = aws_cloudwatch_log_group.bench.name
    region    = var.region
  })

  tags = {
    Name = "log-insights-bench"
  }
}

output "public_ip" {
  value = aws_instance.bench.public_ip
}

output "log_group_name" {
  value = aws_cloudwatch_log_group.bench.name
}







