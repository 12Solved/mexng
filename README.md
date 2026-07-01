# Email Workflow Processor

**Version 1.0.0**

A modular email processing system with configurable workflows. Process emails from IMAP servers using customizable step-based workflows with a web-based management interface.

## Features

- **IMAP Email Processing**: Connect to any IMAP email server
- **Workflow Engine**: Build custom email processing workflows using modular steps
- **Web Interface**: React-based UI for workflow management and monitoring
- **Database Persistence**: PostgreSQL backend with migration support
- **Docker Support**: Development and production Docker configurations
- **Extensible Architecture**: Easy to add custom processing steps

## Prerequisites

- Python 3.8+
- Node.js 24.14.1+
- PostgreSQL 15
- Docker & Docker Compose (for containerized deployment)

## Configuration

### Environment Setup

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Configure required variables in `.env`:
   - **DATABASE_URL**: PostgreSQL connection string
   - **EMAIL_PROVIDER**: Set to `imap`
   - **VITE_BASE_PATH**: Frontend base path (must have leading/trailing slashes)
   - **IMAP_HOST**: Your IMAP server address (e.g., `imap.gmail.com`)
   - **IMAP_PORT**: IMAP port (typically `993` for SSL)
   - **IMAP_USERNAME**: Your email address
   - **IMAP_PASSWORD**: Your email password or app-specific password
   - **IMAP_USE_SSL**: Set to `true` for secure connections
   - **IMAP_MAILBOX**: Mailbox to monitor (e.g., `INBOX`)

   > **Note**: For Gmail, generate an app password at https://myaccount.google.com/apppasswords

## Installation

### Development Environment

#### Python Environment
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

#### Node.js Environment
```bash
nodeenv -n 24.14.1 .nenv
source .nenv/bin/activate
cd frontend
npm install
```

#### Quick Setup
```bash
source scripts/devenv.sh
```

### Database Setup

Start PostgreSQL:
```bash
cd mailextractor
docker-compose up -d
```

Run migrations:
```bash
alembic upgrade head
```

## Usage

### Development

1. **Import Workflows**:
   ```bash
   python scripts/import_workflow.py
   ```

2. **Process Emails**:
   ```bash
   python scripts/read_email.py
   python scripts/process.py
   ```

3. **Start Web Interface**:
   ```bash
   bash scripts/webserver-dev.sh
   ```

### Production Deployment

1. Copy and configure the production environment file:
   ```bash
   cp .env.prod.example .env.prod
   # Edit .env.prod with your production settings
   ```

2. Start the application:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

## Project Structure

```
mailextractor/app/
  ├── steps/           # Workflow step implementations
  ├── poller/          # Email fetching logic
  └── workflow.py      # Workflow engine
mailextractor/backend/
  ├── routes/          # API endpoints
  └── services/        # Business logic
frontend/src/          # React web interface
scripts/               # Utility scripts
```

## Available Workflow Steps

- `AttachmentPatternStep`: Filter emails by attachment patterns
- `SaveAttachmentStep`: Save attachments to filesystem
- `ExtractAttachmentsStep`: Extract attachment data
- `ProviderFilterStep`: Filter by email provider
- `ForEachStep`: Iterate over collections

See [docs/workflow.md](docs/workflow.md) for workflow configuration details.

## Troubleshooting

### Database Connection Issues
- Verify PostgreSQL is running: `docker ps`
- Check DATABASE_URL in `.env` matches your PostgreSQL credentials
- Ensure port 5432 is not already in use

### Email Connection Issues
- For Gmail: Verify app password is correct (not your regular password)
- For other IMAP servers: Check IMAP_HOST and IMAP_PORT settings
- Verify IMAP_USE_SSL is set to `true` for secure connections

### Frontend Not Loading
- Check VITE_BASE_PATH matches BASE_PATH in `.env`
- Verify frontend build completed successfully
- Check browser console for errors

## License

MIT License - see [LICENSE.txt](LICENSE.txt) for details.

Copyright (c) 2026 MB 12 Solved (Maja Vinceviciute, Rokas Uzpurvis, Henryk Gerlach)

## Documentation

- [Workflow Configuration](docs/workflow.md)
- [Magic Variables](docs/magic_variables.md)
- [Context Ideas](docs/context_idea.md)
- [Changelog](CHANGELOG.md)
