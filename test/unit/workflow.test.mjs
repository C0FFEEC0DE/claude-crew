import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import {
  classifyPrompt, taskTypeRequiresImplementationSummary,
  taskTypeRequiresSpecialistHandoffs, loopBlockFields, loopBlockCount,
  recordLoopBlock, clearLoopBlockPatch, userPromptResetPatch,
  sessionBackgroundManagerPending, STOP_SAFE_HINT, parseDispatchContractMarker,
  agentLoopKey, hasPriorStopBlock,
} from '../../plugins/agnthive/modules/workflow.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const fixtures = join(here, '..', '..', 'test', 'hooks', 'fixtures');
function loadPrompt(name) {
  return JSON.parse(readFileSync(join(fixtures, `${name}.json`), 'utf8')).prompt;
}

// Fixture -> expected classification. Each row preserves the task type and
// role state the migrated UserPromptSubmit hook must produce.
const EXPECT = [
  ['user_prompt_feature', { taskType: 'feature', managerMode: 'none', docsRequired: true, requiredSubagents: ['t', 'cr'], anyOf: [['e', 'a']], ctx: 'feature workflow' }],
  ['user_prompt_bugfix', { taskType: 'bugfix', managerMode: 'none', docsRequired: true, requiredSubagents: ['t', 'cr'], anyOf: [['bug', 'e', 'dbg']], ctx: 'bugfix workflow' }],
  ['user_prompt_bugfix_ru', { taskType: 'bugfix', managerMode: 'none', docsRequired: true, requiredSubagents: ['t', 'cr'], anyOf: [['bug', 'e', 'dbg']], ctx: 'bugfix workflow' }],
  ['user_prompt_refactor', { taskType: 'refactor', managerMode: 'none', docsRequired: true, requiredSubagents: ['t', 'cr'], anyOf: [['a', 'e']], ctx: 'refactor workflow' }],
  ['user_prompt_review', { taskType: 'review', managerMode: 'none', docsRequired: false, requiredSubagents: ['cr'], anyOf: [], ctx: '@cr' }],
  ['user_prompt_docs', { taskType: 'docs', managerMode: 'none', docsRequired: true, requiredSubagents: ['doc'], anyOf: [], ctx: '@doc' }],
  ['user_prompt_model_question', { taskType: 'other', managerMode: 'none', docsRequired: false, requiredSubagents: [], anyOf: [], ctx: '' }],
  ['user_prompt_models_info', { taskType: 'other', managerMode: 'none', docsRequired: false, requiredSubagents: [], anyOf: [], ctx: '' }],
  ['user_prompt_models_creative_typo_info', { taskType: 'other', managerMode: 'none', docsRequired: false, requiredSubagents: [], anyOf: [], ctx: '' }],
  ['user_prompt_models_compare_repo', { taskType: 'other', managerMode: 'none', docsRequired: false, requiredSubagents: [], anyOf: [], ctx: '' }],
  ['user_prompt_models_feature', { taskType: 'feature', managerMode: 'none', docsRequired: true, requiredSubagents: ['t', 'cr'], anyOf: [['e', 'a']], ctx: 'feature workflow' }],
  ['user_prompt_models_mixed_feature', { taskType: 'feature', managerMode: 'none', docsRequired: true, requiredSubagents: ['t', 'cr'], anyOf: [['e', 'a']], ctx: 'feature workflow' }],
  ['user_prompt_models_manager_plan_only', { taskType: 'feature', managerMode: 'plan_only', docsRequired: true, requiredSubagents: [], anyOf: [], ctx: 'Plan-only' }],
  ['user_prompt_models_review', { taskType: 'review', managerMode: 'none', docsRequired: false, requiredSubagents: ['cr'], anyOf: [], ctx: '@cr' }],
  ['user_prompt_models_docs', { taskType: 'docs', managerMode: 'none', docsRequired: true, requiredSubagents: ['doc'], anyOf: [], ctx: '@doc' }],
  ['user_prompt_tech_support_bug_word', { taskType: 'support', managerMode: 'none', docsRequired: false, requiredSubagents: [], anyOf: [], ctx: 'support workflow' }],
  ['user_prompt_benchmark_refactor_override', { taskType: 'refactor', managerMode: 'none', docsRequired: true, requiredSubagents: ['t', 'cr'], anyOf: [['a', 'e']], ctx: 'refactor workflow' }],
  ['user_prompt_mixed_intent', { taskType: 'bugfix', managerMode: 'none', docsRequired: true, requiredSubagents: ['t', 'cr'], anyOf: [['bug', 'e', 'dbg']], ctx: 'bugfix workflow' }],
  ['user_prompt_hey', { taskType: 'other', managerMode: 'none', docsRequired: false, requiredSubagents: [], anyOf: [], ctx: '' }],
  ['user_prompt_manager_plan_only', { taskType: 'feature', managerMode: 'plan_only', docsRequired: true, requiredSubagents: [], anyOf: [], ctx: 'Plan-only' }],
  ['user_prompt_no_session_id', { taskType: 'feature', managerMode: 'none', docsRequired: true, requiredSubagents: ['t', 'cr'], anyOf: [['e', 'a']], ctx: 'feature workflow' }],
];

