import { test } from 'node:test';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import {
  loadAliases, canonicalizeSubagentLabel, extractSubagentLabel, extractSubagentScope,
  inferStartedRolesFromTranscript, effectiveStartedRoles, formatSubagentList,
  formatSubagentGroup, GENERIC_TYPES, isAgntHiveSpecialistRole,
  shouldEnforceSubagentFooter, isGenericType, isAliasesLoaded,
} from '../../plugins/agnthive/modules/agents.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const pluginRoot = join(here, '..', '..', 'plugins', 'agnthive');
const aliases = loadAliases(pluginRoot);
const transcripts = join(here, '..', '..', 'test', 'hooks', 'fixtures', 'transcripts');
import { readFileSync } from 'node:fs';
function readTranscript(name) { return readFileSync(join(transcripts, name), 'utf8'); }

test('loadAliases reads the bundled alias map', () => {
  assert.equal(aliases.cr.includes('code-reviewer'), true);
  assert.equal(aliases.a.includes('design'), true);
  assert.equal(aliases.e.includes('nerd'), true);
});

// --- canonicalizeSubagentLabel --------------------------------------------

const CANON_CASES = [
  ['Code Reviewer', 'cr'],
  ['code reviewer', 'cr'],
  ['@toxic-senior', 'cr'],
  ['design', 'a'],
  ['the-architect', 'a'],
  ['Tester', 't'],
  ['@paranoid', 't'],
  ['Explorer', 'e'],
  ['nerd', 'e'],
  ['Architect', 'a'],
  ['dbg', 'dbg'],
  ['manager', 'm'],
  ['big-boss', 'm'],
  ['general-purpose', 'general-purpose'],
  ['  @Code_Reviewer  ', 'cr'],
  ['', ''],
  [null, ''],
  // ADR 0004: strip a leading namespace: prefix before normalizing.
  ['agnthive:Explorer', 'e'],
  ['agnthive:Code Reviewer', 'cr'],
  ['agnthive:architect', 'a'],
  ['AGNTHIVE:Tester', 't'],
  ['@agnthive:Manager', 'm'],
  // Bare labels (no colon) are unchanged — general-purpose/workflow-subagent
  // are generic dispatch types, not canonical roles.
  ['workflow-subagent', 'workflow-subagent'],
  // ADR-0004 over-match guard: a foreign namespace prefix must NOT be stripped.
  // mcp:tester -> 'mcp-tester' (kept whole), NOT 'tester' -> 't'.
  // workflow:docs -> 'workflow-docs', NOT 'docs' -> 'doc'. Only the plugin's own
  // 'agnthive:' prefix is stripped; anything else is left intact and so is not
  // misrecognized as an AgntHive specialist.
  ['mcp:tester', 'mcp-tester'],
  ['workflow:docs', 'workflow-docs'],
  ['mcp:Code Reviewer', 'mcp-code-reviewer'],
];
for (const [raw, expected] of CANON_CASES) {
  test(`canonicalizeSubagentLabel(${JSON.stringify(raw)}) -> ${expected}`, () => {
    assert.equal(canonicalizeSubagentLabel(raw, aliases), expected);
  });
}

// --- extractSubagentLabel (fixture-driven) --------------------------------

const LABEL_FIXTURES = [
  ['subagent_start_code_reviewer', 'cr'],
  ['subagent_start_designer_alias', 'a'],
  ['subagent_start_tool_input_name_over_type', 't'],
  ['subagent_start_tool_input_subagent_type_over_agent_type', 't'],
  ['subagent_start_camelcase_subagent_type_over_agent_type', 'e'],
  ['subagent_start_top_level_subagent_type_over_type', 'a'],
  ['subagent_start_tool_input_agent_name_over_type', 'cr'],
  ['subagent_start_tool_input_agent_alias_over_type', 'dbg'],
];
for (const [name, expected] of LABEL_FIXTURES) {
  test(`extractSubagentLabel: ${name} -> @${expected}`, () => {
    const fx = JSON.parse(readFileSync(join(here, '..', '..', 'test', 'hooks', 'fixtures', `${name}.json`), 'utf8'));
    assert.equal(extractSubagentLabel(fx, aliases), expected);
  });
}

