"""prompts/06-demo-polish.md: scoring a company and building the Sorano bridge each respond in under 1 s."""
import time

API = "/api/v1"
BUDGET_S = 1.0


def timed(call) -> float:
    call()  # warm-up: config loading and the first database round trips
    start = time.perf_counter()
    res = call()
    elapsed = time.perf_counter() - start
    assert res.status_code == 200, res.text
    return elapsed


def test_scoring_a_company_is_under_a_second(client, as_analyst):
    elapsed = timed(lambda: client.post(f"{API}/companies/subros/trust-score", json={"role": "supplier"},
                                        headers=as_analyst))
    assert elapsed < BUDGET_S, f"trust-score took {elapsed:.2f}s"


def test_building_the_sorano_bridge_is_under_a_second(client, as_viewer):
    elapsed = timed(lambda: client.post(f"{API}/smes/sorano/bridge", headers=as_viewer))
    assert elapsed < BUDGET_S, f"bridge took {elapsed:.2f}s"
