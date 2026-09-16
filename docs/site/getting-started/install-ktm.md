# Install KTM

KTM creates projects, resolves runtime dependencies, builds, tests, and packs deployable process artifacts.

```bash
curl -fsSL https://app.kinematictrees.com/api/v2/registry/install.sh | sh
export PATH="$HOME/.ktrees/bin:$PATH"
ktm --version
```

## Log in without device enrollment

Run `ktm login`, answer **No** when asked to enroll the current device, and open the short-lived authorization link. This authenticates package operations without registering the machine as a managed device.

Never paste bootstrap tokens or saved credentials into project files.

Next: [install the runtime and Python SDK](install-runtime-sdk.md).
