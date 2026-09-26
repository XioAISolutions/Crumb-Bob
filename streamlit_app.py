"""CrumbBob live demo — Streamlit app.

Interactive demo of CrumbBob: generate a memory pack from a real IBM Bob session
report, verify its tamper-evident proof chain, browse multi-session intelligence,
and inspect the Bob handoff artifacts. Runs fully offline from bundled assets.

Deploy target: Streamlit Community Cloud from this repo (main file: streamlit_app.py).
"""
import hashlib
import io
import json
import os
import sqlite3
import sys
import tempfile
import zipfile
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from crumdbob.packer import write_pack_from_directory  # noqa: E402

ASSETS = ROOT / "streamlit_assets"
SAMPLE_REPORT = ASSETS / "sample_bob_report.md"
DEMO_DB = ASSETS / "crumbbob-demo.db"
DEMO_PACK = ASSETS / "demo_pack"

PACK_FILES = [
    "00_repo_genome.crumb",
    "01_session_flight_recorder.crumb",
    "02_next_task.crumb",
    "03_test_plan.crumb",
    "04_risk_register.crumb",
    "05_agent_passport.crumb",
    "06_replay_prompt.md",
    "07_pr_summary.md",
    "08_proof_chain.json",
]

FILE_LABELS = {
    "00_repo_genome.crumb": "🧬 Repo Genome",
    "01_session_flight_recorder.crumb": "📼 Session Flight Recorder",
    "02_next_task.crumb": "📋 Next Task",
    "03_test_plan.crumb": "🧪 Test Plan",
    "04_risk_register.crumb": "⚠️ Risk Register",
    "05_agent_passport.crumb": "🎫 Agent Passport",
    "06_replay_prompt.md": "⏯️ Replay Prompt",
    "07_pr_summary.md": "📝 PR Summary",
    "08_proof_chain.json": "🔗 Proof Chain",
}


# --------------------------------------------------------------------------- #
# Helpers (import-safe: no Streamlit calls here so they are unit-testable)
# --------------------------------------------------------------------------- #
def generate_pack(report_text: str, base_dir: str) -> str:
    """Write the report into base_dir/input/ and run the real CrumbBob packer.

    Returns the pack directory (== base_dir).
    """
    input_dir = os.path.join(base_dir, "input")
    os.makedirs(input_dir, exist_ok=True)
    with open(os.path.join(input_dir, "bob-report.md"), "w", encoding="utf-8") as fh:
        fh.write(report_text)
    write_pack_from_directory(input_dir, base_dir)
    return base_dir


def verify_pack(pack_dir: str) -> tuple[list[dict], dict]:
    """Recompute size + SHA-256 for every file in the proof chain.

    Returns (rows, proof_chain_dict); each row: file, bytes_ok, sha_ok, ok, path.
    """
    pc_path = os.path.join(pack_dir, "08_proof_chain.json")
    with open(pc_path, encoding="utf-8") as fh:
        pc = json.load(fh)
    rows = []
    for item in pc.get("generated_files", []):
        p = os.path.join(pack_dir, item["path"])
        if os.path.exists(p):
            data = open(p, "rb").read()
        else:
            data = b""
        bytes_ok = len(data) == item.get("bytes")
        sha_ok = hashlib.sha256(data).hexdigest() == item.get("sha256")
        rows.append(
            {
                "file": item["path"],
                "expected_bytes": item.get("bytes"),
                "bytes_ok": bytes_ok,
                "sha256_ok": sha_ok,
                "ok": bool(bytes_ok and sha_ok),
            }
        )
    return rows, pc