for (const [name, exp] of EXPECT) {
  test(`classifyPrompt: ${name} -> ${exp.taskType}/${exp.managerMode}`, () => {
    const r = classifyPrompt(loadPrompt(name));
    assert.equal(r.taskType, exp.taskType, `taskType for ${name}`);
    assert.equal(r.managerMode, exp.managerMode, `managerMode for ${name}`);
    assert.equal(r.docsRequired, exp.docsRequired, `docsRequired for ${name}`);
    assert.deepEqual(r.requiredSubagents, exp.requiredSubagents, `requiredSubagents for ${name}`);
    assert.deepEqual(r.requiredSubagentAnyOf, exp.anyOf, `requiredSubagentAnyOf for ${name}`);
    if (exp.ctx === '') assert.equal(r.contextMessage, '', `contextMessage for ${name} should be empty`);
    else assert.ok(r.contextMessage.includes(exp.ctx), `contextMessage for ${name} should contain "${exp.ctx}", got: ${r.contextMessage}`);
  });
}

test('stop-safe hint appears on non-plan-only gated contexts', () => {
  const r = classifyPrompt(loadPrompt('user_prompt_feature'));
  assert.ok(r.contextMessage.includes(STOP_SAFE_HINT.trim().slice(0, 40)));
});

test('plan-only context omits the stop-safe hint', () => {
  const r = classifyPrompt(loadPrompt('user_prompt_models_manager_plan_only'));
  assert.ok(!r.contextMessage.includes('If a later reply'));
});

test('classifyPrompt: dispatch-contract marker overrides category-default roles', () => {
  const prompt = 'Workflow override: treat this as a bugfix workflow, not a review-only workflow.\n'
    + 'BENCHMARK_DISPATCH_CONTRACT: root_only; mode=observed; roles=bug\n'
    + 'Task: fix the divide-by-zero in calculator.py.';
  const r = classifyPrompt(prompt);
  // Category still classified (for docs/verification gating)...
  assert.equal(r.taskType, 'bugfix');
  // ...but required roles come from the marker only; any-of groups cleared.
  assert.deepEqual(r.requiredSubagents, ['bug']);
  assert.deepEqual(r.requiredSubagentAnyOf, []);
  assert.ok(r.contextMessage.includes('Required specialist handoff before completion: @bug'), r.contextMessage);
  assert.ok(r.contextMessage.includes('do not add category-default'), r.contextMessage);
  // The marker mode is surfaced for persistence to session state.
  assert.equal(r.dispatchContractMode, 'observed');
});

test('classifyPrompt: enforced dispatch-contract mode is surfaced for the hard guard', () => {
  const prompt = 'BENCHMARK_DISPATCH_CONTRACT: root_only; mode=enforced; roles=a\n'
    + 'Use @a to extract the duplicated normalization into a shared helper.';
  const r = classifyPrompt(prompt);
  assert.equal(r.dispatchContractMode, 'enforced');
  assert.deepEqual(r.requiredSubagents, ['a']);
});

test('classifyPrompt: no marker yields empty dispatchContractMode (guard inert)', () => {
  const r = classifyPrompt(loadPrompt('user_prompt_feature'));
  assert.equal(r.dispatchContractMode, '');
});

