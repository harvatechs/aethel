"""Unit tests for manuscript publishing, atomic writing, and revision (specs.md §7, §10)."""

from pathlib import Path

import pytest

from aethel_codex.errors import AethelError, InternalError
from aethel_codex.keyfile import create_key, load_key
from aethel_codex.publish import (
    AssetInput,
    PublishRequest,
    publish_bundle,
    revise_bundle,
)
from aethel_codex.verify import verify_bundle


@pytest.mark.req("UR-08")
@pytest.mark.req("UR-10")
@pytest.mark.req("UR-11")
@pytest.mark.req("UR-12")
def test_publish_genesis_attributed(tmp_path: Path) -> None:
    manuscript = tmp_path / "essay.md"
    manuscript.write_bytes(b"# On Names\n\nContent for the essay.\n")

    key_path = tmp_path / "author.aek"
    create_key("ml-dsa-87", key_path, passphrase="password123")  # noqa: S106

    req = PublishRequest(
        manuscript_path=manuscript,
        title="On Names",
        license="CC-BY-4.0",
        lang="en",
        keys=[key_path],
        passphrases=["password123"],
        out_dir=tmp_path / "bundles",
    )

    res = publish_bundle(req)
    assert res.bundle_path is not None
    assert res.bundle_path.exists()
    assert (res.bundle_path / "manifest.pip").exists()
    assert (res.bundle_path / "text.md").exists()
    assert len(res.envelopes) == 1

    # Verify produced bundle
    report = verify_bundle(res.bundle_path)
    assert report.integrity == "PASS"
    assert report.attribution.cls == "Attributed"
    assert report.attribution.signed == 1
    assert report.attribution.declared == 1
    assert report.checks_dict()["V1"] == "PASS"
    assert report.checks_dict()["V2"] == "PASS"
    assert report.checks_dict()["V6"] == "PASS"


def test_publish_genesis_unsigned(tmp_path: Path) -> None:
    manuscript = tmp_path / "paper.txt"
    manuscript.write_bytes(b"Plain text manuscript.\n")

    req = PublishRequest(
        manuscript_path=manuscript,
        title="Unsigned Paper",
        license="MIT",
        lang="und",
        unsigned=True,
        out_dir=tmp_path / "bundles",
    )

    res = publish_bundle(req)
    assert res.bundle_path is not None
    assert (res.bundle_path / "text.txt").exists()
    assert len(res.envelopes) == 0

    report = verify_bundle(res.bundle_path)
    assert report.integrity == "PASS"
    assert report.attribution.cls == "Unattributed"
    assert report.attribution.signed == 0


def test_publish_dry_run(tmp_path: Path) -> None:
    manuscript = tmp_path / "draft.md"
    manuscript.write_bytes(b"# Draft\n\nDraft text.\n")
    out_dir = tmp_path / "bundles"

    req = PublishRequest(
        manuscript_path=manuscript,
        title="Draft",
        license="CC0-1.0",
        unsigned=True,
        out_dir=out_dir,
        dry_run=True,
    )

    res = publish_bundle(req)
    assert res.dry_run is True
    assert res.bundle_path is None
    assert not out_dir.exists()
    assert str(res.manifest_pid).startswith("pip1:m:")
    assert str(res.text_pid).startswith("pip1:t:")


def test_publish_idempotent_republish(tmp_path: Path) -> None:
    manuscript = tmp_path / "idem.md"
    manuscript.write_bytes(b"Idempotent text.\n")

    req = PublishRequest(
        manuscript_path=manuscript,
        title="Idempotent Test",
        license="CC0-1.0",
        unsigned=True,
        out_dir=tmp_path / "bundles",
    )

    res1 = publish_bundle(req)
    res2 = publish_bundle(req)
    assert res1.bundle_path == res2.bundle_path