test('extractSubagentScope: tool_input.description normalized', () => {
  const fx = { tool_input: { description: '  Trace   workflow\nB  ', subagentType: 'Explorer' } };
  assert.equal(extractSubagentScope(fx), 'Trace workflow B');
});

test('extractSubagentScope: falls back through prompt/task', () => {
  assert.equal(extractSubagentScope({ tool_input: { prompt: 'Run it' } }), 'Run it');
  assert.equal(extractSubagentScope({ task: 'do thing' }), 'do thing');
  assert.equal(extractSubagentScope({}), '');
});

// --- inferStartedRolesFromTranscript --------------------------------------

test('infer roles: alias_pattern_multiple -> cr, e, t', () => {
  assert.deepEqual(inferStartedRolesFromTranscript(readTranscript('alias_pattern_multiple.jsonl'), aliases), ['cr', 'e', 't']);
});

test('infer roles: review_agent_started -> cr, m (Manager( + Code Reviewer()', () => {
  assert.deepEqual(inferStartedRolesFromTranscript(readTranscript('review_agent_started.jsonl'), aliases), ['cr', 'm']);
});

test('infer roles: review_skill_started -> cr, m (skill loads)', () => {
  assert.deepEqual(inferStartedRolesFromTranscript(readTranscript('review_skill_started.jsonl'), aliases), ['cr', 'm']);
});

test('infer roles: short @cr -> cr', () => {
  assert.deepEqual(inferStartedRolesFromTranscript(readTranscript('alias_pattern_short_cr.jsonl'), aliases), ['cr']);
});

test('infer roles: no false positives (@example.com / @email-settings), real @e kept', () => {
  const roles = inferStartedRolesFromTranscript(readTranscript('alias_pattern_no_false_positive.jsonl'), aliases);
  assert.deepEqual(roles, ['e']);
});

test('infer roles: empty/missing text -> []', () => {
  assert.deepEqual(inferStartedRolesFromTranscript('', aliases), []);
});

// --- effectiveStartedRoles ------------------------------------------------

test('effectiveStartedRoles merges explicit + inferred, filters generic types', () => {
  const state = { subagents_started: ['e', 'general-purpose', 'workflow-subagent'] };
  const text = '@cr confirmed';
  assert.deepEqual(effectiveStartedRoles(state, text, aliases), ['cr', 'e']);
});

test('effectiveStartedRoles with no transcript still returns explicit non-generic', () => {
  assert.deepEqual(effectiveStartedRoles({ subagents_started: ['t', 'general-purpose'] }, '', aliases), ['t']);
});

test('GENERIC_TYPES lists the Task dispatch types', () => {
  assert.deepEqual(GENERIC_TYPES, ['general-purpose', 'workflow-subagent']);
});

// --- formatting -----------------------------------------------------------

test('formatSubagentList / formatSubagentGroup', () => {
  assert.equal(formatSubagentList(['a', 'b']), '@a, @b');
  assert.equal(formatSubagentList([]), 'none');
  assert.equal(formatSubagentGroup(['e', 'a']), '@e/@a');
  assert.equal(formatSubagentGroup([]), '');
});

// --- isAgntHiveSpecialistRole (ADR 0001) -----------------------------------

test('isAgntHiveSpecialistRole: true for recognized canonical roles', () => {
  for (const role of ['a', 'e', 'bug', 'dbg', 't', 'cr', 'doc', 'm']) {
    assert.equal(isAgntHiveSpecialistRole(role, aliases), true, `expected ${role} to be recognized`);
  }
});

