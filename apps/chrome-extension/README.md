# JobReach Referral Assistant

Chrome extension used by the Dev2 referral flow.

## Local Package

```bash
PUBLIC_WEB_ORIGIN=http://localhost:3000 \
NEXT_PUBLIC_REFERRAL_API_URL=http://localhost:8001 \
node apps/chrome-extension/scripts/package-extension.mjs
```

Load `dist/chrome-extension` from `chrome://extensions` with Developer Mode enabled.
