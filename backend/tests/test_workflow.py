
import pytest
from fastapi import HTTPException

from app.workflow import validate_transition


def test_open_to_in_progress():
    validate_transition("open", "in_progress")


def test_in_progress_to_resolved():
    validate_transition("in_progress", "resolved")


def test_resolved_to_closed():
    validate_transition("resolved", "closed")


def test_invalid_transition():
    with pytest.raises(HTTPException) as error:
        validate_transition("open", "closed")

    assert error.value.status_code == 400


def test_closed_cannot_reopen():
    with pytest.raises(HTTPException) as error:
        validate_transition("closed", "open")

    assert error.value.status_code == 400
