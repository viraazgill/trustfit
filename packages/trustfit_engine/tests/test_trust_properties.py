"""Property tests (Hypothesis) for the Trust Score."""
import datetime as dt

from conftest import AS_OF, CONFIG_DIR
from hypothesis import given, settings
from hypothesis import strategies as st

from trustfit_engine.config import load_trust_config
from trustfit_engine.models import Company, Evidence, Flag
from trustfit_engine.trust import score_trust

CFG = load_trust_config(CONFIG_DIR / "trust_v1.yaml")
PIDS = list(CFG.parameters)
LEVELS = CFG.scale_levels
FRESH = AS_OF - dt.timedelta(days=5)

# Parameters whose verified 0 is a knock-out are kept above 0 so the company stays scorable.
level_for = {pid: st.sampled_from([lv for lv in LEVELS if lv > 0] if CFG.parameters[pid].knockout_at_zero
                                  else LEVELS) for pid in PIDS}
evidence_maps = st.fixed_dictionaries({}, optional={pid: level_for[pid] for pid in PIDS})
roles = st.sampled_from(list(CFG.roles))
flag_lists = st.lists(st.one_of(
    st.sampled_from(list(CFG.overrides.caps)).map(lambda c: Flag(type="cap", code=c)),
    st.sampled_from(list(CFG.overrides.notches)).map(lambda c: Flag(type="notch", code=c)),
    st.just(Flag(type="fake_reviews", code="review_pattern")),
), max_size=4)
gate_maps = st.fixed_dictionaries({g: st.sampled_from(["passed", "pending", "failed"]) for g in CFG.gates})


def company(levels: dict, flags=(), gates=None) -> Company:
    return Company(id="prop", name="Prop (Demo)", fictional=True, flags=list(flags), gates=gates or {},
                   evidence={pid: Evidence(level=lv, verified=True, source_date=FRESH, checked_at=FRESH)
                             for pid, lv in levels.items()})


@settings(max_examples=300, deadline=None)
@given(evidence_maps, roles, flag_lists, gate_maps)
def test_score_stays_within_0_100(levels, role, flags, gates):
    r = score_trust(company(levels, flags, gates), role, CFG, AS_OF)
    if r["score"] is not None:
        assert 0 <= r["score"] <= 100
        assert 0 <= r["base_score"] <= 100
    if r.get("confidence") is not None:
        assert 0 <= r["confidence"] <= 100 + 1e-9


@settings(max_examples=300, deadline=None)
@given(evidence_maps.filter(bool), roles, st.data())
def test_raising_one_verified_level_never_lowers_base(levels, role, data):
    pid = data.draw(st.sampled_from(sorted(levels)))
    higher = [lv for lv in LEVELS if lv > levels[pid]]
    if not higher:
        return
    before = score_trust(company(levels), role, CFG, AS_OF)
    after = score_trust(company({**levels, pid: data.draw(st.sampled_from(higher))}), role, CFG, AS_OF)
    if before.get("base_score") is not None:
        assert after["base_score"] >= before["base_score"] - 1e-9


@settings(max_examples=300, deadline=None)
@given(evidence_maps, roles, st.data())
def test_verifying_one_more_parameter_never_lowers_confidence(levels, role, data):
    missing = [pid for pid in PIDS if pid not in levels]
    if not missing:
        return
    pid = data.draw(st.sampled_from(missing))
    before = score_trust(company(levels), role, CFG, AS_OF)
    after = score_trust(company({**levels, pid: data.draw(level_for[pid])}), role, CFG, AS_OF)
    assert after["confidence"] >= before["confidence"] - 1e-9
