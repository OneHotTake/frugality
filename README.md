# Frugality

Frugality is a cost-effective solution for AI-assisted development. It orchestrates free-tier AI models for Claude Code, allowing developers to focus on high-level decisions while delegating boilerplate code, tests, and documentation to AI models.

## Getting Started

To get started with Frugality, follow these steps:

1. Install the required dependencies: free-coding-models, ccr, claudish, jq, and curl.
2. Run `frug init` to initialize the Frugality system.
3. Run `frug start` to start the Frugality system.
4. Use `ccr code` to start coding with Frugality.

## Commands

Frugality provides several commands to manage the system:

* `frug start`: Start the Frugality system.
* `frug stop`: Stop the Frugality system.
* `frug status`: Show the current status of the Frugality system.
* `frug update`: Update the Frugality system to the latest version.
* `frug doctor`: Run the doctor command to diagnose and fix issues.

## Presets

Frugality provides several presets to configure the system:

* `free-tier-max`: Best free models across all providers.
* `nvidia-focus`: NVIDIA NIM only.
* `openrouter-only`: OpenRouter via claudish.
* `local-first`: Ollama for background/default, CCR for think/longContext.

## Contributing

To contribute to Frugality, follow these steps:

1. Fork the Frugality repository.
2. Make your changes and commit them.
3. Open a pull request to merge your changes into the main repository.

## License

Frugality is licensed under the MIT License.