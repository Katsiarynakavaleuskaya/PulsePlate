from fastapi.security import APIKeyHeader

# Shared API key header for all routers
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
