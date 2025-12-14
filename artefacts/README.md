# Artefacts Directory

This directory is for storing files that can be read and written by agents.

## Purpose
- **File Reader Agent**: Read files from this directory
- **File Writer Agent**: Write files to this directory (JSON, CSV, TXT, MD, LOG)
- **API Caller Agent**: Save API responses here
- **Airtable Agent**: Export records to files here

## Security
Only files within this directory and the project root can be accessed for security.

## Important Notes
⚠️ **Files in this directory are gitignored** - They will NOT be committed to version control.

This is intentional to prevent accidentally committing:
- API responses with sensitive data
- User-generated content
- Temporary files
- Test data

The directory structure is preserved via `.gitkeep`, but all other files are excluded from git.
