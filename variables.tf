variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "instance_type" {
  type    = string
  default = "t2.micro"
}

variable "bucket_name" {
  type    = string
  default = "cs385finalprojectbucket"
}

variable "s3_key" {
  type    = string
  default = "gns3-dr/site-latest.tar.gz"
}

variable "key_name" {
  type = string
}

variable "ssh_cidr" {
  type    = string
  default = "0.0.0.0/0"
}
