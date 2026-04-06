# OpenClaw on OCI via Resource Manager

## Purpose

This Resource Manager stack launches an OCI compute instance for OpenClaw, discovers which OCI Generative AI models are actually usable for the supplied API key, and automatically configures OpenClaw to use those discovered models.

## Quick Deploy to OCI

Launch this stack directly in OCI Resource Manager.

<p align="center">
  <a href="https://cloud.oracle.com/resourcemanager/stacks/create?zipUrl=https%3A%2F%2Fgithub.com%2FPhirlly%2FOCIOraClaw%2Farchive%2Frefs%2Fheads%2Fmain.zip">
    <img src="https://docs.oracle.com/en-us/iaas/Content/Resources/Images/deploy-to-oracle-cloud.svg" alt="Deploy to Oracle Cloud" />
  </a>
</p>

<p align="center">
  <a href="https://cloud.oracle.com/resourcemanager/stacks/create?zipUrl=https%3A%2F%2Fgithub.com%2FPhirlly%2FOCIOraClaw%2Farchive%2Frefs%2Fheads%2Fmain.zip">
    Direct launch in OCI Resource Manager
  </a>
</p>

After the stack opens in OCI Resource Manager, provide the required deployment inputs such as compartment, availability domain, image, SSH public key, and OCI Generative AI API key.



The stack now implements an end-to-end automated flow that:
- provisions the VM and required network resources
- installs OpenClaw automatically
- discovers usable OCI models at instance startup
- binds those discovered models into OpenClaw as a custom `oci` provider
- configures OpenClaw to use the OCI OpenAI-compatible **Responses API** path
- installs and starts the OpenClaw gateway automatically

## What this stack deploys

- One OCI compute instance
- Self-contained OCI networking for the instance
- Cloud-init bootstrap for discovery and OpenClaw setup
- A systemd oneshot discovery service
- OpenClaw installation and gateway bootstrap
- Runtime-generated OCI model catalog written to:
  - `/opt/openclaw/runtime/03-oci-genai-chat-models.json`

## Runtime behavior

At first boot, the instance performs these phases:

1. Install discovery assets and systemd unit
2. Discover usable OCI models for the supplied API key
3. Install OpenClaw
4. Create the OpenClaw runtime/config home under `/home/opc/.openclaw`
5. Configure OpenClaw gateway basics:
   - `gateway.mode = local`
   - `gateway.bind = loopback`
   - `gateway.auth.mode = token`
6. Create a custom OpenClaw provider named `oci`
7. Configure the discovered OCI models into OpenClaw
8. Set the default OpenClaw model to the first discovered usable OCI model
9. Install and start the OpenClaw gateway service

## Discovery flow

At startup, the instance runs the discovery script sequence:

1. Read candidate catalog from:
   - `/opt/openclaw/discovery/01-oci-genai-chat-candidates.json`
2. Read API key from:
   - `/etc/openclaw/oci-genai.env`
3. Probe supported OCI Generative AI API-key regions
4. Validate usable models through the OCI OpenAI-compatible **Responses API**
5. Write the generated result to:
   - `/opt/openclaw/runtime/03-oci-genai-chat-models.json`
6. Apply the discovered provider/model configuration into:
   - `/home/opc/.openclaw/openclaw.json`

## OpenClaw integration model

The generated OpenClaw config uses:
- a custom provider named `oci`
- the discovered region `baseUrl`
- `api = "openai-responses"`
- API key auth sourced from:
  - `~/.openclaw/.env`

Discovered models are registered as provider-scoped refs such as:

- `oci/xai.grok-code-fast-1`
- `oci/xai.grok-4`
- `oci/xai.grok-3`
- `oci/xai.grok-3-mini`
- `oci/xai.grok-3-fast`
- `oci/xai.grok-3-mini-fast`

## Stack inputs

This stack expects the following inputs through Resource Manager:

- `compartment_ocid`
- `availability_domain`
- `image_id`
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

```hcl
create_vnic_details {
  subnet_id        = oci_core_subnet.openclaw_public.id
  assign_public_ip = true
}
```

## Accessing the OpenClaw UI

The OpenClaw gateway is intentionally configured as loopback-only:

- bind: `127.0.0.1`
- port: `18789`

That means the Control UI is not directly exposed on the VM public IP.

Use an SSH local port forward from your local machine:

```bash
ssh -i /ABSOLUTE/PATH/TO/YOUR/PRIVATE_KEY -L 18789:127.0.0.1:18789 opc@<INSTANCE_PUBLIC_IP>
```

Then open locally in your browser:

```text
http://127.0.0.1:18789/
```

## Post-deploy verification

On the VM, validate the deployment with:

```bash
sudo cloud-init status --long
sudo systemctl status openclaw-model-discovery.service --no-pager
sudo cat /opt/openclaw/runtime/03-oci-genai-chat-models.json
sudo -u opc bash -lc 'cat /home/opc/.openclaw/openclaw.json'
sudo -u opc bash -lc 'export PATH="/home/opc/.npm-global/bin:$PATH"; export XDG_RUNTIME_DIR="/run/user/$(id -u)"; openclaw gateway status'
sudo -u opc bash -lc 'export PATH="/home/opc/.npm-global/bin:$PATH"; export XDG_RUNTIME_DIR="/run/user/$(id -u)"; openclaw health --verbose'
```

Expected outcomes:
- cloud-init completes successfully
- discovery service succeeds
- discovery output contains usable OCI models
- `openclaw.json` contains the `oci` provider binding and discovered models
- OpenClaw gateway is installed, running, and healthy

## Current implementation status

This stack now includes:

- canonical discovery assets under `stack/discovery/`
- dynamic OpenClaw provider/model application from discovery output
- systemd discovery service under `stack/systemd/`
- Terraform-rendered cloud-init bootstrap under `stack/cloud-init/cloud-init.userdata.tftpl`
- OCI compute launch and self-contained network provisioning

## Current limitations / next hardening steps

The stack is now functionally working end-to-end, but later improvements may still include:

- stronger secret handling beyond direct API-key rendering into cloud-init and `~/.openclaw/.env`
- optional further refinement of model discovery heuristics and exclusions
- optional exposure improvements (for example Tailscale or reverse proxy / LB patterns) instead of SSH local forwarding
- optional networking/security hardening after bootstrap validation

## Canonical files

Primary stack files:

- `provider.tf`
- `variables.tf`
- `main.tf`
- `compute.tf`
- `network.tf`
- `shapes.tf`
- `outputs.tf`
- `schema.yaml`
- `README.md`

Canonical discovery/runtime source files:

- `discovery/01-oci-genai-chat-candidates.json`
- `discovery/02-discover-oci-genai-chat-models.py`
- `discovery/03-apply-openclaw-models.py`
- `systemd/openclaw-model-discovery.service`
- `cloud-init/cloud-init.userdata.tftpl`

## Notes

- The generated discovery output is runtime data and is not intended to be committed back into the stack.
- The candidate catalog is a bundled snapshot and does not depend on live documentation at runtime.
- Manual operator checks on a headless VM should set:

```bash
export PATH="/home/opc/.npm-global/bin:$PATH"
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
```

before running interactive `openclaw gateway ...` status/health commands.