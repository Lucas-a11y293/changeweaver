import pytest

from changeweaver.domain.errors import ConfigurationError
from changeweaver.infrastructure.config import match_layer, parse_contract


def test_parse_contract_and_match_layer() -> None:
    contract = parse_contract(
        {
            "version": 1,
            "project": {
                "name": "demo",
                "roots": ["lib"],
                "include": ["**/*.dart"],
                "exclude": ["**/*.g.dart"],
            },
            "architecture": {
                "layers": [
                    {"name": "presentation", "paths": ["lib/presentation/**"]},
                    {"name": "domain", "paths": ["lib/domain/**"]},
                ],
                "rules": [],
            },
            "analysis": {},
        }
    )

    assert match_layer("lib/presentation/page.dart", contract.layers) == "presentation"
    assert match_layer("lib/domain/user.dart", contract.layers) == "domain"
    assert match_layer("lib/unknown.dart", contract.layers) is None


def test_unknown_contract_keys_fail_closed() -> None:
    with pytest.raises(ConfigurationError, match="unknown keys"):
        parse_contract(
            {
                "version": 1,
                "project": {"name": "demo", "roots": ["lib"], "include": ["**/*.dart"], "exclude": []},
                "architecture": {"layers": [], "rules": []},
                "analysis": {"unexpected": True},
            }
        )
