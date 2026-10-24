import json
import subprocess
import sys

from conftest import CONFIG_DIR, REPO_ROOT, assert_matches, load_expected

from trustfit_engine.cli import main


def test_cli_prints_subros_supplier(capsys):
    code = main(["trust", str(REPO_ROOT / "seed" / "subros.json"), "--role", "supplier",
                 "--as-of", "2026-10-24", "--config-dir", str(CONFIG_DIR)])
    assert code == 0
    assert_matches(json.loads(capsys.readouterr().out), load_expected("subros_supplier.json"))


def test_cli_picks_a_demo_company(capsys):
    code = main(["trust", str(REPO_ROOT / "seed" / "demo_companies.json"), "--company", "western-flow",
                 "--role", "distributor", "--as-of", "2026-10-24", "--config-dir", str(CONFIG_DIR)])
    assert code == 0
    assert json.loads(capsys.readouterr().out)["company_id"] == "western-flow"


def test_module_entry_point_from_repo_root():
    out = subprocess.run(
        [sys.executable, "-m", "trustfit_engine", "trust", "seed/subros.json", "--role", "supplier",
         "--as-of", "2026-10-24"], cwd=REPO_ROOT, capture_output=True, text=True, check=True).stdout
    r = json.loads(out)
    assert (r["score"], r["verdict"], r["outlook"]) == (87, "Amber", "Watch")
