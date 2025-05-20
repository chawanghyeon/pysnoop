# server/utils/message.py
import json
from datetime import datetime, timezone
from typing import Any, Dict, Tuple, Type, Union  # Ensure Type, Tuple, Union are imported


class MessageParseError(Exception):
    pass


# Define a type alias for the valid types for the second argument of isinstance().
# This can be a single type (e.g., str, int) or a tuple of types (e.g., (int, float)).
_ClassInfo = Union[Type[Any], Tuple[Type[Any], ...]]


def parse_message(
    raw_line: str,
) -> Dict[str, Any]:  # Changed return type from plain dict
    try:
        # Give msg an explicit type hint
        msg: Dict[str, Any] = json.loads(raw_line)

        # Explicitly type the 'required_fields' dictionary.
        # The values are of type _ClassInfo.
        required_fields: Dict[str, _ClassInfo] = {
            "type": str,
            "uri": str,
            "ts": str,  # Further validation for ISO format happens later
            "value": (int, float),  # This is a Tuple[Type[int], Type[float]]
            "token": str,
            "signature": str,
        }

        for field, expected_classinfo in required_fields.items():
            if field not in msg:
                raise MessageParseError(f"Missing required field: '{field}'")

            # This is line 27 (or equivalent after minor changes for typing).
            # With 'expected_classinfo' correctly typed as _ClassInfo, Mypy should be happy.
            if not isinstance(msg[field], expected_classinfo):
                # The previous nested if/else for "value" was redundant.
                # If the type doesn't match, we should raise an error directly.
                raise MessageParseError(
                    f"Invalid type for field '{field}': "
                    f"Expected a type from {expected_classinfo}, got {type(msg[field]).__name__}"
                )

        # Timestamp validation: ensure it's a valid ISO 8601 string and convert to UTC
        try:
            # Assuming 'ts' field passed the 'str' type check above.
            parsed_ts = datetime.fromisoformat(str(msg["ts"]).replace("Z", "+00:00"))
            if parsed_ts.tzinfo is None:  # Ensure timezone-aware
                parsed_ts = parsed_ts.replace(tzinfo=timezone.utc)
            msg["ts_datetime"] = parsed_ts  # Store the parsed datetime object
        except ValueError as e:
            raise MessageParseError(
                f"Invalid timestamp format for 'ts' field: {msg['ts']}. Error: {e}"
            )
        except TypeError as e:  # Handles if msg["ts"] is not string-like
            raise MessageParseError(f"Timestamp 'ts' field must be a string. Error: {e}")

        # Example: URI specific validation (can be expanded)
        # This assumes 'value' has already passed the (int, float) check if it's the 'value' field.
        if msg["uri"].startswith("/sensitive/") and not isinstance(msg["value"], int):
            # This check is more specific: if it's sensitive, it must be an int, not allowing float.
            raise MessageParseError(
                f"Value for sensitive URI '{msg['uri']}' must be an integer, got {type(msg['value']).__name__}."  # noqa
            )

        return msg
    except json.JSONDecodeError as e:
        raise MessageParseError(f"Invalid JSON message: {e}")
    # Consider if a broad "except Exception" is needed or if specific errors are better.
    # For now, specific exceptions are handled.
