locals {
  discovery_candidates_json = file("${path.module}/discovery/01-oci-genai-chat-candidates.json")
  discovery_script_py       = file("${path.module}/discovery/02-discover-oci-genai-chat-models.py")
  discovery_service_unit    = file("${path.module}/systemd/openclaw-model-discovery.service")

  openclaw_cloud_init_user_data = templatefile("${path.module}/cloud-init/cloud-init.userdata.tftpl", {
    discovery_candidates_json = local.discovery_candidates_json
    discovery_script_py       = local.discovery_script_py
    discovery_service_unit    = local.discovery_service_unit
    oci_genai_api_key         = var.oci_genai_api_key
  })
}