def test_publish_collision_different_content(tmp_path: Path) -> None:
    manuscript = tmp_path / "doc.md"
    manuscript.write_bytes(b"Document text.\n")

    req = PublishRequest(
        manuscript_path=manuscript,
        title="Collision Test",
        license="CC0-1.0",
        unsigned=True,
        out_dir=tmp_path / "bundles",
    )

    # Pre-create directory with conflicting text
    out_bundles = tmp_path / "bundles"
    out_bundles.mkdir(parents=True)
    res_dry = publish_bundle(
        PublishRequest(
            manuscript_path=manuscript,
            title="Collision Test",
            license="CC0-1.0",
            unsigned=True,
            out_dir=out_bundles,
            dry_run=True,
        )
    )
    conflict_dir = out_bundles / res_dry.manifest_pid.hex()
    conflict_dir.mkdir()
    (conflict_dir / "text.md").write_bytes(b"Differing content\n")

    with pytest.raises(AethelError) as exc:
        publish_bundle(req)
    assert exc.value.code == "ID_MISMATCH"


@pytest.mark.req("UR-09")
def test_publish_assets_and_case_collision(tmp_path: Path) -> None:
    manuscript = tmp_path / "assets_doc.md"
    manuscript.write_bytes(b"Assets doc.\n")

    fig1 = tmp_path / "figure1.svg"
    fig1.write_bytes(b"<svg></svg>\n")
    data_csv = tmp_path / "table.csv"
    data_csv.write_bytes(b"a,b\n1,2\n")

    req = PublishRequest(
        manuscript_path=manuscript,
        title="Assets Document",
        license="CC-BY-4.0",
        unsigned=True,
        assets=[
            AssetInput(path=fig1, name="figure1.svg"),
            AssetInput(path=data_csv, name="table.csv"),
        ],
        out_dir=tmp_path / "bundles",
    )

    res = publish_bundle(req)
    assert res.bundle_path is not None
    assert (res.bundle_path / "assets" / "figure1.svg").exists()
    assert (res.bundle_path / "assets" / "table.csv").exists()

    report = verify_bundle(res.bundle_path)
    assert report.integrity == "PASS"
    assert report.checks_dict()["V3"] == "PASS"

    # Collision test: figure1.svg and FIGURE1.SVG
    req_collision = PublishRequest(
        manuscript_path=manuscript,
        title="Assets Document",
        license="CC-BY-4.0",
        unsigned=True,
        assets=[
            AssetInput(path=fig1, name="figure1.svg"),
            AssetInput(path=data_csv, name="FIGURE1.SVG"),
        ],
        out_dir=tmp_path / "bundles_collision",
    )
    with pytest.raises(AethelError) as exc:
        publish_bundle(req_collision)
    assert exc.value.code == "E_NOT_SORTED_OR_UNIQUE"


def test_publish_title_from_heading(tmp_path: Path) -> None:
    manuscript = tmp_path / "heading_doc.md"
    manuscript.write_bytes(b"# Extracted Title\n\nContent paragraph.\n")

    req = PublishRequest(
        manuscript_path=manuscript,
        title_from_heading=True,
        license="CC0-1.0",
        unsigned=True,
        out_dir=tmp_path / "bundles",
    )

    res = publish_bundle(req)
    assert res.manifest.title == "Extracted Title"


def test_revise_bundle_with_parents(tmp_path: Path) -> None:
    # 1. Publish genesis bundle
    genesis_doc = tmp_path / "genesis.md"
    genesis_doc.write_bytes(b"# Genesis Edition\n\nFirst edition text.\n")
    key_path = tmp_path / "key.aek"
    create_key("ml-dsa-87", key_path)

    sk = load_key(key_path)

    gen_req = PublishRequest(
        manuscript_path=genesis_doc,
        title="Genesis Edition",
        license="CC-BY-4.0",
        lang="en",
        keys=[sk],
        out_dir=tmp_path / "bundles",
    )
    gen_res = publish_bundle(gen_req)
    assert gen_res.bundle_path is not None

    # 2. Revise genesis bundle
    revised_doc = tmp_path / "revised.md"
    revised_doc.write_bytes(b"# Second Edition\n\nRevised text content.\n")

    rev_req = PublishRequest(
        manuscript_path=revised_doc,
        title="Second Edition",
        keys=[sk],
        out_dir=tmp_path / "bundles",
    )

    rev_res = revise_bundle(gen_res.bundle_path, rev_req)
    assert rev_res.bundle_path is not None
    assert rev_res.manifest.work_pid == gen_res.manifest_pid
    assert gen_res.manifest_pid in rev_res.manifest.parents

    # Verify revised bundle with parents supplied
    report = verify_bundle(rev_res.bundle_path, parents=tmp_path / "bundles")
    assert report.integrity == "PASS"
    assert report.checks_dict()["V5"] == "PASS"
    assert report.attribution.cls == "Attributed"


