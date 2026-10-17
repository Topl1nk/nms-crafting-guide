"""The game extractor's parser, on a tiny hand-written MXML fixture.

tests/fixtures/mxml/ mimics MBINCompiler's output layout with invented items
(Testite, Fixture Pie), so this runs without the game, MBINCompiler or
hgpaktool. It checks the two things that would silently corrupt data/ if they
broke: telling MXML lists from structs, and handing build_data.py the same
shape NMS-Handbook does.
"""

from __future__ import annotations

import os
import stat
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_data  # noqa: E402
import extract_game  # noqa: E402

FIXTURE = Path(__file__).parent / "fixtures" / "mxml"


def test_mxml_shapes() -> None:
    xml = ET.fromstring(
        '<Property name="Rarity" value="GcRarity">'
        '<Property name="Rarity" value="Common" /></Property>')
    # An enum wrapper shares its child's name but is a struct, not a list.
    assert extract_game.mxml_value(xml) == {"Rarity": "Common"}
    assert extract_game.enum(extract_game.mxml_value(xml)) == "Common"

    xml = ET.fromstring(
        '<Property name="Ingredients">'
        '<Property name="Ingredients" value="GcRefinerRecipeElement" _id="A">'
        '<Property name="Id" value="A" /></Property></Property>')
    assert extract_game.mxml_value(xml) == [{"Id": "A"}]

    assert extract_game.mxml_value(ET.fromstring('<Property name="AltRequirements" />')) is None


def test_language_table() -> None:
    lang = extract_game.load_language([FIXTURE / "language" / "nms_loc1_english.MXML"])
    assert lang["T_ORE_NAME_L"] == "Testite"
    assert lang["T_ORE_DESC"] == "Found only in <TECHNOLOGY>unit tests<>."


@pytest.fixture(scope="module")
def tables(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("json")
    counts = extract_game.convert(FIXTURE, out, {"source": "game", "summary": "fixture"})
    assert counts == {"substances": 1, "products": 2, "refining": 2, "cooking": 1}
    return out


def test_handbook_shape(tables: Path) -> None:
    import json

    subs = json.loads((tables / "Substance_Table.json").read_text())
    assert subs["T_ORE"]["NameLower_Text"] == "Testite"
    assert subs["T_ORE"]["Category"] == "Earth"
    assert subs["T_ORE"]["BaseValue"] == "7"

    products = json.loads((tables / "Product_Table.json").read_text())
    pie = products["T_PIE"]
    assert (pie["Type"], pie["Consumable"]) == ("Consumable", "true")
    # The stat's display name comes from the loc string keyed by the enum.
    assert pie["FoodBonusStatType"] == "Suit_Energy"
    assert pie["FoodBonusStatTypeText"] == "Pretend Stamina"
    assert products["T_BAR"]["FoodBonusStatTypeText"] == ""

    refining = json.loads((tables / "Refining_Table.json").read_text())
    assert list(refining) == ["T_BAR", "T_ORE"]  # grouped by output, game order
    loop = refining["T_ORE"]["Recipes"][0]
    assert loop["RecipeName"] == "Test Smelting"
    assert loop["RecipeType"] == "Requested Operation: Test Smelting"
    assert loop["Amount"] == "6"
    assert [(i["Id"], i["Amount"]) for i in loop["Ingredients"]] == [("T_ORE", "1"), ("T_BAR", "2")]

    cooking = json.loads((tables / "Cooking_Table.json").read_text())
    assert list(cooking) == ["T_PIE"]
    assert json.loads((tables / "_source.json").read_text())["summary"] == "fixture"


def test_build_data_reads_it(tables: Path, monkeypatch) -> None:
    """End to end through the normaliser, as `mise run extract` does it."""
    monkeypatch.setattr(build_data, "CACHE", tables)
    items = build_data.build_items(build_data.load("Substance_Table.json"),
                                   build_data.load("Product_Table.json"))
    recipes = build_data.build_recipes(build_data.load("Refining_Table.json"), "refine", items)
    recipes += build_data.build_recipes(build_data.load("Cooking_Table.json"), "cook", items)

    assert items["T_ORE"]["name"] == "Testite"
    assert items["T_PIE"]["effect"] == "Pretend Stamina"
    assert items["T_PIE"]["potency"] == 0.42
    assert items["T_PIE"]["edible"] is True

    smelt, loop, bake = recipes
    assert (smelt["output"], smelt["machine"], smelt["time"]) == (
        {"id": "T_BAR", "n": 2}, "Portable / Personal Refiner", 30.0)
    assert loop["machine"] == "Medium Refiner"
    assert loop["loop"] == 6.0  # 1 seed in, 6 out
    assert (bake["domain"], bake["machine"], bake["operation"]) == (
        "cook", "Nutrient Processor", "Test Baking")


def test_decompile_refuses_unrecognised_files(tmp_path, monkeypatch) -> None:
    """MBINCompiler exits 0 on a struct mismatch; the extractor must not."""
    src = tmp_path / "mbin" / "language"
    src.mkdir(parents=True)
    (src / "nms_loc1_english.mbin").write_bytes(b"\xcc" * 16)
    fake = tmp_path / "MBINCompiler"
    fake.write_text("#!/bin/sh\n"
                    "echo '[WARN]: File not recognized. You may need to use an older "
                    "(or newer) version of MBINCompiler.'\n"
                    "echo '1 files converted.'\nexit 0\n")
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("MBINCOMPILER", str(fake))
    if os.name == "nt":
        pytest.skip("shell-script stand-in")
    with pytest.raises(SystemExit) as exc:
        extract_game.decompile(tmp_path / "mbin", tmp_path / "mxml")
    assert "File not recognized" in str(exc.value)
    assert "mbin-releases" in str(exc.value)
