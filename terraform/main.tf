# ============================================================================
# PROJETO HANDS-ON ENGENHARIA DE DADOS - MACKENZIE
# Infraestrutura como Código (IaC) com Terraform
# Compatível com AWS Academy Learner Lab (us-east-1 e LabRole)
# ============================================================================

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "bucket_name" {
  type    = string
  default = "ecommerce-data-platform-mack-lab-paulo"
}

variable "key_name" {
  description = "Nome do Par de Chaves (.pem) criado no console AWS"
  type        = string
  default     = "vockey" # Nome padrão do AWS Academy ou crie o seu
}

# 1. Bucket S3 para o Data Lake Medallion
resource "aws_s3_bucket" "datalake" {
  bucket        = var.bucket_name
  force_destroy = true

  tags = {
    Project     = "Shopee-Cart-Abandonment"
    Environment = "AWS-Academy-Lab"
    Course      = "MBA-Engenharia-de-Dados"
  }
}

# Pastas da Arquitetura Medallion
resource "aws_s3_object" "bronze_folder" {
  bucket = aws_s3_bucket.datalake.id
  key    = "bronze/"
}

resource "aws_s3_object" "silver_folder" {
  bucket = aws_s3_bucket.datalake.id
  key    = "silver/"
}

resource "aws_s3_object" "gold_folder" {
  bucket = aws_s3_bucket.datalake.id
  key    = "gold/"
}

# 2. Security Group para a Instância EC2
resource "aws_security_group" "ec2_sg" {
  name        = "ecommerce-platform-sg"
  description = "Portas de acesso para SSH, Dashboard Web, Streamlit e pgAdmin"

  # SSH
  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Dashboard Web / Simulador
  ingress {
    description = "Web Dashboard HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Streamlit
  ingress {
    description = "Streamlit Analytics"
    from_port   = 8501
    to_port     = 8501
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # pgAdmin
  ingress {
    description = "pgAdmin Web"
    from_port   = 5050
    to_port     = 5050
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Spark Web UI
  ingress {
    description = "Spark Master UI"
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Saída liberada
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# 3. Instância Virtual EC2 (Ubuntu 22.04 LTS)
data "aws_ami" "ubuntu" {
  most_recent = true
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
  owners = ["099720109477"] # Canonical
}

resource "aws_instance" "data_platform" {
  ami                  = data.aws_ami.ubuntu.id
  instance_type        = "t3.large" # 2 vCPUs, 8 GB RAM (Permitido no Learner Lab)
  key_name             = var.key_name
  iam_instance_profile = "LabInstanceProfile" # Role nativa do AWS Academy!
  security_groups      = [aws_security_group.ec2_sg.name]

  root_block_device {
    volume_size           = 30 # 30 GB para SO, Docker e dados
    volume_type           = "gp3"
    delete_on_termination = true
  }

  tags = {
    Name        = "Ecommerce-Data-Platform-EC2"
    Project     = "Shopee-Cart-Abandonment"
    Environment = "AWS-Academy-Lab"
  }
}

output "s3_bucket_name" {
  value = aws_s3_bucket.datalake.id
}

output "ec2_public_ip" {
  value = aws_instance.data_platform.public_ip
}

output "ec2_public_dns" {
  value = aws_instance.data_platform.public_dns
}
