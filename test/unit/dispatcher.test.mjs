import { test } from 'node:test';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dispatch, eventFromArgs } from '../../plugins/agnthive/modules/hook-dispatcher.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const dispatcher = join(here, '..', '..', 'plugins', 'agnthive', 'modules', 'hook-dispatcher.mjs');

// Tests must never write into the user's real ~/.claude plugin data dir, so
// point CLAUDE_PLUGIN_DATA at a temp dir for both in-process dispatch and the
// spawned end-to-end runs.
let dataRoot;
test.before(() => {
  dataRoot = mkdtempSync(join(tmpdir(), 'disp-'));
  process.env.CLAUDE_PLUGIN_DATA = dataRoot;
});
test.after(() => {
  delete process.env.CLAUDE_PLUGIN_DATA;
  rmSync(dataRoot, { recursive: true, force: true });
});

const parsed = { ok: true, empty: false, error: null, data: {}, event: 'Stop', toolName: null, toolInput: {}, sessionId: 's', cwd: null, transcriptPath: null };

// Stop / UserPromptSubmit / PreToolUse / PostToolUse all return passthrough
// against a fresh (no-code-change) session. SubagentStop is no longer inert:
// with no assistant message it blocks (see the contract test below).
test('dispatch: stateless events return passthrough against a fresh session', () => {
  for (const ev of ['Stop', 'UserPromptSubmit', 'PreToolUse', 'PostToolUse']) {
    assert.deepEqual(dispatch(ev, parsed), {}, `${ev} should be passthrough`);
  }
});

// SubagentStop footer enforcement is now scoped to AgntHive specialist roles
// (ADR 0001). The shared `parsed` carries no recognized role, so a fresh
// `data: {}` payload passes through; this test seeds a recognized agent_alias
// ('cr') so the no-message block still fires.
test('dispatch: SubagentStop blocks when no assistant summary is present', () => {
  const out = dispatch('SubagentStop', { ...parsed, data: { agent_alias: 'cr' } });
  assert.equal(out.decision, 'block');
  assert.match(out.reason, /No assistant summary message was found/);
});

// --- ADR 0001: SubagentStop footer scope -------------------------------
// Recognized AgntHive specialists are footer-enforced; generic dispatch types
// and unidentified subagents pass through so structured output is not corrupted.

test('dispatch: SubagentStop with agent_alias cr + incomplete footer -> block', () => {
  const out = dispatch('SubagentStop', { ...parsed, data: { agent_alias: 'cr', last_assistant_message: 'Outcome: fixed the bug' } });
  assert.equal(out.decision, 'block');
  assert.match(out.reason, /Changed files:/);
});

test('dispatch: SubagentStop with agent_type general-purpose -> passthrough', () => {
  const out = dispatch('SubagentStop', { ...parsed, data: { agent_type: 'general-purpose', last_assistant_message: 'irrelevant structured output' } });
  assert.deepEqual(out, {});
});

test('dispatch: SubagentStop with no agent_type -> passthrough', () => {
  const out = dispatch('SubagentStop', { ...parsed, data: { last_assistant_message: 'unidentified subagent output' } });
  assert.deepEqual(out, {});
});

test('dispatch: SubagentStop with agent_type workflow-subagent -> passthrough', () => {
  const out = dispatch('SubagentStop', { ...parsed, data: { agent_type: 'workflow-subagent' } });
  assert.deepEqual(out, {});
});

// ADR-0004 (narrowed namespace strip): an agnthive: namespace prefix must be
// stripped so a plugin-namespaced specialist is still footer-enforced. Guards
// the order-of-operations regression: a too-broad colon strip would also
// misrecognize foreign namespaces (mcp:tester) as specialists.
test('dispatch: SubagentStop with agent_type agnthive:Code Reviewer + incomplete footer -> block', () => {
  const out = dispatch('SubagentStop', { ...parsed, data: { agent_type: 'agnthive:Code Reviewer', last_assistant_message: 'Outcome: fixed the bug' } });
  assert.equal(out.decision, 'block');
  assert.match(out.reason, /Changed files:/);
});

// ADR-0004 over-match guard at the dispatcher level: a foreign namespace
// (mcp:tester) is NOT stripped to 'tester', so it is not recognized as a
// specialist and passes through without footer enforcement.
test('dispatch: SubagentStop with agent_type mcp:tester -> passthrough (foreign namespace)', () => {
  const out = dispatch('SubagentStop', { ...parsed, data: { agent_type: 'mcp:tester', last_assistant_message: 'structured output, no footer' } });
  assert.deepEqual(out, {});
});

// --- ADR 0003: stop_hook_active yields the Stop hook ------------------

// Seed code_changed:true for a session by dispatching an EditWrite PostToolUse,
// then exercise the stop_hook_active short-circuit against that state.
function seedCodeChanged(sessionId) {
  dispatch('PostToolUse', { ...parsed, sessionId, toolInput: { file_path: '/tmp/src/app.js' } }, 'EditWrite');
}

// ADR-0003 hardening: stop_hook_active on a FIRST Stop invocation (no prior
// block this session) must NOT silently disable enforcement. A conformant
// runtime sets stop_hook_active only on a re-invocation after our own block,
// so a prior block is always present then; a runtime that erroneously sets it
// on the first call falls through to normal blocking instead of yielding.
test('dispatch: Stop with stopHookActive true but NO prior block -> block (not a blind yield)', () => {
  const sid = 'stop-hook-active-no-prior';
  seedCodeChanged(sid);
  // code_changed is true, no stop_block_count, no stalled_by_policy.
  const out = dispatch('Stop', { ...parsed, sessionId: sid, stopHookActive: true, data: {} });
  assert.equal(out.decision, 'block', 'a first-invocation stop_hook_active must not skip enforcement');
});