def test_publish_dual_family_signatures(tmp_path: Path) -> None:
    manuscript = tmp_path / "dual.md"
    manuscript.write_bytes(b"# Dual Family\n\nDual signed manuscript.\n")

    k1 = tmp_path / "k1.aek"
    k2 = tmp_path / "k2.aek"
    create_key("ml-dsa-87", k1)
    create_key("slh-dsa-shake-256s", k2)

    sk1 = load_key(k1)
    sk2 = load_key(k2)

    req = PublishRequest(
        manuscript_path=manuscript,
        title="Dual Family",
        license="CC0-1.0",
        keys=[sk1, sk2],
        out_dir=tmp_path / "bundles",
    )

    res = publish_bundle(req)
    assert len(res.envelopes) == 2
    assert res.bundle_path is not None

    report = verify_bundle(res.bundle_path)
    assert report.integrity == "PASS"
    assert report.attribution.cls == "Dual-family"


def test_publish_markup_and_heading_edge_cases(tmp_path: Path) -> None:
    doc = tmp_path / "doc.unknown"
    doc.write_bytes(b"No heading here.\n")

    # 1. Unknown extension
    with pytest.raises(AethelError) as exc:
        publish_bundle(
            PublishRequest(
                manuscript_path=doc,
                title="Title",
                license="MIT",
                unsigned=True,
            )
        )
    assert exc.value.code == "E_BAD_VALUE"

    # 2. Unsupported markup argument
    with pytest.raises(AethelError) as exc:
        publish_bundle(
            PublishRequest(
                manuscript_path=doc,
                title="Title",
                license="MIT",
                markup="unsupported",
                unsigned=True,
            )
        )
    assert exc.value.code == "E_BAD_VALUE"

    # 3. Explicit tex markup
    tex_doc = tmp_path / "paper.tex"
    tex_doc.write_bytes(b"\\section{Intro}\n")
    res_tex = publish_bundle(
        PublishRequest(
            manuscript_path=tex_doc,
            title="Tex Paper",
            license="MIT",
            markup="tex",
            unsigned=True,
            out_dir=tmp_path / "bundles",
        )
    )
    assert res_tex.manifest.markup == "pip-tex-1"

    # 4. Title from heading failure (no heading)
    with pytest.raises(AethelError) as exc:
        publish_bundle(
            PublishRequest(
                manuscript_path=doc,
                title_from_heading=True,
                license="MIT",
                markup="txt",
                unsigned=True,
            )
        )
    assert exc.value.code == "E_BAD_VALUE"


