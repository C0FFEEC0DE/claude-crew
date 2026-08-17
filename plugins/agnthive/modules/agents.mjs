// agents.mjs — role inference, alias normalization, subagent labeling.
// Ported from lib.sh: extract_subagent_label, extract_subagent_scope,
// canonicalize_subagent_label, infer_started_roles_from_transcript,
// effective_started_roles, format_subagent_list, format_subagent_group.
// Backed by assets/aliases.json for transcript compatibility. Node stdlib only.
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

/** Generic Task tool dispatch types, filtered from role enforcement. */
export const GENERIC_TYPES = ['general-purpose', 'workflow-subagent'];

/** True if `x` is a generic Task tool dispatch type (not an agent role). */
export function isGenericType(x) {
  return typeof x === 'string' && GENERIC_TYPES.includes(x);
}

/**
 * True if the alias map is loaded (a non-empty plain object). Single source of
 * truth for the "is the alias map loaded?" predicate: the dispatcher precomputes
 * it once at module init (the map is immutable for the process lifetime) and
 * `shouldEnforceSubagentFooter` derives it from `aliases` when the caller omits
 * the precomputed boolean. Sharing the predicate keeps the safe-floor
 * degradation logic from drifting between the two modules.
 */
export function isAliasesLoaded(aliases) {
  return !!(aliases && typeof aliases === 'object' && Object.keys(aliases).length > 0);
}

/** Load the alias map from assets/aliases.json (returns {} if missing). */
export function loadAliases(pluginRoot) {
  if (!pluginRoot) return {};
  try { return JSON.parse(readFileSync(join(pluginRoot, 'assets', 'aliases.json'), 'utf8')); } catch { return {}; }
}

function getPath(obj, dotted) {
  let cur = obj;
  for (const k of dotted.split('.')) {
    if (cur == null || typeof cur !== 'object') return undefined;
    cur = cur[k];
  }
  return cur;
}

// Field paths probed in order by extract_subagent_label (jq `//` chain).
const LABEL_PATHS = [
  'agent_alias', 'agentAlias', 'alias', 'subagent_alias', 'subagentAlias',
  'subagent_type', 'subagentType',
  'tool_input.agent_alias', 'tool_input.agentAlias', 'tool_input.alias',
  'tool_input.subagent_alias', 'tool_input.subagentAlias',
  'tool_input.subagent_type', 'tool_input.subagentType',
  'agent_name', 'agentName', 'subagent_name', 'subagentName', 'name',
  'tool_input.agent', 'tool_input.agent_name', 'tool_input.agentName',
  'tool_input.subagent_name', 'tool_input.subagentName', 'tool_input.name',
  'tool_input.type', 'tool_input.agent_type', 'tool_input.agentType',
  'agent_type', 'agentType', 'type',
];

const SCOPE_PATHS = [
  'tool_input.description', 'tool_input.prompt', 'tool_input.task',
  'description', 'prompt', 'task',
];

/**
 * canonicalize_subagent_label: lowercase, strip leading @, turn whitespace and
 * underscores into dashes, drop non-[a-z0-9.-], trim/collapse dashes, then map
 * to a canonical role via the alias map (key whose value list contains it).
 */
export function canonicalizeSubagentLabel(raw, aliases = {}) {
  if (raw == null) return '';
  let n = String(raw).toLowerCase().replace(/^@/, '');
  // Strip only this plugin's own namespace prefix (e.g. agnthive:Explorer ->
  // explorer) so plugin-namespaced agent types canonicalize to the bare role.
  // Narrowing to the 'agnthive' prefix avoids over-matching foreign namespaces:
  // mcp:tester -> tester -> t or workflow:docs -> docs -> doc would otherwise be
  // misrecognized as AgntHive specialists and footer-blocked (the ADR-0001 bug
  // reintroduced for any colon-suffixed type). No alias value or canonical role
  // contains a colon, and the plugin namespace is the only one we own.
  if (n.startsWith('agnthive:')) n = n.slice('agnthive:'.length);
  // Guard against ReDoS on unbounded input — labels are short identifiers.
  if (n.length > 128) n = n.slice(0, 128);
  n = n.replace(/[\s_]/g, '-');
  n = n.replace(/[^a-z0-9.-]/g, '-');
  // Collapse consecutive dashes and trim leading/trailing dashes
  // (split/filter/join avoids /-+/g regex flagged by CodeQL js/polynomial-redos).
  n = n.split('-').filter(Boolean).join('-');
  if (!n) return '';
  for (const [canonical, list] of Object.entries(aliases)) {
    if (Array.isArray(list) && list.includes(n)) return canonical;
  }
  return n;
}

/** extract_subagent_label: first non-null label field, canonicalized. */
export function extractSubagentLabel(hookInput, aliases = {}) {
  for (const p of LABEL_PATHS) {
    const v = getPath(hookInput, p);
    if (v !== undefined && v !== null) return canonicalizeSubagentLabel(v, aliases);
  }
  return '';
}

/** extract_subagent_scope: first non-null scope field, whitespace-normalized. */
export function extractSubagentScope(hookInput) {
  for (const p of SCOPE_PATHS) {
    const v = getPath(hookInput, p);
    if (v !== undefined && v !== null) {
      return String(v).replace(/\s+/g, ' ').replace(/^ /, '').replace(/ $/, '');
    }
  }
  return '';
}

