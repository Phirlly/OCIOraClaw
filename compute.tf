data "oci_core_images" "ol9_images" {
  compartment_id           = var.compartment_ocid
  operating_system         = "Oracle Linux"
  operating_system_version = "9"
  shape                    = var.instance_shape
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

resource "oci_core_instance" "openclaw" {
  availability_domain = var.availability_domain
  compartment_id      = var.compartment_ocid
  display_name        = var.instance_display_name
  shape               = var.instance_shape

  shape_config {
    ocpus         = var.instance_ocpus
    memory_in_gbs = var.instance_memory_gbs
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.openclaw_public.id
    assign_public_ip = true
  }

  source_details {
    source_type = "image"
    source_id   = data.oci_core_images.ol9_images.images[0].id
  }

  metadata = {
    ssh_authorized_keys = var.ssh_public_key
    user_data           = base64encode(local.openclaw_cloud_init_user_data)
  }

  lifecycle {
    precondition {
      condition     = local.selected_shape_is_flexible
      error_message = "The selected shape must be a flexible shape."
    }

    precondition {
      condition = (
        local.selected_shape_ocpu_min == null ||
        local.selected_shape_ocpu_max == null ||
        (
          var.instance_ocpus >= local.selected_shape_ocpu_min &&
          var.instance_ocpus <= local.selected_shape_ocpu_max
        )
      )
      error_message = "The selected OCPU value is outside the supported range for the chosen shape."
    }

    precondition {
      condition = (
        local.selected_shape_memory_min == null ||
        local.selected_shape_memory_max == null ||
        (
          var.instance_memory_gbs >= local.selected_shape_memory_min &&
          var.instance_memory_gbs <= local.selected_shape_memory_max
        )
      )
      error_message = "The selected memory value is outside the supported range for the chosen shape."
    }
  }
}
