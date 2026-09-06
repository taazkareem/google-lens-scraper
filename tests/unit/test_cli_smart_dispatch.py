"""SPDX-FileCopyrightText: © 2026 Talib Kareem <taazkareem@icloud.com>
SPDX-License-Identifier: MIT

Unit tests for CLI smart dispatch (image vs text) and shop subcommand.
"""

from unittest.mock import MagicMock, patch
from click.testing import CliRunner
import pytest

from google_lens_pro.cli import cli
from google_lens_pro.models.shopping import ShoppingOffer, ShoppingResult
from google_lens_pro.models.common import NormalizedPrice


@pytest.fixture
def mock_shop_result():
    return ShoppingResult(
        query="Sony Headphones",
        total_offers=1,
        offers=[
            ShoppingOffer(
                title="Sony WH-1000XM5",
                merchant_name="Best Buy",
                direct_url="https://bestbuy.com/headphones",
                price=NormalizedPrice(amount=349.99, currency="USD", raw="$349.99"),
            )
        ],
        min_price=349.99,
        max_price=349.99,
        avg_price=349.99,
        currency="USD",
    )


def test_cli_shop_subcommand_json(mock_shop_result):
    """Verify explicit 'lens shop' subcommand with JSON output."""
    runner = CliRunner()

    with patch("google_lens_pro.engines.shopping.engine.ShoppingEngine.search", return_value=mock_shop_result):
        result = runner.invoke(cli, ["shop", "Sony Headphones", "--json-output"])
        assert result.exit_code == 0
        assert '"total_offers": 1' in result.output
        assert "Sony WH-1000XM5" in result.output


def test_cli_shop_subcommand_flags(tmp_path, mock_shop_result):
    """Verify 'lens shop' exports CSV and JSON correctly."""
    runner = CliRunner()
    csv_file = tmp_path / "shop.csv"
    json_file = tmp_path / "shop.json"

    with patch("google_lens_pro.engines.shopping.engine.ShoppingEngine.search", return_value=mock_shop_result):
        result = runner.invoke(
            cli,
            [
                "shop",
                "Sony Headphones",
                "--country", "UK",
                "--currency", "GBP",
                "--export-csv", str(csv_file),
                "--export-json", str(json_file),
            ],
        )
        assert result.exit_code == 0
        assert csv_file.exists()
        assert json_file.exists()


def test_cli_smart_dispatch_text_query(mock_shop_result):
    """Verify passing a text product query directly without subcommand routes to 'shop'."""
    runner = CliRunner()

    with patch("google_lens_pro.engines.shopping.engine.ShoppingEngine.search", return_value=mock_shop_result):
        result = runner.invoke(cli, ["Sony Headphones", "--json-output"])
        assert result.exit_code == 0
        assert '"total_offers": 1' in result.output
