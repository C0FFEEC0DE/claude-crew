"""Tests for validating claude-code settings.json hooks structure."""
import json
from pathlib import Path


HOOK_EVENTS = {
    "SessionStart",
    "InstructionsLoaded",
    "UserPromptSubmit",
    "PreToolUse",
    "PermissionRequest",
    "PermissionDenied",
    "PostToolUse",
    "PostToolUseFailure",
    "SubagentStart",
    "SubagentStop",
    "Stop",
    "TeammateIdle",
    "TaskCompleted",
    "ConfigChange",
    "PreCompact",
    "PostCompact",
    "SessionEnd",
}

VALID_HOOK_KEYS = {"type", "command", "async"}
VALID_EVENT_KEYS = {"matcher", "hooks"}


def load_settings_json() -> dict:
    """Load the settings.json from claudecfg directory."""
    repo_root = Path(__file__).resolve().parents[1]
    settings_path = repo_root / "claudecfg" / "settings.json"
    with settings_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_hook_object(hook_obj: dict, event_name: str, has_matcher: bool) -> list[str]:
    """
    Validate a single hook object within an event array.

    Args:
        hook_obj: The hook object to validate
        event_name: Name of the hook event (for error messages)
        has_matcher: Whether this event uses matcher-based format

    Returns:
        List of validation errors
    """
    errors = []

    if has_matcher:
        # Matcher-based format: {"matcher": "...", "hooks": [...]}
        if "matcher" not in hook_obj:
            errors.append(f"{event_name}: hook record missing required 'matcher' key")
        if "hooks" not in hook_obj:
            errors.append(f"{event_name}: hook record missing required 'hooks' key")
        elif not isinstance(hook_obj["hooks"], list):
            errors.append(f"{event_name}: 'hooks' must be an array")
        else:
            # Validate nested hook definitions
            for idx, nested_hook in enumerate(hook_obj["hooks"]):
                nested_errors = validate_hook_definition(nested_hook, f"{event_name}[{idx}].hooks")
                errors.extend(nested_errors)

        # Check for invalid keys (keys other than matcher/hooks)
        invalid_keys = set(hook_obj.keys()) - VALID_EVENT_KEYS
        if invalid_keys:
            errors.append(f"{event_name}: invalid keys in hook record: {invalid_keys}")
    else:
        # Flat format: {"type": "...", "command": "..."}
        # Check for invalid nested 'hooks' key (common mistake)
        if "hooks" in hook_obj:
            errors.append(
                f"{event_name}: invalid 'hooks' key in flat format - "
                f"hook objects should be direct array elements, not nested"
            )
        if "matcher" in hook_obj:
            errors.append(
                f"{event_name}: has 'matcher' key but event should use flat format"
            )

        # Validate hook definition keys
        def_errors = validate_hook_definition(hook_obj, event_name)
        errors.extend(def_errors)

    return errors


def validate_hook_definition(hook_def: dict, path: str) -> list[str]:
    """
    Validate a hook definition object (type/command structure).

    Args:
        hook_def: The hook definition to validate
        path: Path string for error reporting

    Returns:
        List of validation errors
    """
    errors = []

    if not isinstance(hook_def, dict):
        errors.append(f"{path}: hook definition must be an object, got {type(hook_def).__name__}")
        return errors

    if "type" not in hook_def:
        errors.append(f"{path}: hook definition missing required 'type' key")

    if hook_def.get("type") == "command" and "command" not in hook_def:
        errors.append(f"{path}: command hook missing required 'command' key")

    # Check for invalid keys
    invalid_keys = set(hook_def.keys()) - VALID_HOOK_KEYS
    if invalid_keys:
        errors.append(f"{path}: invalid keys in hook definition: {invalid_keys}")

    return errors


def test_settings_json_valid():
    """Test that settings.json is valid JSON."""
    settings = load_settings_json()
    assert isinstance(settings, dict)


def test_hooks_section_exists():
    """Test that hooks section exists in settings.json."""
    settings = load_settings_json()
    assert "hooks" in settings
    assert isinstance(settings["hooks"], dict)


def test_all_hook_events_are_known():
    """Test that all hook events in settings are known event types."""
    settings = load_settings_json()
    hook_events = set(settings["hooks"].keys())

    unknown_events = hook_events - HOOK_EVENTS
    assert not unknown_events, f"Unknown hook events in settings.json: {unknown_events}"


def test_hook_events_have_arrays():
    """Test that all hook events contain arrays."""
    settings = load_settings_json()

    for event_name, event_value in settings["hooks"].items():
        assert isinstance(event_value, list), f"{event_name}: must be an array"
        assert len(event_value) > 0, f"{event_name}: array must not be empty"


