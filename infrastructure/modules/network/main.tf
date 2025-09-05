# infrastructure/modules/network/main.tf

# Create Virtual Cloud Network (VCN)
resource "oci_core_vcn" "avosoft_vcn" {
  compartment_id = var.compartment_id
  cidr_block     = var.vcn_cidr_block
  display_name   = "avosoft-retail-vcn"
  dns_label      = "avosoft"
}

# Create Internet Gateway
resource "oci_core_internet_gateway" "internet_gateway" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.avosoft_vcn.id
  display_name   = "avosoft-internet-gateway"
}

# Create Public Subnet
resource "oci_core_subnet" "public_subnet" {
  compartment_id    = var.compartment_id
  vcn_id            = oci_core_vcn.avosoft_vcn.id
  cidr_block        = var.public_subnet_cidr
  display_name      = "avosoft-public-subnet"
  dns_label         = "public"
  route_table_id    = oci_core_route_table.public_route_table.id
  security_list_ids = [oci_core_security_list.public_security_list.id]
  prohibit_public_ip_on_vnic = false
}

# Create Route Table for Public Subnet
resource "oci_core_route_table" "public_route_table" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.avosoft_vcn.id
  display_name   = "public-route-table"

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.internet_gateway.id
  }
}

# Security List for Public Subnet (Web Access)
resource "oci_core_security_list" "public_security_list" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.avosoft_vcn.id
  display_name   = "public-security-list"

  # Allow SSH access
  ingress_security_rules {
    protocol  = "6" # TCP
    source    = "0.0.0.0/0"
    stateless = false

    tcp_options {
      min = 22
      max = 22
    }
  }

  # Allow HTTP access
  ingress_security_rules {
    protocol  = "6" # TCP
    source    = "0.0.0.0/0"
    stateless = false

    tcp_options {
      min = 80
      max = 80
    }
  }

  # Allow HTTPS access
  ingress_security_rules {
    protocol  = "6" # TCP
    source    = "0.0.0.0/0"
    stateless = false

    tcp_options {
      min = 443
      max = 443
    }
  }

  # Allow FastAPI access (port 8000)
  ingress_security_rules {
    protocol  = "6" # TCP
    source    = "0.0.0.0/0"
    stateless = false

    tcp_options {
      min = 8000
      max = 8000
    }
  }

  # Allow Streamlit access (port 8501)
  ingress_security_rules {
    protocol  = "6" # TCP
    source    = "0.0.0.0/0"
    stateless = false

    tcp_options {
      min = 8501
      max = 8501
    }
  }

  # Allow all outbound traffic
  egress_security_rules {
    protocol    = "all"
    destination = "0.0.0.0/0"
    stateless   = false
  }
}