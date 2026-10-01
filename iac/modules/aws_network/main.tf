data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  azs = slice(data.aws_availability_zones.available.names, 0, 2)

  subnets = {
    public_a = { cidr = "10.10.0.0/24", az = local.azs[0], tier = "public" }
    public_b = { cidr = "10.10.1.0/24", az = local.azs[1], tier = "public" }
    app_a    = { cidr = "10.10.10.0/24", az = local.azs[0], tier = "app" }
    app_b    = { cidr = "10.10.11.0/24", az = local.azs[1], tier = "app" }
    db_a     = { cidr = "10.10.20.0/24", az = local.azs[0], tier = "db" }
    db_b     = { cidr = "10.10.21.0/24", az = local.azs[1], tier = "db" }
  }
}

resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-vpc"
  })
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-igw"
  })
}

resource "aws_subnet" "this" {
  for_each = local.subnets

  vpc_id                  = aws_vpc.this.id
  cidr_block              = each.value.cidr
  availability_zone       = each.value.az
  map_public_ip_on_launch = each.value.tier == "public"

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-${replace(each.key, "_", "-")}"
    Tier = each.value.tier
  })
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this.id
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-rt-public"
  })
}

resource "aws_route_table" "app" {
  vpc_id = aws_vpc.this.id

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-rt-app"
  })
}

resource "aws_route_table" "db" {
  vpc_id = aws_vpc.this.id

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-rt-db"
  })
}

resource "aws_route_table_association" "public" {
  for_each = toset(["public_a", "public_b"])

  subnet_id      = aws_subnet.this[each.value].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "app" {
  for_each = toset(["app_a", "app_b"])

  subnet_id      = aws_subnet.this[each.value].id
  route_table_id = aws_route_table.app.id
}

resource "aws_route_table_association" "db" {
  for_each = toset(["db_a", "db_b"])

  subnet_id      = aws_subnet.this[each.value].id
  route_table_id = aws_route_table.db.id
}