// skill(...) / Name(...) launch-line patterns -> role. Order matters: longer
// alternatives first so "code reviewer(" is matched before "reviewer(".
const LAUNCH_RE = /skill\(\/(manager|review|test|explore|design|bug|debug|docs|refactor)\)|manager\(|code reviewer\(|tester\(|explorer\(|architect\(|bugbuster\(|debugger\(|docwriter\(/gi;

const ALIAS_RE = /@(m|e|a|t|cr|bug|dbg|doc|manager|explorer|architect|tester|code-reviewer|code-review|reviewer|bugbuster|debugger|docwriter|big-boss|nerd|toxic-senior|paranoid|the-architect|wiki-wiki)($|[^a-z0-9-])/gi;

function roleFromLaunch(match) {
  const m = match.toLowerCase();
  if (m === 'skill(/manager)' || m === 'manager(') return 'm';
  if (m === 'skill(/review)' || m === 'code reviewer(') return 'cr';
  if (m === 'skill(/test)' || m === 'tester(') return 't';
  if (m === 'skill(/explore)' || m === 'explorer(') return 'e';
  if (m === 'skill(/design)' || m === 'skill(/refactor)' || m === 'architect(') return 'a';
  if (m === 'skill(/bug)' || m === 'bugbuster(') return 'bug';
  if (m === 'skill(/debug)' || m === 'debugger(') return 'dbg';
  if (m === 'skill(/docs)' || m === 'docwriter(') return 'doc';
  return null;
}

/**
 * infer_started_roles_from_transcript: scan transcript text for skill()/Name()
 * launch lines and @alias mentions, map each to a canonical role, and return
 * the unique sorted set.
 */
export function inferStartedRolesFromTranscript(transcriptText, aliases = {}) {
  if (!transcriptText) return [];
  const roles = new Set();
  for (const m of transcriptText.matchAll(LAUNCH_RE)) {
    const r = roleFromLaunch(m[0]);
    if (r) roles.add(r);
  }
  for (const m of transcriptText.matchAll(ALIAS_RE)) {
    if (m[1]) {
      const c = canonicalizeSubagentLabel(m[1], aliases);
      if (c) roles.add(c);
    }
  }
  return [...roles].filter(Boolean).sort();
}

/**
 * effective_started_roles: explicit roles from state.subagents_started (generic
 * dispatch types filtered out) plus roles inferred from the transcript, unique
 * and sorted.
 */
export function effectiveStartedRoles(state, transcriptText, aliases = {}) {
  const explicit = Array.isArray(state?.subagents_started) ? state.subagents_started : [];
  const roles = new Set();
  for (const r of explicit) {
    if (typeof r === 'string' && r && !isGenericType(r)) roles.add(r);
  }
  for (const r of inferStartedRolesFromTranscript(transcriptText, aliases)) roles.add(r);
  return [...roles].sort();
}

/**
 * isAgntHiveSpecialistRole: true iff `label` is a non-empty string that is a
 * key of `aliases` — i.e. one of the recognized canonical roles
 * (a | e | bug | dbg | t | cr | doc | m). Generic dispatch types and
 * unrecognized labels return false so footer enforcement can pass them through.
 */
export function isAgntHiveSpecialistRole(label, aliases = {}) {
  return typeof label === 'string' && label !== '' && Object.prototype.hasOwnProperty.call(aliases, label);
}

/**
 * shouldEnforceSubagentFooter: the ADR-0001 scope decision, hardened against the
 * two regressions the adversarial review caught.
 *
 *  1. Generic dispatch types (general-purpose, workflow-subagent) are ALWAYS
 *     exempt — they are hardcoded Task tool types, not agent roles, and must
 *     never be footer-blocked regardless of the alias map. This exemption is
 *     checked against the hardcoded GENERIC_TYPES list (and the raw agent_type
 *     when available), so it holds even if the alias map failed to load.
 *  2. Safe floor: when the alias map is available, enforce only for recognized
 *     AgntHive specialists (the ADR-0001 scope). When loadAliases swallowed an
 *     error and returned {} — aliases.json missing or corrupt — isAgntHiveSpecialistRole
 *     would always be false and EVERY subagent (including specialists) would pass
 *     through, silently disabling the footer contract. As a floor, a missing
 *     map enforces on all non-generic subagents so the safety contract degrades
 *     loud, not silent.
 *
 * `aliasesLoaded` is an optional boolean the caller may precompute once at
 * module init (the alias map is immutable for the process lifetime) to avoid
 * the per-call `Object.keys(aliases).length` allocation on the SubagentStop
 * hot path. When omitted it is derived from `aliases`.
 */
export function shouldEnforceSubagentFooter(label, rawType = null, aliases = {}, aliasesLoaded) {
  if (isGenericType(label)) return false;
  if (isGenericType(rawType)) return false;
  const loaded = typeof aliasesLoaded === 'boolean'
    ? aliasesLoaded
    : isAliasesLoaded(aliases);
  if (loaded) return isAgntHiveSpecialistRole(label, aliases);
  // No alias map (missing/corrupt): enforce on every non-generic subagent as a
  // safe floor. An empty/blank label is treated as unidentified and not enforced.
  return typeof label === 'string' && label !== '';
}

/** format_subagent_list: "@a, @b" or "none" for an empty list. */
export function formatSubagentList(items) {
  if (!Array.isArray(items) || items.length === 0) return 'none';
  return items.map((i) => `@${i}`).join(', ');
}

/** format_subagent_group: "@a/@b" for any-of groups. */
export function formatSubagentGroup(items) {
  if (!Array.isArray(items) || items.length === 0) return '';
  return items.map((i) => `@${i}`).join('/');
}