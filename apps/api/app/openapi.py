"""Print the API's OpenAPI schema: python -m app.openapi > apps/web/lib/api/openapi.json"""
import json

from app.main import app

if __name__ == "__main__":
    print(json.dumps(app.openapi(), indent=2))  # ASCII-only, so the Windows console encoding can't break it