def tamper_rows(pack_dir: str) -> list[dict]:
    """Copy the pack, flip one byte inside 00_repo_genome.crumb, re-verify.

    Demonstrates that the proof chain detects modification.
    """
    import shutil

    tmp = tempfile.mkdtemp(prefix="crumbbob_tamper_")
    shutil.copytree(pack_dir, tmp, dirs_exist_ok=True)
    target = os.path.join(tmp, "00_repo_genome.crumb")
    if os.path.exists(target):
        data = bytearray(open(target, "rb").read())
        if data:
            data[len(data) // 2] ^= 0x01  # flip one bit
            open(target, "wb").write(bytes(data))
    rows, _ = verify_pack(tmp)
    return rows


def db_introspect(db_path: str) -> list[dict]:
    """All user tables in the demo DB with row counts + column names."""
    out = []
    if not os.path.exists(db_path):
        return out
    con = sqlite3.connect(db_path)
    try:
        names = [
            r[0]
            for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        for name in names:
            count = con.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
            cols = [r[1] for r in con.execute(f'PRAGMA table_info("{name}")')]
            out.append({"table": name, "rows": count, "columns": cols})
    finally:
        con.close()
    return out


def db_preview(db_path: str, table: str, limit: int = 8) -> list[dict]:
    con = sqlite3.connect(db_path)
    try:
        cur = con.execute(f'SELECT * FROM "{table}" LIMIT {int(limit)}')
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        con.close()


def zip_pack(pack_dir: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in sorted(os.listdir(pack_dir)):
            if name == "input":
                continue
            p = os.path.join(pack_dir, name)
            if os.path.isfile(p):
                zf.write(p, arcname=name)
    return buf.getvalue()


def read_text(path: str) -> str:
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


# --------------------------------------------------------------------------- #
# UI
# --------------------------------------------------------------------------- #
st.set_page_config(
    page_title="CrumbBob — Flight Recorder for IBM Bob",
    page_icon="🧠",
    layout="wide",
)

st.sidebar.title("🧠 CrumbBob")
st.sidebar.caption("The flight recorder for IBM Bob development sessions.")
page = st.sidebar.radio(
    "Demo sections",
    [
        "Overview",
        "① Generate a Memory Pack",
        "② Verify the Proof Chain",
        "③ Multi-Session Intelligence",
        "④ Bob Handoff",
    ],
)
st.sidebar.divider()
st.sidebar.markdown(
    "**Bundled demo** — all data shipped in-repo, runs offline.\n\n"
    "[GitHub repo](https://github.com/XioAISolutions/Crumb-Bob)"
)

if page == "Overview":
    st.title("🧠 CrumbBob")
    st.subheader("IBM Bob gives software a temporary brain. CrumbBob gives that brain permanent memory.")
    st.markdown(
        """
CrumbBob converts an exported **IBM Bob session report** into a portable,
tamper-evident **memory pack** — so the next developer (or AI agent) continues
from everything the previous session learned, without re-reading the whole repo.
        """
    )
    st.code(
        "Bob session report  +  repo artifacts  +  test output  +  git diff\n"
        "                              ↓   CrumbBob\n"
        "🧬 Repo Genome   📼 Flight Recorder   📋 Next Task   🧪 Test Plan\n"
        "⚠️ Risk Register   🎫 Agent Passport   ⏯️ Replay Prompt   📝 PR Summary\n"
        "🔗 Proof Chain (SHA-256, tamper-evident)",
        language="text",
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("Pack files", "9")
    c2.metric("Proof chain", "SHA-256")
    c3.metric("Manual collection time", "~30 s")
    st.markdown(
        """
**Why it matters**

- **Onboarding** — a repo genome + session recorder rebuild context in seconds.
- **Handoffs** — the replay prompt + PR summary carry state between people and agents.
- **Auditability** — every pack is hash-verified; nothing unverified gets trusted.
- **Bob 2.0 workflows** — designed for multi-agent sessions: one pack per session,
  chained into a permanent memory of the whole effort.
        """
    )
    st.info("Start with **① Generate a Memory Pack** in the sidebar — it runs the real pipeline on a real report.")

elif page == "① Generate a Memory Pack":
    st.title("① Generate a Memory Pack")
    st.markdown(
        "Below is a **real IBM Bob session report** (bundled sample: a compliance-AI repo hardening session). "
        "Edit it if you like, then run the same packer the CLI uses."
    )
    if not SAMPLE_REPORT.exists():
        st.error("Bundled sample report missing (streamlit_assets/sample_bob_report.md).")
    else:
        report_text = st.text_area(
            "Bob session report (bob-report.md)",
            read_text(SAMPLE_REPORT),
            height=280,
        )
        if st.button("▶ Run CrumbBob on this report", type="primary"):
            try:
                tmp = tempfile.mkdtemp(prefix="crumbbob_demo_")
                pack_dir = generate_pack(report_text, tmp)
                st.session_state["pack_dir"] = pack_dir
                st.success(f"Pack generated at {pack_dir}")
            except Exception as exc:  # noqa: BLE001 - show honest failure in UI
                st.error(f"Pack generation failed: {exc}")
        pack_dir = st.session_state.get("pack_dir")
        if pack_dir and os.path.isdir(pack_dir):
            files = [f for f in PACK_FILES if os.path.exists(os.path.join(pack_dir, f))]
            st.markdown(f"**{len(files)} files generated** — every one is part of the memory pack:")
            tabs = st.tabs([FILE_LABELS.get(f, f) for f in files])
            for tab, fname in zip(tabs, files):
                with tab:
                    st.code(read_text(os.path.join(pack_dir, fname))[:20000], language="markdown" if fname.endswith(".md") else "text")
            st.download_button(
                "⬇️ Download pack (.zip)",
                data=zip_pack(pack_dir),
                file_name="crumbbob_pack.zip",
                mime="application/zip",
            )
        elif DEMO_PACK.exists():
            st.caption("No pack generated in this session yet — showing the bundled reference pack instead.")

elif page == "② Verify the Proof Chain":
    st.title("② Verify the Proof Chain")
    st.markdown(
        "Every pack ships an `08_proof_chain.json` recording **byte size and SHA-256 for each file**. "
        "Verify recomputes both hashes live — then try the built-in tamper simulation."
    )
    pack_dir = st.session_state.get("pack_dir")
    source = pack_dir if (pack_dir and os.path.isdir(pack_dir)) else str(DEMO_PACK)
    if st.button("🔍 Verify this pack", type="primary"):
        try:
            rows, pc = verify_pack(source)
            st.session_state["verify_rows"] = rows
            st.session_state["verify_pc"] = pc
        except Exception as exc:  # noqa: BLE001
            st.error(f"Verification failed: {exc}")
    if "verify_rows" in st.session_state:
        rows = st.session_state["verify_rows"]
        pc = st.session_state.get("verify_pc", {})
        all_ok = all(r["ok"] for r in rows)
        (st.success if all_ok else st.error)(
            f"Proof chain: {'VERIFIED ✓' if all_ok else 'FAILED ✗'} — "
            f"{sum(r['ok'] for r in rows)}/{len(rows)} files match their recorded hashes."
        )
        st.json(
            {
                "crumdbob_version": pc.get("crumdbob_version"),
                "extracted_counts": pc.get("extracted_counts"),
            },
            expanded=False,
        )
        st.dataframe(
            [
                {
                    "file": r["file"],
                    "bytes_ok": r["bytes_ok"],
                    "sha256_ok": r["sha256_ok"],
                    "status": "✓" if r["ok"] else "✗",
                }
                for r in rows
            ],
            use_container_width=True,
        )
        if st.checkbox("🧪 Simulate tampering (flip one bit of 00_repo_genome.crumb, then re-verify)"):
            try:
                trows = tamper_rows(source)
                bad = [r["file"] for r in trows if not r["ok"]]
                if bad:
                    st.error(f"Tampering detected ✗ — modified file(s): {', '.join(bad)}. The chain catches it.")
                else:
                    st.warning("No difference detected (unexpected — please file an issue).")
            except Exception as exc:  # noqa: BLE001
                st.error(f"Tamper check failed: {exc}")

elif page == "③ Multi-Session Intelligence":
    st.title("③ Multi-Session Intelligence")
    st.markdown(
        "Packs also feed a local **SQLite memory database** (`crumdbob record <pack> --db memory.db`). "
        "Across sessions it answers: *what keeps breaking, what keeps recurring, what happened last time.*"
    )
    if not DEMO_DB.exists():
        st.error("Bundled demo DB missing (streamlit_assets/crumbbob-demo.db).")
    else:
        info = db_introspect(str(DEMO_DB))
        st.subheader("Database contents")
        st.dataframe(
            [{"table": i["table"], "rows": i["rows"]} for i in info],
            use_container_width=True,
        )
        for table in ("sessions", "risks", "tasks"):
            if any(i["table"] == table for i in info) and any(i["table"] == table and i["rows"] > 0 for i in info):
                with st.expander(f"🔎 {table}", expanded=(table == "sessions")):
                    try:
                        st.dataframe(db_preview(str(DEMO_DB), table), use_container_width=True)
                    except Exception as exc:  # noqa: BLE001
                        st.warning(f"Could not read {table}: {exc}")
        st.info(
            "This is the persistence layer judges can extend: record dozens of sessions and the "
            "CLI adds trends, insights, patterns and predictions on top (`crumdbob trends`, `insights`, `patterns`)."
        )

elif page == "④ Bob Handoff":
    st.title("④ Bob Handoff — continuing a session")
    st.markdown(
        "The pack's **replay prompt** is what the next Bob session starts from. "
        "Paste it into Bob (or hand it to a teammate) and the session resumes with full context."
    )
    prompt_path = os.path.join(str(DEMO_PACK), "06_replay_prompt.md")
    if os.path.exists(prompt_path):
        st.code(read_text(prompt_path)[:8000], language="markdown")
    pr_path = os.path.join(str(DEMO_PACK), "07_pr_summary.md")
    if os.path.exists(pr_path):
        with st.expander("📝 PR summary (what a handoff PR description looks like)"):
            st.code(read_text(pr_path)[:6000], language="markdown")
    st.markdown(
        """
**Bob 2.0 multi-agent workflows:** each session — the main agent or a subagent —
exports its report, and CrumbBob preserves them as a chain. Nothing learned in
a branch of the agent tree gets lost when that context closes.
        """
    )

st.divider()
st.caption("CrumbBob · built for the IBM Bob 2.0 hackathon · MIT licensed · proof chains by SHA-256")
