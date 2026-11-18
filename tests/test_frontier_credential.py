"""Credential file handling never executes shell content or prints secrets."""

import pytest

from tools.run_frontier_pair import credential_from_file


def test_reads_single_owner_key_as_plain_data(tmp_path):
    secret = "sk-synthetic-private-value"
    path = tmp_path / ".env"
    path.write_text(f"AIA_GPT='{secret}'\nUNRELATED=$(false)\n", "utf-8")
    assert credential_from_file(path) == secret


@pytest.mark.parametrize("contents", ["", "AIA_GPT=placeholder\n", "AIA_GPT=sk-a\nAIA_GPT=sk-b\n"])
def test_rejects_missing_or_ambiguous_key(tmp_path, contents):
    path = tmp_path / ".env"
    path.write_text(contents, "utf-8")
    with pytest.raises(ValueError):
        credential_from_file(path)