test('isAgntHiveSpecialistRole: false for generic dispatch types and unrecognized labels', () => {
  for (const label of ['general-purpose', 'workflow-subagent', 'agnthive-explorer', 'explorer', '', null, undefined, 42]) {
    assert.equal(isAgntHiveSpecialistRole(label, aliases), false, `expected ${JSON.stringify(label)} to not be recognized`);
  }
});

test('isAgntHiveSpecialistRole: false when aliases is empty', () => {
  assert.equal(isAgntHiveSpecialistRole('cr', {}), false);
});

test('isAgntHiveSpecialistRole: only own-property keys count, not inherited', () => {
  const proto = { cr: ['cr'] };
  const child = Object.create(proto);
  assert.equal(isAgntHiveSpecialistRole('cr', child), false);
});

// --- shouldEnforceSubagentFooter (ADR-0001 hardened scope) -----------------
// Guards the two regressions the adversarial review caught: (1) generic dispatch
// types are always exempt even when the alias map is missing, and (2) a missing
// alias map degrades to enforcing on all non-generic subagents (safe floor),
// never to silently disabling the footer contract.

test('isAliasesLoaded: shared predicate for alias-map loaded-ness', () => {
  assert.equal(isAliasesLoaded({ cr: 'Code Reviewer' }), true);
  assert.equal(isAliasesLoaded({}), false, 'an empty map is not loaded');
  assert.equal(isAliasesLoaded(null), false);
  assert.equal(isAliasesLoaded(undefined), false);
  assert.equal(isAliasesLoaded('not-an-object'), false);
  // The alias map is always a JSON object in practice; the predicate (shared
  // with shouldEnforceSubagentFooter's fallback, behavior-preserving) treats any
  // non-empty object as loaded, so a non-empty array reads as loaded too.
  assert.equal(isAliasesLoaded(['x']), true);
});

test('shouldEnforceSubagentFooter: generic types are exempt even with an empty alias map', () => {
  for (const label of GENERIC_TYPES) {
    assert.equal(shouldEnforceSubagentFooter(label, label, {}), false, `${label} must pass through with no aliases`);
    assert.equal(shouldEnforceSubagentFooter(label, null, {}), false, `${label} must pass through via label`);
  }
});

test('shouldEnforceSubagentFooter: raw agent_type also exempts generics', () => {
  assert.equal(shouldEnforceSubagentFooter('cr', 'general-purpose', aliases), false);
  assert.equal(shouldEnforceSubagentFooter('cr', 'workflow-subagent', aliases), false);
});

test('shouldEnforceSubagentFooter: recognized specialists are enforced when aliases loaded', () => {
  for (const role of ['a', 'e', 'bug', 'dbg', 't', 'cr', 'doc', 'm']) {
    assert.equal(shouldEnforceSubagentFooter(role, role, aliases), true, `${role} should be enforced`);
  }
});

test('shouldEnforceSubagentFooter: unrecognized non-generic labels pass through when aliases loaded', () => {
  for (const label of ['agnthive-explorer', 'explorer', 'mcp-tester', 'workflow-docs']) {
    assert.equal(shouldEnforceSubagentFooter(label, label, aliases), false, `${label} should pass through`);
  }
});

test('shouldEnforceSubagentFooter: safe floor — missing alias map enforces on all non-generic', () => {
  // loadAliases swallowed an error and returned {}: specialists must still be
  // enforced (not silently passed through), and unidentified non-generic labels
  // too. Only generic types and blank labels are exempt.
  assert.equal(shouldEnforceSubagentFooter('cr', 'cr', {}), true);
  assert.equal(shouldEnforceSubagentFooter('some-other-agent', 'some-other-agent', {}), true);
  assert.equal(shouldEnforceSubagentFooter('', '', {}), false);
  assert.equal(shouldEnforceSubagentFooter(null, null, {}), false);
  assert.equal(shouldEnforceSubagentFooter('general-purpose', 'general-purpose', {}), false);
});