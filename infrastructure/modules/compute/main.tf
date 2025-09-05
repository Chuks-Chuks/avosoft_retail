# infrastructure/modules/compute/main.tf

# Get Ubuntu 22.04 image
data "oci_core_images" "ubuntu_images" {
  compartment_id           = var.compartment_id
  operating_system         = "Canonical Ubuntu"
  operating_system_version = "22.04"
  shape                    = "VM.Standard.E2.1.Micro"
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

# Create compute instance
resource "oci_core_instance" "avosoft_app_server" {
  compartment_id      = var.compartment_id
  availability_domain = var.availability_domain
  shape               = "VM.Standard.E2.1.Micro"
  display_name        = "avosoft-app-server"

  source_details {
    source_type = "image"
    source_id   = data.oci_core_images.ubuntu_images.images[0].id
  }

  create_vnic_details {
    subnet_id        = var.subnet_id
    assign_public_ip = true
    hostname_label   = "avosoftapp"
  }

  metadata = {
    ssh_authorized_keys = file("C:/Users/phili/.ssh/id_rsa.pub") 
    user_data = base64encode(templatefile("${path.module}/user-data.sh", {
      db_host     = var.aws_db_host
      db_name     = var.aws_db_name
      db_user     = var.aws_db_user
      db_password = var.aws_db_password
    }))
  }

  shape_config {
    memory_in_gbs = 1
    ocpus         = 1
  }
}

# Output the public IP
output "instance_public_ip" {
  value = oci_core_instance.avosoft_app_server.public_ip
}