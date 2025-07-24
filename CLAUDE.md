# CLAUDE.md - LeoLab API Foundation

This file provides guidance to Claude Code when working with the LeoLab API Foundation repository.

## 🚨 MANDATORY: Development Workflow

**BEFORE making ANY changes to this repository, you MUST follow the LeoLab Development Workflow:**

📖 **READ**: `/Users/leomaguire/Documents/GitHub/DEVELOPMENT-WORKFLOW.md`

**Key Requirements:**
- ✅ **Always create feature branches** - Never commit directly to main
- ✅ **Use pull requests** - All changes go through PR review process  
- ✅ **Follow commit standards** - Include proper commit messages with Claude signature
- ✅ **No secrets in code** - All credentials must come from Vault
- ✅ **Link to Jira tickets** - Reference INFRA-XX tickets in PRs
- ✅ **API design standards** - Follow FastAPI best practices
- ✅ **Attribution maintained** - Preserve credit to original author (Clint)

**Branch Protection**: The `main` branch is protected - you cannot push directly to it.

## Project Overview

This repository is the FastAPI foundation for LeoLab infrastructure APIs, originally forked from Clint's excellent Python API Website. It provides the base architecture for building REST APIs that integrate with the leoslab-toolkit.

## Attribution

This project builds upon the solid foundation created by **Clint** at [sln-app-dev/python-api-website](https://github.com/sln-app-dev/python-api-website). His original work provides clean FastAPI patterns, async/await implementation, and excellent development practices.

## Architecture

### Base Components (from Clint's work)
- **FastAPI Framework**: Modern, fast web framework for building APIs
- **SQLAlchemy + SQLite**: Database ORM and lightweight storage
- **Async/Await Patterns**: High-performance asynchronous operations
- **Automatic Documentation**: Built-in Swagger UI and ReDoc
- **Comprehensive Logging**: File and console logging with rotation
- **Health Checks**: Built-in health monitoring endpoints

### LeoLab Integration Patterns
- **Toolkit Integration**: Imports and uses leoslab-toolkit for backend operations
- **Vault Authentication**: Secure credential management through HashiCorp Vault
- **Jira Operations**: REST endpoints for Jira ticket management
- **Infrastructure APIs**: Endpoints for infrastructure automation

## Development Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run in development mode
uvicorn main:app --reload

# Access documentation
open http://localhost:8000/docs
```

## API Design Standards

### Endpoint Patterns
- **GET /health** - Health check (required)
- **GET /{resource}** - List resources
- **GET /{resource}/{id}** - Get specific resource
- **POST /{resource}** - Create resource
- **PUT /{resource}/{id}** - Update resource
- **DELETE /{resource}/{id}** - Delete resource

### Response Standards
- **200**: Success with data
- **201**: Created successfully
- **400**: Bad request (client error)
- **401**: Unauthorized
- **404**: Not found
- **500**: Internal server error

### Security Requirements
- All endpoints that interact with external services use Vault for authentication
- No secrets or credentials in code or configuration files
- Proper error handling without exposing internal details
- Input validation on all endpoints

## Integration with LeoLab Toolkit

### Example Usage
```python
from leoslab_toolkit import JiraClient, VaultClient

# In your FastAPI endpoints
@app.post("/jira/issues/{issue_key}/transition")
async def transition_issue(issue_key: str, transition: str):
    jira = JiraClient()
    result = jira.transition_issue(issue_key, transition)
    return {"status": "success", "result": result}
```

### Vault Integration
```python
@app.get("/vault/health")
async def vault_health():
    vault = VaultClient()
    health = vault.health_check()
    return health
```

## Future Enhancements

Based on INFRA-12 and integration roadmap:
- Infrastructure management endpoints
- Real-time monitoring APIs
- Bulk operation endpoints
- Webhook handlers for automation
- Dashboard data APIs

## Common Operations

### Running the API
```bash
# Development
python main.py

# Production
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Testing Endpoints
```bash
# Health check
curl http://localhost:8000/health

# API documentation
open http://localhost:8000/docs
```

## Related Projects

- **leoslab-toolkit**: Python package for infrastructure operations
- **leoslab-k8s-infra**: Infrastructure as Code repository
- **Original Project**: [sln-app-dev/python-api-website](https://github.com/sln-app-dev/python-api-website)