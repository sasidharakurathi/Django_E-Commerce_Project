# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please open an issue or contact the maintainers directly. Do **not** post sensitive information in public issues.

## Supported Versions
- Only the latest version is supported.

## Security Best Practices
- **Never commit secrets or API keys.**
- All sensitive data must be loaded from environment variables (see `.env.example`).
- Set `DEBUG=False` in production.
- Use strong, unique `SECRET_KEY` for each deployment.
- Restrict `ALLOWED_HOSTS` to your domain(s).
- Use HTTPS in production.
- Keep dependencies up to date.

## Disclosure Policy
We will respond to security issues as soon as possible and patch vulnerabilities promptly.