def test_session_start_flat_format():
    """Test that SessionStart uses flat format (no nested 'hooks' key)."""
    settings = load_settings_json()
    session_start = settings["hooks"].get("SessionStart", [])

    for idx, hook_obj in enumerate(session_start):
        assert "hooks" not in hook_obj, (
            f"SessionStart[{idx}]: invalid nested 'hooks' key - "
            f"use flat format for events without matcher"
        )
        assert "matcher" not in hook_obj, (
            f"SessionStart[{idx}]: should not have 'matcher' key in flat format"
        )


def test_matcher_based_events_have_correct_structure():
    """Test that matcher-based events have correct structure with matcher and hooks keys."""
    settings = load_settings_json()

    # Events that should use matcher-based format
    matcher_events = {
        "InstructionsLoaded",
        "PreToolUse",
        "PermissionRequest",
        "PermissionDenied",
        "PostToolUse",
        "PostToolUseFailure",
    }

    for event_name in matcher_events:
        if event_name not in settings["hooks"]:
            continue

        event_array = settings["hooks"][event_name]
        for idx, hook_obj in enumerate(event_array):
            assert "matcher" in hook_obj, (
                f"{event_name}[{idx}]: matcher-based events must have 'matcher' key"
            )
            assert "hooks" in hook_obj, (
                f"{event_name}[{idx}]: matcher-based events must have 'hooks' key"
            )
            assert isinstance(hook_obj["hooks"], list), (
                f"{event_name}[{idx}]: 'hooks' must be an array"
            )


def test_no_invalid_keys_in_hook_records():
    """Test that hook records don't contain invalid keys."""
    settings = load_settings_json()

    for event_name, event_array in settings["hooks"].items():
        # Determine if this event uses matcher-based format
        uses_matcher = event_name in {
            "InstructionsLoaded",
            "PreToolUse",
            "PermissionRequest",
            "PermissionDenied",
            "PostToolUse",
            "PostToolUseFailure",
        }

        for idx, hook_obj in enumerate(event_array):
            errors = validate_hook_object(hook_obj, f"{event_name}[{idx}]", uses_matcher)
            assert not errors, f"Validation errors: {'; '.join(errors)}"


def test_hook_definitions_have_required_keys():
    """Test that all hook definitions have required 'type' and 'command' keys."""
    settings = load_settings_json()

    for event_name, event_array in settings["hooks"].items():
        uses_matcher = event_name in {
            "InstructionsLoaded",
            "PreToolUse",
            "PermissionRequest",
            "PermissionDenied",
            "PostToolUse",
            "PostToolUseFailure",
        }

        for idx, hook_obj in enumerate(event_array):
            if uses_matcher:
                # Nested format
                for nested_idx, hook_def in enumerate(hook_obj.get("hooks", [])):
                    assert "type" in hook_def, (
                        f"{event_name}[{idx}].hooks[{nested_idx}]: missing 'type' key"
                    )
                    if hook_def.get("type") == "command":
                        assert "command" in hook_def, (
                            f"{event_name}[{idx}].hooks[{nested_idx}]: command hook missing 'command' key"
                        )
            else:
                # Flat format
                hook_def = hook_obj
                assert "type" in hook_def, (
                    f"{event_name}[{idx}]: missing 'type' key"
                )
                if hook_def.get("type") == "command":
                    assert "command" in hook_def, (
                        f"{event_name}[{idx}]: command hook missing 'command' key"
                    )


def test_flat_format_events_reject_nested_hooks_key():
    """
    Test that flat-format events (without matcher) reject nested 'hooks' key.

    This is a regression test for: PermissionDenied: Invalid key in record
    which occurred when hook objects were wrapped in {'hooks': [...]} instead
    of being direct array elements.
    """
    settings = load_settings_json()

    # Events that must use flat format (no matcher, no nested 'hooks')
    flat_format_events = {
        "SessionStart",
        "UserPromptSubmit",
        "SubagentStart",
        "SubagentStop",
        "Stop",
        "TeammateIdle",
        "TaskCompleted",
        "ConfigChange",
        "PreCompact",
        "PostCompact",
        "SessionEnd",
    }

    for event_name in flat_format_events:
        if event_name not in settings["hooks"]:
            continue

        event_array = settings["hooks"][event_name]
        for idx, hook_obj in enumerate(event_array):
            assert "hooks" not in hook_obj, (
                f"{event_name}[{idx}]: nested 'hooks' key is invalid - "
                f"this causes 'PermissionDenied: Invalid key in record' error. "
                f"Use flat format: {{'type': 'command', 'command': '...'}}"
            )
            assert "matcher" not in hook_obj, (
                f"{event_name}[{idx}]: 'matcher' key not allowed in flat format"
            )
