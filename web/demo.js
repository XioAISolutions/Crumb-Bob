const sampleReport = `# IBM Bob Report: XIO Compliance Brain

Bob analyzed a Canadian compliance review system with document intake, reviewer personas, citation verification, approval gating, audit trails, and DOCX export.

## Architecture map

- apps/web/src/app/matters/new handles the wizard and task selection flow.
- packages/agents contains task-specific reviewer personas.
- packages/cognition contains source locker metadata and citation verification.
- packages/approvals contains the hash-bound approval state machine.

## Command surface

- pnpm test
- pnpm -r typecheck
- pnpm --filter @compliance-ai/web build

## Risks and gaps

- Risk: judges may misunderstand the product as generic RAG unless citation verification is foregrounded.
- Risk: local setup may feel heavy if the first-run path requires database/auth configuration.
- Gap: add a replay prompt so another AI agent can continue from prior repo analysis.

## Recommended next tasks

- Add Repo Genome to preserve this analysis.
- Add Proof Chain so generated output is hash-bound to the Bob report.
- Add PR Summary for GitHub review.`;

const reportInput = document.querySelector("#bob-report");
const status = document.querySelector("#status");
const outputIds = ["repo-genome", "flight-recorder", "risk-register", "replay-prompt"];

function lines(text) {
  return text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
}

function bullets(text) {
  return lines(text)
    .filter((line) => /^[-*+]\s+/.test(line))
    .map((line) => line.replace(/^[-*+]\s+/, ""));
}

function titleFrom(text) {
  return lines(text).find((line) => line.startsWith("# "))?.replace(/^#\s+/, "") || "IBM Bob Session";
}

function commandLines(items) {
  return items.filter((item) => /\b(pnpm|npm|python|pytest|git|node)\s+/.test(item));
}

function fileLines(items) {
  return items.filter((item) => /[A-Za-z0-9_.@-]+\/[A-Za-z0-9_.@/-]+/.test(item));
}

function riskLines(items) {
  return items.filter((item) => /(risk|gap|missing|unclear|manual|todo|blocker)/i.test(item));
}

async function sha256(text) {
  const data = new TextEncoder().encode(text);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(digest)).map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

function list(items, fallback) {
  return (items.length ? items : [fallback]).map((item) => `- ${item}`).join("\n");
}

async function buildPack(text) {
  const extracted = bullets(text);
  const title = titleFrom(text);
  const files = fileLines(extracted);
  const commands = commandLines(extracted);
  const risks = riskLines(extracted);
  const hash = await sha256(text);
  const shortHash = hash.slice(0, 16);

  return {
    genome: `BEGIN CRUMB
v=1.4
kind=map
title=Repo Genome: ${title}
source=ibm-bob
id=repo-genome
refs=session-flight-recorder,next-task,test-plan,risk-register,agent-passport
---
[project]
${lines(text).find((line) => !line.startsWith("#") && !line.startsWith("-")) || "Bob analyzed the repository and produced reusable development context."}

[modules]
${list(files, "No file paths were captured in the pasted report.")}

[commands]
${list(commands, "Run the repo's documented test and build commands.")}

[checks]
source-report :: captured
proof-chain :: ${shortHash}

END CRUMB`,
    recorder: `BEGIN CRUMB
v=1.4
kind=audit
title=Session Flight Recorder
source=ibm-bob
id=session-flight-recorder
refs=repo-genome,proof-chain
---
[goal]
Preserve Bob's repository understanding as replayable software memory.

[actions]
- Parsed pasted Bob report.
- Extracted ${files.length} files, ${commands.length} commands, and ${risks.length} risks.
- Prepared replay and proof-chain preview.

[verdict]
Ready to continue from captured context.

[evidence]
- source_sha256=${hash}

END CRUMB`,
    risks: `BEGIN CRUMB
v=1.4
kind=todo
title=Risk Register
source=ibm-bob
id=risk-register
refs=repo-genome,session-flight-recorder
---
[tasks]
${list(risks.map((risk) => `[ ] ${risk}`), "[ ] Validate assumptions Bob could not prove.")}

[checks]
risks-extracted :: ${risks.length}
source-hash :: ${shortHash}

END CRUMB`,
    replay: `# Replay this IBM Bob session

Load the Repo Genome, Session Flight Recorder, Risk Register, and Proof Chain before changing code.

Continue from ${title}. Do not re-discover captured context. Run the extracted commands, address the highest risk, then regenerate the CrumbBob pack.

Proof preview:
- source_sha256=${hash}
- files=${files.length}
- commands=${commands.length}
- risks=${risks.length}`,
    counts: { files: files.length, commands: commands.length, risks: risks.length },
  };
}

async function generate() {
  const text = reportInput.value.trim();
  if (!text) {
    status.textContent = "Paste a Bob report first.";
    status.classList.remove("ready");
    return;
  }
  const pack = await buildPack(text);
  document.querySelector("#repo-genome").textContent = pack.genome;
  document.querySelector("#flight-recorder").textContent = pack.recorder;
  document.querySelector("#risk-register").textContent = pack.risks;
  document.querySelector("#replay-prompt").textContent = pack.replay;
  status.textContent = `Generated demo pack: ${pack.counts.files} files, ${pack.counts.commands} commands, ${pack.counts.risks} risks.`;
  status.classList.add("ready");
}

async function copyOutput(id, button) {
  const text = document.querySelector(`#${id}`).textContent;
  if (!text) return;
  try {
    if (!navigator.clipboard) throw new Error("Clipboard API unavailable");
    await navigator.clipboard.writeText(text);
  } catch {
    const scratch = document.createElement("textarea");
    scratch.value = text;
    scratch.setAttribute("readonly", "");
    scratch.style.position = "fixed";
    scratch.style.left = "-9999px";
    document.body.appendChild(scratch);
    scratch.select();
    document.execCommand("copy");
    scratch.remove();
  }
  const previous = button.textContent;
  button.textContent = "Copied";
  window.setTimeout(() => {
    button.textContent = previous;
  }, 1200);
}

document.querySelector("#load-sample").addEventListener("click", () => {
  reportInput.value = sampleReport;
  generate();
});

document.querySelector("#generate").addEventListener("click", generate);

document.querySelectorAll(".copy").forEach((button) => {
  button.addEventListener("click", () => copyOutput(button.dataset.copy, button));
});

reportInput.value = sampleReport;
generate();
