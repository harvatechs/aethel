"""Property tests for domain separation (Lemma 1, R-PROTO-09, PT0)."""

from hypothesis import given
from hypothesis import strategies as st

from aethel_codex.hashing import H, lp


@given(
    l1=st.binary(min_size=1, max_size=255),
    l2=st.binary(min_size=1, max_size=255),
)
def test_lp_prefix_free(l1: bytes, l2: bytes) -> None:
    """Length-prefixed encoding ensures no encoded label is a prefix of another."""
    if l1 != l2:
        lp1 = lp(l1)
        lp2 = lp(l2)
        # One cannot be a prefix of the other unless equal
        assert not (len(lp1) <= len(lp2) and lp2.startswith(lp1))
        assert not (len(lp2) <= len(lp1) and lp1.startswith(lp2))


@given(
    l1=st.binary(min_size=1, max_size=32),
    l2=st.binary(min_size=1, max_size=32),
    data=st.binary(min_size=0, max_size=128),
)
def test_domain_separation_distinct_hashes(l1: bytes, l2: bytes, data: bytes) -> None:
    """Distinct labels guarantee distinct hash outputs on the same payload."""
    if l1 != l2:
        assert H(l1, data) != H(l2, data)