test('parseDispatchContractMarker parses well-formed markers and rejects malformed ones', () => {
  assert.equal(parseDispatchContractMarker('nothing here'), null);
  assert.equal(parseDispatchContractMarker('BENCHMARK_DISPATCH_CONTRACT: root_only; mode=observed; roles='), null);
  const m = parseDispatchContractMarker('BENCHMARK_DISPATCH_CONTRACT: root_only; mode=enforced; roles=t,cr');
  assert.deepEqual(m, { rootOnly: true, mode: 'enforced', roles: ['t', 'cr'] });
  const m2 = parseDispatchContractMarker('BENCHMARK_DISPATCH_CONTRACT: mode=observed; roles=Bug');
  assert.deepEqual(m2, { rootOnly: false, mode: 'observed', roles: ['bug'] });
});

// --- task type predicates --------------------------------------------------

test('taskTypeRequiresImplementationSummary', () => {
  for (const t of ['feature', 'bugfix', 'refactor', 'review', 'docs']) {
    assert.equal(taskTypeRequiresImplementationSummary(t), true, t);
  }
  for (const t of ['support', 'other', '', 'random']) {
    assert.equal(taskTypeRequiresImplementationSummary(t), false, t);
  }
});

test('taskTypeRequiresSpecialistHandoffs', () => {
  for (const t of ['feature', 'bugfix', 'refactor', 'review', 'docs', 'support']) {
    assert.equal(taskTypeRequiresSpecialistHandoffs(t), true, t);
  }
  for (const t of ['other', '', 'random']) {
    assert.equal(taskTypeRequiresSpecialistHandoffs(t), false, t);
  }
});

// --- loop-block accounting -------------------------------------------------

test('agentLoopKey returns the agent id or the shared _session fallback (ADR 0006)', () => {
  assert.equal(agentLoopKey('agent-a'), 'agent-a');
  assert.equal(agentLoopKey(undefined), '_session');
  assert.equal(agentLoopKey(''), '_session');
  assert.equal(agentLoopKey(null), '_session');
});

test('loopBlockFields maps stop and subagent_stop, rejects others', () => {
  assert.deepEqual(loopBlockFields('stop'), { countKey: 'stop_block_count', reasonKey: 'stop_block_reason', messageKey: 'stop_block_message', perAgent: false });
  assert.deepEqual(loopBlockFields('subagent_stop'), { mapKey: 'subagent_stop_blocks', perAgent: true });
  assert.equal(loopBlockFields('nope'), null);
});

test('recordLoopBlock increments on matching reason+message, resets otherwise', () => {
  const s = { stop_block_count: 2, stop_block_reason: 'r', stop_block_message: 'm' };
  assert.deepEqual(recordLoopBlock(s, 'stop', 'r', 'm'), { stop_block_count: 3, stop_block_reason: 'r', stop_block_message: 'm' });
  assert.deepEqual(recordLoopBlock(s, 'stop', 'r2', 'm'), { stop_block_count: 1, stop_block_reason: 'r2', stop_block_message: 'm' });
  assert.equal(recordLoopBlock(s, 'bad', 'r', 'm'), null);
});

test('recordLoopBlock: subagent_stop is per-agent (increment/reset per agent key)', () => {
  const s = { subagent_stop_blocks: { 'agent-a': { count: 2, reason: 'r', message: 'm' } } };
  // ADR-0005: the per-agent return is { mapKey, key, entry } — the single
  // changed key plus its new entry, no full-map snapshot.
  // same agent, same reason+message -> increment
  assert.deepEqual(recordLoopBlock(s, 'subagent_stop', 'r', 'm', 'agent-a'), {
    mapKey: 'subagent_stop_blocks', key: 'agent-a', entry: { count: 3, reason: 'r', message: 'm' },
  });
  // same agent, new reason -> reset to 1
  assert.deepEqual(recordLoopBlock(s, 'subagent_stop', 'r2', 'm', 'agent-a'), {
    mapKey: 'subagent_stop_blocks', key: 'agent-a', entry: { count: 1, reason: 'r2', message: 'm' },
  });
  // different agent starts at 1 even with the same reason+message as agent-a
  assert.deepEqual(recordLoopBlock(s, 'subagent_stop', 'r', 'm', 'agent-b'), {
    mapKey: 'subagent_stop_blocks', key: 'agent-b', entry: { count: 1, reason: 'r', message: 'm' },
  });
  // absent agent_id falls back to the shared _session key
  assert.deepEqual(recordLoopBlock({}, 'subagent_stop', 'r', 'm'), {
    mapKey: 'subagent_stop_blocks', key: '_session', entry: { count: 1, reason: 'r', message: 'm' },
  });
  assert.equal(recordLoopBlock(s, 'bad', 'r', 'm', 'agent-a'), null);
});