// The yield path: stop_hook_active is honored when there IS evidence of a prior
// block (a non-zero stop_block_count). Seed one block, then a re-invocation with
// stop_hook_active yields (clears loop state and passes through).
test('dispatch: Stop with stopHookActive true + prior stop_block_count -> passthrough', () => {
  const sid = 'stop-hook-active-prior-block';
  seedCodeChanged(sid);
  const missing = { ...parsed, sessionId: sid, data: { last_assistant_message: 'No changes were made.' } };
  // One prior block raises stop_block_count to 1 (not a terminal stall).
  const blocked = dispatch('Stop', missing);
  assert.equal(blocked.decision, 'block');
  // The re-invocation with stop_hook_active yields because a prior block exists.
  const out = dispatch('Stop', { ...parsed, sessionId: sid, stopHookActive: true, data: {} });
  assert.deepEqual(out, {}); // passthrough
});

test('dispatch: Stop without stopHookActive + code_changed + missing footer -> block', () => {
  const sid = 'stop-no-hook-active';
  seedCodeChanged(sid);
  const out = dispatch('Stop', { ...parsed, sessionId: sid, data: { last_assistant_message: 'No changes were made.' } });
  assert.equal(out.decision, 'block');
});

// ADR-0003 order-of-operations: stop_hook_active is checked BEFORE the
// policy-stall repeat. A session that already hit a terminal policy-stall
// (stalled_by_policy true) must still yield — not repeat the terminal cancel —
// when the runtime re-invokes Stop with stop_hook_active.
test('dispatch: Stop with stopHookActive true yields even when stalled_by_policy is true', () => {
  const sid = 'stop-hook-active-stalled';
  seedCodeChanged(sid);
  const missing = { ...parsed, sessionId: sid, data: { last_assistant_message: 'No changes were made.' } };
  // Drive the stop loop to a terminal policy-stall: 3x same block -> hardStop.
  dispatch('Stop', missing); // count 1
  dispatch('Stop', missing); // count 2
  const terminal = dispatch('Stop', missing); // count 3 -> hardStop, stalled_by_policy
  assert.equal(terminal.continue, false);
  assert.equal(terminal.hardStop, true);
  // A re-invocation with stop_hook_active must yield, not repeat the cancel.
  const out = dispatch('Stop', { ...parsed, sessionId: sid, stopHookActive: true, data: {} });
  assert.deepEqual(out, {}); // passthrough
  // And it clears the stop loop state as a side effect.
  const probe = dispatch('Stop', { ...parsed, sessionId: sid, data: { last_assistant_message: 'No changes were made.' } });
  assert.equal(probe.decision, 'block'); // count reset to 1, not a terminal repeat
  assert.notEqual(probe.continue, false);
});

test('dispatch: unknown event degrades to passthrough (never blocks)', () => {
  assert.deepEqual(dispatch('NotARealEvent', parsed), {});
});

test('dispatch: a handler crash never blocks the runtime', () => {
  // Simulated by dispatching an unknown event (no handler) — already passthrough.
  // A throwing handler is covered by the crash path inside dispatch, which also
  // returns passthrough; assert the contract holds for the unknown path.
  const out = dispatch('UnknownEvent', parsed);
  assert.equal('decision' in out, false);
  assert.equal('continue' in out, false);
});

test('eventFromArgs: reads --event, returns null when absent', () => {
  assert.equal(eventFromArgs(['--event', 'Stop']), 'Stop');
  assert.equal(eventFromArgs(['--event', 'PreToolUse', '--other', 'x']), 'PreToolUse');
  assert.equal(eventFromArgs([]), null);
  assert.equal(eventFromArgs(['--event']), null); // missing value
});

function runDispatcher(args, input) {
  return spawnSync(process.execPath, [dispatcher, ...args], {
    input, encoding: 'utf8', timeout: 10000,
    env: { ...process.env, CLAUDE_PLUGIN_DATA: dataRoot },
  });
}

test('end-to-end: valid stdin -> valid JSON stdout, exit 0, clean stderr', () => {
  const r = runDispatcher(['--event', 'Stop'], JSON.stringify({ hook_event_name: 'Stop', session_id: 's1' }));
  assert.equal(r.status, 0, `stderr: ${r.stderr}`);
  assert.deepEqual(JSON.parse(r.stdout), {});
});

test('end-to-end: malformed stdin -> still valid JSON output + stderr warning + exit 0', () => {
  const r = runDispatcher(['--event', 'Stop'], '{ not json');
  assert.equal(r.status, 0);
  JSON.parse(r.stdout); // does not throw
  assert.match(r.stderr, /invalid JSON|input warning/i);
});

test('end-to-end: empty stdin -> valid JSON output, exit 0', () => {
  const r = runDispatcher(['--event', 'Stop'], '');
  assert.equal(r.status, 0);
  JSON.parse(r.stdout);
});

test('end-to-end: no --event and no hook_event_name -> stderr note, still exit 0', () => {
  const r = runDispatcher([], JSON.stringify({ session_id: 's' }));
  assert.equal(r.status, 0);
  JSON.parse(r.stdout);
  assert.match(r.stderr, /no event/i);
});

test('end-to-end: arbitrary Unicode in stdin survives', () => {
  const input = JSON.stringify({ hook_event_name: 'UserPromptSubmit', prompt: 'naïve façade ☃ 日本語' });
  const r = runDispatcher(['--event', 'UserPromptSubmit'], input);
  assert.equal(r.status, 0);
  JSON.parse(r.stdout);
});