def test_publish_validation_errors(tmp_path: Path) -> None:
    doc = tmp_path / "doc.md"
    doc.write_bytes(b"# Title\n\nText\n")

    # 1. Missing license
    with pytest.raises(AethelError) as exc:
        publish_bundle(
            PublishRequest(
                manuscript_path=doc,
                title="Title",
                license="",
                unsigned=True,
            )
        )
    assert exc.value.code == "E_MISSING_FIELD"

    # 2. Neither key nor unsigned
    with pytest.raises(AethelError) as exc:
        publish_bundle(
            PublishRequest(
                manuscript_path=doc,
                title="Title",
                license="MIT",
                unsigned=False,
                keys=[],
            )
        )
    assert exc.value.code == "NO_SIGNATURES"

    # 3. Manuscript missing
    with pytest.raises(AethelError) as exc:
        publish_bundle(
            PublishRequest(
                manuscript_path=tmp_path / "missing.md",
                title="Title",
                license="MIT",
                unsigned=True,
            )
        )
    assert exc.value.code == "TEXT_MISSING"

    # 4. Manuscript too large
    from aethel_codex.limits import Limits

    with pytest.raises(AethelError) as exc:
        publish_bundle(
            PublishRequest(
                manuscript_path=doc,
                title="Title",
                license="MIT",
                unsigned=True,
                limits=Limits(max_text_bytes=5),
            )
        )
    assert exc.value.code == "LIMIT_EXCEEDED"

    # 5. Asset name invalid
    fig = tmp_path / "fig.png"
    fig.write_bytes(b"png")
    with pytest.raises(AethelError) as exc:
        publish_bundle(
            PublishRequest(
                manuscript_path=doc,
                title="Title",
                license="MIT",
                unsigned=True,
                assets=[AssetInput(path=fig, name="invalid name with spaces.png")],
            )
        )
    assert exc.value.code == "E_BAD_VALUE"

    # 6. Asset missing
    with pytest.raises(AethelError) as exc:
        publish_bundle(
            PublishRequest(
                manuscript_path=doc,
                title="Title",
                license="MIT",
                unsigned=True,
                assets=[AssetInput(path=tmp_path / "nonexistent.png", name="fig.png")],
            )
        )
    assert exc.value.code == "ASSET_MISSING"

    # 7. Manifest limit exceeded
    with pytest.raises(AethelError) as exc:
        publish_bundle(
            PublishRequest(
                manuscript_path=doc,
                title="Title",
                license="MIT",
                unsigned=True,
                limits=Limits(max_manifest_bytes=10),
            )
        )
    assert exc.value.code == "LIMIT_EXCEEDED"


def test_publish_beacon_cites_derivatives(tmp_path: Path) -> None:
    doc = tmp_path / "doc.md"
    doc.write_bytes(b"# Complex Doc\n\nBody text.\n")

    cite_pid = "pip1:t:" + "01" * 32
    deriv_pid = "pip1:m:" + "02" * 32

    res = publish_bundle(
        PublishRequest(
            manuscript_path=doc,
            title="Complex Doc",
            license="MIT",
            unsigned=True,
            beacon=("nist-beacon", 100, b"\x00" * 32),
            cites=[cite_pid],
            derivatives=[("translation", deriv_pid)],
            out_dir=tmp_path / "bundles",
        )
    )
    assert res.manifest.beacon is not None
    assert res.manifest.beacon.source == "nist-beacon"
    assert len(res.manifest.cites) == 1
    assert len(res.manifest.derivatives) == 1


def test_revise_keep_assets_and_cites(tmp_path: Path) -> None:
    # 1. Parent missing
    with pytest.raises(AethelError) as exc:
        revise_bundle(tmp_path / "nonexistent_parent", PublishRequest(manuscript_path=tmp_path))
    assert exc.value.code == "MANIFEST_MISSING"

    # 2. Parent with asset and cite
    doc = tmp_path / "p1.md"
    doc.write_bytes(b"# Version 1\n\nText 1.\n")
    asset_file = tmp_path / "data.json"
    asset_file.write_bytes(b'{"key": "value"}')

    cite_pid = "pip1:m:" + "33" * 32

    p1_res = publish_bundle(
        PublishRequest(
            manuscript_path=doc,
            title="Version 1",
            license="MIT",
            unsigned=True,
            assets=[AssetInput(path=asset_file, name="data.json", media_type="application/json")],
            cites=[cite_pid],
            out_dir=tmp_path / "bundles",
        )
    )
    assert p1_res.bundle_path is not None

    # Revise with keep_assets and keep_cites
    doc2 = tmp_path / "p2.md"
    doc2.write_bytes(b"# Version 2\n\nText 2.\n")

    p2_res = revise_bundle(
        p1_res.bundle_path,
        PublishRequest(
            manuscript_path=doc2,
            unsigned=True,
            out_dir=tmp_path / "bundles",
        ),
        keep_assets=True,
        keep_cites=True,
    )
    assert p2_res.bundle_path is not None
    assert len(p2_res.manifest.assets) == 1
    assert p2_res.manifest.assets[0].name == "data.json"
    assert p2_res.manifest.assets[0].media_type == "application/json"
    assert len(p2_res.manifest.cites) == 1
    assert str(p2_res.manifest.cites[0]) == cite_pid