test('loopBlockCount reads defensively', () => {
  assert.equal(loopBlockCount({ stop_block_count: 5 }, 'stop'), 5);
  assert.equal(loopBlockCount({}, 'stop'), 0);
  assert.equal(loopBlockCount({ subagent_stop_blocks: { 'agent-a': { count: 3 } } }, 'subagent_stop', 'agent-a'), 3);
  // different agent -> 0 (per-agent isolation)
  assert.equal(loopBlockCount({ subagent_stop_blocks: { 'agent-a': { count: 3 } } }, 'subagent_stop', 'agent-b'), 0);
  // absent agent_id falls back to _session
  assert.equal(loopBlockCount({ subagent_stop_blocks: { _session: { count: 2 } } }, 'subagent_stop'), 2);
  assert.equal(loopBlockCount({}, 'subagent_stop', 'agent-a'), 0);
  assert.equal(loopBlockCount({}, 'subagent_stop'), 0);
  assert.equal(loopBlockCount({}, 'bad'), 0);
});

// ADR-0003 amendment: the stop_hook_active yield is gated on this predicate so
// a runtime that erroneously sets the flag on a first Stop invocation cannot
// silently disable enforcement. It reads the count through loopBlockCount (the
// declared single read path) and ORs in the terminal policy-stall flag.
test('hasPriorStopBlock is true only when a prior stop block or policy stall exists', () => {
  assert.equal(hasPriorStopBlock({}), false, 'fresh session has no prior block');
  assert.equal(hasPriorStopBlock({ stop_block_count: 0, stalled_by_policy: false }), false);
  assert.equal(hasPriorStopBlock({ stop_block_count: 1 }), true, 'one prior block counts');
  assert.equal(hasPriorStopBlock({ stop_block_count: '2' }), true, 'coerces a string count');
  assert.equal(hasPriorStopBlock({ stop_block_count: 0, stalled_by_policy: true }), true, 'terminal policy stall counts');
  // A non-numeric / NaN count with no stall is NOT a prior block (Number(NaN)||0 = 0).
  assert.equal(hasPriorStopBlock({ stop_block_count: 'oops' }), false);
});

test('clearLoopBlockPatch zeroes stop fields and policy-stall state', () => {
  assert.deepEqual(clearLoopBlockPatch('stop'), {
    stop_block_count: 0, stop_block_reason: '', stop_block_message: '',
    stalled_by_policy: false, policy_stall_reason: '',
  });
  assert.equal(clearLoopBlockPatch('bad'), null);
  // The per-agent `subagent_stop` clear is no longer routed through this
  // function (the dispatcher clears one agent key via a map_delete event); it
  // returns null for a per-agent prefix instead of a full-map snapshot that
  // would re-introduce the ADR-0002 race clobber.
  assert.equal(clearLoopBlockPatch('subagent_stop'), null);
});

test('userPromptResetPatch returns scalar reset + mapClears for the per-agent map', () => {
  // ADR-0002 amendment: the per-agent map is cleared via a map_clear event
  // (listed in mapClears), not folded into the scalar set_many, so a
  // concurrent SubagentStop writer's key survives the turn reset.
  assert.deepEqual(userPromptResetPatch(), {
    scalar: {
      stop_block_count: 0, stop_block_reason: '', stop_block_message: '',
      stalled_by_policy: false, policy_stall_reason: '',
    },
    mapClears: ['subagent_stop_blocks'],
  });
});

// --- session_background_manager_pending ------------------------------------

test('sessionBackgroundManagerPending gating', () => {
  const base = { taskType: 'feature', managerMode: 'orchestrate', codeChanged: false, backgroundedAgent: true, startedRoles: ['m'] };
  assert.equal(sessionBackgroundManagerPending(base), true);
  assert.equal(sessionBackgroundManagerPending({ ...base, taskType: 'other' }), false);
  assert.equal(sessionBackgroundManagerPending({ ...base, managerMode: 'none' }), false);
  assert.equal(sessionBackgroundManagerPending({ ...base, codeChanged: true }), false);
  assert.equal(sessionBackgroundManagerPending({ ...base, backgroundedAgent: false }), false);
  assert.equal(sessionBackgroundManagerPending({ ...base, startedRoles: ['e'] }), false);
  assert.equal(sessionBackgroundManagerPending({ ...base, taskType: 'support' }), false);
});