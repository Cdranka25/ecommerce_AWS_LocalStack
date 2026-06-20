terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

provider "aws" {
  region                      = "us-east-1"
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true
  endpoints {
    sqs = "http://localhost:4566"
    s3  = "http://localhost:4566"
  }
}

resource "aws_sqs_queue" "dlq" {
  name                      = "sqs-dead-letter"
  message_retention_seconds = 86400
}

locals {
  servicos = ["pagamento", "estoque", "fiscal", "logistica", "notificacao"]
}

resource "aws_sqs_queue" "filas" {
  for_each                   = toset(local.servicos)
  name                       = "sqs-pedidos-${each.key}"
  visibility_timeout_seconds = 30
  message_retention_seconds  = 3600
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3
  })
}

