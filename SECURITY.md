# Security Policy

## Scope

This project is a local-only Flask application for preparing documents with private PDF templates. It is designed to bind to `127.0.0.1` and to keep session data in a local SQLite database.

## Do not expose it publicly

Do not bind the application to `0.0.0.0`, put it behind an unauthenticated reverse proxy, or deploy it directly to the Internet. The application has no user authentication because the intended security boundary is the trusted local machine.

## Private data boundary

Never commit:

- Company PDF templates or generated PDFs
- `app/config/documents.json`
- `app/data/sessions.sqlite3`
- Source originals, QA files, temporary files, or duplicate archives
- Secrets, credentials, or real company data

## Reporting a vulnerability

Do not open a public issue containing private data or exploit details. Contact the repository owner privately with a description, impact, reproduction steps, and a suggested mitigation.
