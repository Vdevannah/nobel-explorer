"""Uniform, JSON-serialisable tool envelopes and safe error handling.

Every tool returns::

    {"tool": <name>, "ok": true,  "data": {...}}
    {"tool": <name>, "ok": false, "error": {"type": <kind>, "message": <text>}}

Error messages never include tracebacks, SQL, connection strings or driver
messages (MySQL errors can contain the DB user name and host); database
failures report only the numeric driver error code.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

from pydantic import ValidationError
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from backend.ai.tools.context import IndexUnavailableError
from backend.services.exceptions import ResourceNotFoundError, ServiceValidationError

logger = logging.getLogger(__name__)

ERROR_TYPES = (
    "validation_error",
    "not_found",
    "database_unavailable",
    "database_error",
    "index_unavailable",
    "index_incompatible",
    "index_error",
    "internal_error",
)


def format_validation_error(error: ValidationError) -> str:
    parts = []
    for item in error.errors(include_url=False, include_input=False):
        location = ".".join(str(p) for p in item.get("loc", ())) or "arguments"
        parts.append(f"{location}: {item.get('msg', 'invalid value')}")
    return "; ".join(parts)[:600]


def ok(tool: str, data: dict[str, Any]) -> dict[str, Any]:
    envelope = {"tool": tool, "ok": True, "data": data}
    return ensure_json_serialisable(envelope)


def error(tool: str, kind: str, message: str) -> dict[str, Any]:
    if kind not in ERROR_TYPES:
        kind = "internal_error"
    return {"tool": tool, "ok": False, "error": {"type": kind, "message": message}}


def ensure_json_serialisable(payload: dict[str, Any]) -> dict[str, Any]:
    """Round-trip through JSON so callers always receive plain JSON types."""
    return json.loads(json.dumps(payload, ensure_ascii=False, allow_nan=False))


def run_safely(tool: str, func: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    """Execute ``func`` and translate every failure into an error envelope."""
    from backend.ai.vector_store import EmbeddingModelMismatchError

    try:
        return ok(tool, func())
    except ValidationError as exc:
        return error(tool, "validation_error", format_validation_error(exc))
    except ResourceNotFoundError as exc:
        return error(tool, "not_found", f"{exc.resource} not found: {exc.identifier}")
    except ServiceValidationError as exc:  # includes SearchValidationError
        return error(tool, "validation_error", str(exc)[:600])
    except OperationalError as exc:
        code = exc.orig.args[0] if getattr(exc, "orig", None) is not None and exc.orig.args else "unknown"
        logger.warning("%s: database unavailable (driver code %s)", tool, code)
        return error(tool, "database_unavailable",
                     f"The Nobel database is unavailable (driver error code {code}).")
    except SQLAlchemyError as exc:
        logger.warning("%s: database error %s", tool, type(exc).__name__)
        return error(tool, "database_error", f"The database query failed ({type(exc).__name__}).")
    except IndexUnavailableError as exc:
        return error(tool, "index_unavailable", str(exc))
    except EmbeddingModelMismatchError:
        return error(tool, "index_incompatible",
                     "The knowledge index was built with a different embedding model. Rebuild it.")
    except Exception as exc:  # noqa: BLE001 - last-resort guard; no traceback leaves the tool
        if type(exc).__module__.split(".", 1)[0] == "chromadb":
            logger.warning("%s: vector index error %s", tool, type(exc).__name__)
            return error(tool, "index_error", f"The knowledge index query failed ({type(exc).__name__}).")
        logger.exception("%s: unexpected failure", tool)
        return error(tool, "internal_error", f"The tool failed unexpectedly ({type(exc).__name__}).")
