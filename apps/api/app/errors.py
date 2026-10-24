"""Every error response has the shape {"error": {"code", "message", "field"}}."""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

STATUS_CODES = {400: "bad_request", 401: "unauthorized", 403: "forbidden", 404: "not_found",
                409: "conflict", 422: "validation_error"}


class ApiError(Exception):
    def __init__(self, status: int, message: str, code: str | None = None, field: str | None = None):
        self.status, self.message, self.field = status, message, field
        self.code = code or STATUS_CODES.get(status, "error")


def _body(code: str, message: str, field: str | None = None) -> dict:
    return {"error": {"code": code, "message": message, "field": field}}


def install(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(_body(exc.code, exc.message, exc.field), status_code=exc.status)

    @app.exception_handler(HTTPException)
    async def http_error(_: Request, exc: HTTPException) -> JSONResponse:
        code = STATUS_CODES.get(exc.status_code, "error")
        return JSONResponse(_body(code, str(exc.detail)), status_code=exc.status_code, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        loc = [str(p) for p in first.get("loc", ()) if p not in ("body", "query", "path")]
        message = str(first.get("msg", "Invalid request"))
        return JSONResponse(_body("validation_error", message, ".".join(loc) or None), status_code=422)
