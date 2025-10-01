variable "region" {
  type        = string
  description = "AWS region"
  default     = "us-east-1"
}

variable "instance_type" {
  type        = string
  description = "EC2 instance type"
  default     = "t3.small"
}

variable "key_name" {
  type        = string
  description = "EC2 key pair name for SSH"
}

variable "log_group_name" {
  type        = string
  description = "CloudWatch Log Group name"
  default     = "/log-insights/bench"
}







