# Contributing to Frugality

We welcome contributions! The highest-value contributions are presets.

## Submitting a Preset

Presets are the easiest way to contribute. A preset adds support for a new provider.

### Format

Create a directory in `presets/<preset-name>/` with a `manifest.json`:

```json
{
  "version": "1.0.0",
  "name": "my-preset",
  "description": "Brief description",
  "Router": {
    "default": "model-id",
    "background": "model-id",
    "think": "model-id",
    "longContext": "model-id"
  },
  "Providers": [
    {
      "id": "provider-id",
      "name": "Provider Name",
      "base_url": "https://api.example.com",
      "auth": { "api_key": "${API_KEY_VAR}" }
    }
  ]
}
```

### Requirements

- Provider must be free-tier or have a generous free tier
- Model IDs must match free-coding-models output
- Include link to API key acquisition
- Test before submitting

## Code Contributions

Follow these rules:

- Zero runtime npm dependencies
- CommonJS (require/module.exports)
- Atomic file writes (temp + rename)
- Error handling for all external calls
- Idempotent operations

## Testing

```bash
npm test           # Unit tests
npm run stress-test # Integration tests
npm run doctor     # Diagnostics
```

All tests must pass before a PR is merged.

## License

All contributions are MIT licensed.
