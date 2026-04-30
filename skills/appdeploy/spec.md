---
name: appdeploy
description: Deploy web apps with backend APIs, database, file storage, AI operations, authentication, realtime, and cron jobs. Use when the user asks to deploy or publish a website or web app and wants a public URL. Uses HTTP API via curl.
allowed-tools:
  - Bash
metadata:
  author: appdeploy
  version: "1.0.7"
---

# AppDeploy Skill

Deploy web apps to AppDeploy via HTTP API.

## Setup (First Time Only)

1. **Check for existing API key:**
   - Look for a `.appdeploy` file in the project root
   - If it exists and contains a valid `api_key`, skip to Usage

2. **If no API key exists, register and get one:**
   ```bash
   curl -X POST https://api-v2.appdeploy.ai/mcp/api-key \
     -H "Content-Type: application/json" \
     -d '{"client_name": "claude-code"}'
   ```

3. **Save credentials to `.appdeploy`:**
   ```json
   {
     "api_key": "ak_...",
     "endpoint": "https://api-v2.appdeploy.ai/mcp"
   }
   ```

   Add `.appdeploy` to `.gitignore` if not already present.

## Usage

Make JSON-RPC calls to the MCP endpoint.

## Available Tools

- **deploy_app**: Deploy or update a web app (sends source code to third-party service)
- **delete_app**: Permanently delete an app (irreversible)
- **get_deploy_instructions**: Get deployment constraints
- **get_app_template**: Get base app template
- **get_app_status**: Check deployment status, QA snapshot, error logs
- **get_app_versions**: List deployable versions
- **apply_app_version**: Deploy a specific version
- **src_glob**: Discover files in app source
- **src_grep**: Search app source code
- **src_read**: Read app source files
- **get_apps**: List user's deployed apps
