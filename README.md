# LeoLab API Foundation

A FastAPI-based foundation for LeoLab infrastructure APIs, originally forked from Clint's excellent Python API Website.

## Attribution

This project is built upon the solid foundation created by **Clint** at [sln-app-dev/python-api-website](https://github.com/sln-app-dev/python-api-website). 

🙏 **Huge thanks to Clint** for:
- Clean, well-structured FastAPI architecture
- Excellent async/await patterns with SQLAlchemy
- Comprehensive logging implementation
- Solid development patterns and best practices

His original work provides the perfect foundation for building LeoLab's infrastructure management APIs.

## About This Fork

This fork adapts Clint's base architecture to serve as the foundation for LeoLab's infrastructure management APIs, including integrations with Jira, HashiCorp Vault, and infrastructure automation tools.

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the API

```bash
python main.py
```

## Runnign the API in dev
```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

## API Documentation

Interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Logging
Logging is configured to log to a file named `app.log`. You can change the logging level in the `main.py` file. To tail the log file, you can use:
```bash
tail -f app.log
``` 

## Endpoints

- `GET /` - Welcome message
- `GET /health` - Health check
- `GET /items` - Get all items
- `GET /items/{id}` - Get item by ID
- `POST /items` - Create new item
- `PUT /items/{id}` - Update item
- `DELETE /items/{id}` - Delete item
