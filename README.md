# OpenClaw on OCI via Resource Manager

## Purpose

This Resource Manager stack launches an OCI compute instance for OpenClaw and bootstraps OCI Generative AI chat-model discovery at instance startup.

The stack uses an OCI Generative AI API key to:
- detect the key's usable OCI region
- validate which chat-completions models actually work for that key
- generate a runtime model catalog on the VM for OpenClaw to consume

## What this stack deploys

- One OCI compute instance
- Cloud-init bootstrap for discovery/runtime setup
- A systemd oneshot discovery service
- Runtime-generated chat model catalog written to:
  - `/opt/openclaw/runtime/03-oci-genai-chat-models.json`

## Discovery flow

At startup, the instance runs the discovery script:

1. Read candidate catalog from:
   - `/opt/openclaw/discovery/01-oci-genai-chat-candidates.json`
2. Read API key from:
   - `/etc/openclaw/oci-genai.env`
3. Probe supported OCI Generative AI API-key regions
4. Validate working chat-completions models
5. Write generated result to:
   - `/opt/openclaw/runtime/03-oci-genai-chat-models.json`

## Stack inputs

This stack expects the following inputs through Resource Manager:

- `compartment_ocid`
- `subnet_ocid`
- `availability_domain`
- `image_ocid`
- `ssh_public_key`
- `oci_genai_api_key`

Optional / defaulted:

- `instance_display_name` (default: `openclaw`)
- `instance_shape` (default: `VM.Standard.A1.Flex`)
- `instance_ocpus` (default: `2`)
- `instance_memory_gbs` (default: `12`)

## Outputs

This stack exports:

- `instance_id`
- `instance_display_name`
- `instance_public_ip`
- `instance_private_ip`
- `openclaw_discovery_output_path`

## Public IP behavior

This stack is currently configured to assign a public IP to the instance primary VNIC.

Terraform implementation:

hcl
create_vnic_details {
  subnet_id        = var.subnet_ocid
  assign_public_ip = true
}

## Current implementation status

This stack currently includes:

- canonical discovery assets under `stack/discovery/`
- systemd service under `stack/systemd/`
- Terraform-rendered cloud-init under `stack/cloud-init/cloud-init.userdata.tftpl`
- OCI compute launch using verified `oci_core_instance` provider guidance

## Current limitations / next hardening steps

This is the first working Resource Manager-oriented version.

Still to improve in later iterations:

- secure secret handling beyond direct API-key rendering into cloud-init
- OpenClaw service bootstrap ordering and integration
- removal of non-canonical prototype files from the stack package
- optional networking/security hardening beyond public-IP bootstrap mode

## Canonical files

Primary stack files:

- `provider.tf`
- `variables.tf`
- `main.tf`
- `compute.tf`
- `outputs.tf`
- `schema.yaml`
- `README.md`

Canonical discovery/runtime source files:

- `discovery/01-oci-genai-chat-candidates.json`
- `discovery/02-discover-oci-genai-chat-models.py`
- `systemd/openclaw-model-discovery.service`
- `cloud-init/cloud-init.userdata.tftpl`

## Non-canonical / reference-only files

These are not part of the preferred final RM deployment path:

- `cloud-init/cloud-init-minimal.yaml` (reference only, if retained)

## Notes

- The generated discovery output is runtime data and is not intended to be committed back into the stack.
- The candidate catalog is a bundled snapshot and does not depend on live documentation at runtime.
- The current stack is suitable for first-pass Resource Manager deployment validation.