def test_publish_atomic_cleanup_and_self_verify_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import aethel_codex.publish
    from aethel_codex.report import AttributionReport, CheckResult, VerifyReport

    doc = tmp_path / "doc.md"
    doc.write_bytes(b"# Doc\n\nText\n")

    # Simulate verify failure
    def mock_verify(*args: object, **kwargs: object) -> VerifyReport:
        return VerifyReport(
            bundle_path=str(tmp_path),
            manifest_id="pip1:m:" + "00" * 32,
            work_id="pip1:m:" + "00" * 32,
            integrity="FAIL",
            attribution=AttributionReport("Unattributed", 0, 0, False),
            history={"status": "SKIPPED"},
            time={"status": "SKIPPED"},
            checks=[CheckResult("V1", "FAIL", "MANIFEST_INVALID")],
        )

    monkeypatch.setattr(aethel_codex.publish, "verify_bundle", mock_verify)

    with pytest.raises(InternalError):
        publish_bundle(
            PublishRequest(
                manuscript_path=doc,
                title="Doc",
                license="MIT",
                unsigned=True,
                out_dir=tmp_path / "bundles_fail",
            )
        )
    monkeypatch.undo()


def test_publish_deep_edge_cases(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from aethel_codex.publish import _atomic_write_bundle, _compare_directory_contents

    # 1. _compare_directory_contents with non-dir
    f = tmp_path / "a_file"
    f.write_text("hello")
    assert not _compare_directory_contents(f, {})

    # 2. _compare_directory_contents with unreadable file
    d = tmp_path / "test_dir"
    d.mkdir()
    (d / "sub.txt").write_bytes(b"content")

    def mock_read_bytes(self: Path) -> bytes:
        raise OSError("Read failed")

    monkeypatch.setattr(Path, "read_bytes", mock_read_bytes)
    assert not _compare_directory_contents(d, {"sub.txt": b"content"})
    monkeypatch.undo()

    # 3. _atomic_write_bundle exception cleanup
    target = tmp_path / "atomic_target"

    def mock_open(*args: object, **kwargs: object) -> object:
        raise OSError("Disk failure during write")

    monkeypatch.setattr("builtins.open", mock_open)
    with pytest.raises(OSError, match="Disk failure during write"):
        _atomic_write_bundle(target, {"file.txt": b"data"})
    monkeypatch.undo()

    # 4. Explicit txt markup
    txt_doc = tmp_path / "paper2.txt"
    txt_doc.write_bytes(b"text\n")
    res_txt = publish_bundle(
        PublishRequest(
            manuscript_path=txt_doc,
            title="Txt Paper",
            license="MIT",
            markup="txt",
            unsigned=True,
            out_dir=tmp_path / "bundles",
        )
    )
    assert res_txt.manifest.markup == "pip-txt-1"

    # 5. Revise keep_assets when asset file is missing on disk
    doc1 = tmp_path / "m1.md"
    doc1.write_bytes(b"# V1\n\nText\n")
    ass = tmp_path / "ass.png"
    ass.write_bytes(b"png")
    p1 = publish_bundle(
        PublishRequest(
            manuscript_path=doc1,
            license="MIT",
            unsigned=True,
            assets=[AssetInput(path=ass, name="ass.png")],
            out_dir=tmp_path / "b_miss",
        )
    )
    assert p1.bundle_path is not None
    # Remove the asset file from parent bundle
    (p1.bundle_path / "assets" / "ass.png").unlink()

    # Revise with keep_assets skips missing file
    doc2 = tmp_path / "m2.md"
    doc2.write_bytes(b"# V2\n\nText\n")
    p2 = revise_bundle(
        p1.bundle_path,
        PublishRequest(
            manuscript_path=doc2,
            unsigned=True,
            out_dir=tmp_path / "b_miss",
        ),
        keep_assets=True,
    )
    assert len(p2.manifest.assets) == 0
