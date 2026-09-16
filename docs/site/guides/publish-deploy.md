# Publish and deploy

Publishing changes external registry state. Inspect the archive and validate in a clean environment before running `ktm publish`.

```bash
ktm pack --mode compiled
ktm pack --dry-run --list
ktm pack --explain path/to/file
```

Deployment requires:

- the process package;
- a compatible `kinematic-trees/kt-node` runtime artifact;
- runtime JSON for the target transport and platform;
- model or schema artifacts named by the package contract.

Normal packages must not contain credentials, `.env` files, private keys, external symlinks, or paths into a developer's KTM store.

The detached `summer` deployment is delivered by the next plan goal; it is not claimed complete in this documentation version.
