# OpenClaw on OCI via Resource Manager

## Purpose

This Resource Manager stack launches an OCI compute instance for OpenClaw, discovers which OCI Generative AI models are actually usable for the supplied API key, and automatically configures OpenClaw to use those discovered models.

## Required OCI IAM Policy for the Generative AI API Key

Before deploying this stack:

1. Create an OCI Generative AI API key.
2. Copy the API key **value**.
3. Copy the API key **OCID**.
4. Create an IAM policy that allows that API key to use OCI Generative AI.
5. Use the API key **value** in the `oci_genai_api_key` stack variable when launching this stack.

Example IAM policy:

```text
allow any-user to use generative-ai-family in tenancy where ALL {request.principal.type='generativeaiapikey', request.principal.id='<your-generative-ai-api-key-ocid>'}
```

Notes:
- The **API key value** is what you paste into the Resource Manager stack variable.
- The **API key OCID** is what you use in the IAM policy condition.

## Quick Deploy to OCI

Launch this stack directly in OCI Resource Manager.

<p align="center">
  <a href="https://cloud.oracle.com/resourcemanager/stacks/create?zipUrl=https%3A%2F%2Fgithub.com%2FPhirlly%2FOCIOraClaw%2Farchive%2Frefs%2Fheads%2Fmain.zip">
    <img src="https://docs.oracle.com/en-us/iaas/Content/Resources/Images/deploy-to-oracle-cloud.svg" alt="Deploy to Oracle Cloud" />
  </a>
</p>

After the stack opens in OCI Resource Manager, provide the required deployment inputs such as compartment, availability domain, image, SSH public key, and OCI Generative AI API key.

The stack implements an end-to-end automated flow that:
- provisions the VM and required network resources
- installs OpenClaw automatically
- discovers usable OCI models at instance startup
- binds those discovered models into OpenClaw as a custom `oci` provider
- configures OpenClaw to use the OCI OpenAI-compatible **Responses API** path
- installs and starts the OpenClaw gateway automatically

## Runtime behavior

At first boot, the instance performs these phases:

1. Install discovery assets and systemd unit.
2. Create the OpenClaw runtime/config home under `/home/opc/.openclaw`.
3. Wait for DNS resolution and outbound HTTPS readiness before network-dependent bootstrap steps begin.
4. Refresh package metadata and install bootstrap dependencies with bounded retries.
5. Download and run the OpenClaw installer only after the installer endpoint is reachable.
6. Verify that the OpenClaw binary exists before running configuration commands.
7. Configure OpenClaw gateway basics:
   - `gateway.mode = local`
   - `gateway.bind = loopback`
   - `gateway.auth.mode = token`
8. Start the OCI model discovery systemd unit.
9. Wait for discovery output to exist.
10. Create a custom OpenClaw provider named `oci`.
11. Configure the discovered OCI models into OpenClaw.
12. Set the default OpenClaw model to the first discovered usable OCI model.
13. Install and start the OpenClaw gateway service.

## Important: wait for cloud-init to finish before running OpenClaw commands

Do not run `openclaw` commands immediately after the VM becomes reachable.
Wait until first-boot bootstrap has fully completed.

Run this command on the VM:

```bash
sudo cloud-init status --long || true
```

### What users see while bootstrap is still running

Example output while the instance is still provisioning OpenClaw and discovery assets:

```text
[opc@openclaw ~]$ sudo cloud-init status --long || true
status: running
extended_status: running
boot_status_code: enabled-by-generator
last_update: Thu, 01 Jan 1970 00:00:31 +0000
detail: DataSourceOracle
errors: []
recoverable_errors: {}
```

If the output shows `status: running`, wait and run the command again in a minute.

### What users see when bootstrap is complete

Example output after bootstrap has finished successfully:

```text
[opc@openclaw ~]$ sudo cloud-init status --long || true
status: done
extended_status: done
boot_status_code: enabled-by-generator
last_update: Thu, 01 Jan 1970 00:06:45 +0000
detail: DataSourceOracle
errors: []
recoverable_errors: {}
[opc@openclaw ~]$
```

Only after the output shows `status: done` should users proceed with `openclaw` commands.

## Get the current gateway token in the terminal

After `cloud-init` is complete, print the current OpenClaw gateway token with:

```bash
sudo -u opc bash -lc 'python3 -c "import json; print(json.load(open(\"/home/opc/.openclaw/openclaw.json\"))[\"gateway\"][\"auth\"][\"token\"])"'
```

This prints the token currently configured in `/home/opc/.openclaw/openclaw.json`.

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

When prompted, paste the token printed from the terminal.

Because the gateway is configured with:
- `bind = loopback`
- `auth.mode = token`

you must both:
- access it through the SSH local port forward, and
- provide the current gateway token to log in.

## Optional post-deploy verification

Use the following commands only if you want to validate the deployment in more detail or troubleshoot an issue.
These commands are not required just to sign in and use OpenClaw.

```bash
sudo cloud-init status --long || true
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
- optional networking/security hardening after bootstrap validation.