# OpenClaw on OCI via Resource Manager

## Purpose

This Resource Manager stack launches an OCI compute instance for OpenClaw, discovers which OCI Generative AI models are actually usable for the supplied API key, and automatically configures OpenClaw to use those discovered models.

## Required OCI IAM Policy for the Generative AI API Key

Before deploying this stack:

1. Create an OCI Generative AI API key.
2. Copy the API key OCID.
3. Create an IAM policy that allows that API key to use OCI Generative AI.
4. Use the API key value in the `oci_genai_api_key` stack variable when launching this stack.

Example IAM policy:

```text
allow any-user to use generative-ai-family in tenancy where ALL {request.principal.type='generativeaiapikey', request.principal.id='<your-generative-ai-api-key-ocid>'}
```

## Quick Deploy to OCI

Launch this stack directly in OCI Resource Manager.

<p align="center">
  <a href="https://cloud.oracle.com/resourcemanager/stacks/create?zipUrl=https%3A%2F%2Fgithub.com%2FPhirlly%2FOCIOraClaw%2Farchive%2Frefs%2Fheads%2Fmain.zip">
    <img src="https://docs.oracle.com/en-us/iaas/Content/Resources/Images/deploy-to-oracle-cloud.svg" alt="Deploy to Oracle Cloud" />
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

## Current limitations / next hardening steps

The stack is now functionally working end-to-end, but later improvements may still include:

- stronger secret handling beyond direct API-key rendering into cloud-init and `~/.openclaw/.env`
- optional further refinement of model discovery heuristics and exclusions
- optional exposure improvements (for example Tailscale or reverse proxy / LB patterns) instead of SSH local forwarding
- optional networking/security hardening after bootstrap validation