// workflow.mjs — UserPromptSubmit classification, manager modes, docs/role
// requirements, and stop/subagent loop-block accounting. Pure module: no
// filesystem, no side effects. The dispatcher wires this to state.mjs events
// and hook-output.mjs. Ported from claudecfg/hooks/user-prompt-submit.sh and
// the lib.sh functions task_type_requires_implementation_summary,
// task_type_requires_specialist_handoffs, record_loop_block, clear_loop_block,
// loop_block_count, session_background_manager_pending.
//
// Regexes use the 'iu' flags so [[:alpha:]] -> \p{L}, [[:space:]] -> \s,
// [[:punct:]] -> \p{P} behave like grep -Ei in a UTF-8 locale (case-insensitive
// for Latin and Cyrillic). Node 22+ supports these Unicode classes.

const STOP_SAFE_HINT = ' If a later reply in the same session makes no additional changes, still report the actual verification, review, changed files, docs status when relevant, and remaining risks instead of using a no-change shortcut after code or config changes.';

const RE_MANAGER_ORCHESTRATE = /(^|\s)(@m|@manager|\/manager)($|[\s\p{P}])/iu;
const RE_PLAN_ONLY = /(plan only|only plan|plan-only|только план|только спланиру|только составь план|сделай план,? но не выполняй|без выполнения|без реализации)/iu;
const RE_OVERRIDE = /workflow override: treat this as a (feature|bugfix|refactor|review|docs|support|other) workflow/i;
const RE_WORKFLOW_CATEGORY = /workflow_category:\s*(feature|bugfix|refactor|review|docs|support|other)/i;

// Machine-readable dispatch contract injected by the benchmark runner into the
// ROOT prompt only (see bench_runner_claude_code.mjs dispatchContractMarker).
// When present, the plugin requires exactly the listed specialist(s) instead of
// the category-default role set, so a tiny task is not forced to also dispatch
// @t/@cr/one-of groups that the runner does not ask for.
// Fixed single-space form: dispatchContractMarker() always emits
// "BENCHMARK_DISPATCH_CONTRACT: [root_only; ]mode=…; roles=…". Literal spaces
// (not \s*) avoid the polynomial backtracking CodeQL flags on long \t runs.
const RE_DISPATCH_CONTRACT = /BENCHMARK_DISPATCH_CONTRACT: (root_only; )?mode=(observed|enforced|standard); roles=([A-Za-z0-9_,-]{1,64})/i;

const RE_MODEL_TERMS = /(model|models|llm|ollama|openrouter|qwen|llama|deepseek|mistral|claude|gpt|gemini|command r|модел|модели|модель)/iu;
const RE_QUESTION_TERMS = /(which|what|recommend|recommendation|compare|best|better|vs|versus|open source|opensource|closed model|api|creative|creativity|style|storytelling|какую|какой|посовет|совет|рекоменд|сравн|лучш|выбрат|подскажи|подбери|нужн|креатив|стиль|сторител|иде[йи])/iu;
const RE_EXCLUSION_TERMS = /(feature|implement|add support|integrat|new capability|фич|добав|интеграц|подключ|fix|bug|defect|баг|ошиб|исправ|refactor|rename|cleanup|tech debt|рефактор|почист|переимен|review|audit|ревью|аудит|проверь|docs|readme|document|док|ридми)/iu;

const RE_BUGFIX = /(^|[^\p{L}])(bugfix|bug|defect|regression|fix|fixes|fixed|fixing|баг|ошиб|исправ)([^\p{L}]|$)/iu;
const RE_REFACTOR = /(refactor|rename|cleanup|tech debt|рефактор|почист|переимен)/iu;
const RE_REVIEW = /(review|audit|ревью|аудит|проверь)/iu;
const RE_DOCS = /(docs|readme|document|док|ридми)/iu;
const RE_FEATURE = /(feature|implement|add support|integrat|new capability|фич|добав|интеграц|подключ|модел|pyrit|openrouter)/iu;

const RE_CODE_SIGNALS = /(\.py\b|\.js\b|\.ts\b|\.tsx\b|\.jsx\b|\.rs\b|\.go\b|\.java\b|\.kt\b|\.c\b|\.cc\b|\.cpp\b|\.h\b|\.hpp\b|package\.json\b|pyproject\.toml\b|cargo\.toml\b|go\.mod\b|pom\.xml\b|build\.gradle\b|cmakelists\.txt\b|makefile\b|dockerfile\b|src\/|tests?\/|pytest\b|jest\b|vitest\b|npm\b|yarn\b|pnpm\b|pip\b|venv\b|ci\b|github actions\b|pull request\b|commit\b|branch\b|diff\b|patch\b|код\b|файл\b|репозитор|проект\b)/iu;
const RE_TECH_SUPPORT_SIGNALS = /(fedora|ubuntu|debian|arch linux|kernel|ядро|dmesg|lsusb|udev|systemctl|modemmanager|ttyusb|ttys|\/dev\/tty|dialout|uucp|com[- ]?port|rs[- ]?232|serial|usb[- ]?to[- ]?serial|driver|драйвер|pilot[- ]?link|hotsync|palm\b|palmos|кредл|док[- ]?станц)/iu;

const TASK_TYPES = ['feature', 'bugfix', 'refactor', 'review', 'docs', 'support', 'other'];

function uniq(arr) {
  return [...new Set(arr)];
}

/**
 * Parse a BENCHMARK_DISPATCH_CONTRACT marker from a prompt. Returns
 * { rootOnly, mode, roles } (roles lowercased canonical aliases) or null when
 * no marker is present. Pure; no I/O.
 */
export function parseDispatchContractMarker(text) {
  if (typeof text !== 'string') return null;
  const m = text.match(RE_DISPATCH_CONTRACT);
  if (!m) return null;
  const roles = String(m[3]).split(',').map((r) => r.trim().toLowerCase()).filter(Boolean);
  if (!roles.length) return null;
  return { rootOnly: Boolean(m[1]), mode: String(m[2]).toLowerCase(), roles };
}

/**
 * Classify a user prompt. Returns the task type, manager mode, required
 * subagents, any-of groups, docs-required flag, and the context message to
 * emit (or '' to emit nothing). Pure; no I/O.
 */
export function classifyPrompt(prompt) {
  const text = typeof prompt === 'string' ? prompt : '';
  let taskType = 'other';
  let managerMode = 'none';
  let requiredSubagents = [];
  let requiredSubagentAnyOf = [];
  let contextMessage = '';

  if (RE_MANAGER_ORCHESTRATE.test(text)) managerMode = 'orchestrate';
  if (RE_PLAN_ONLY.test(text)) managerMode = 'plan_only';

  let overrideTaskType = '';
  const ov = text.match(RE_OVERRIDE);
  if (ov) overrideTaskType = ov[1];
  if (!overrideTaskType) {
    const cat = text.match(RE_WORKFLOW_CATEGORY);
    if (cat) overrideTaskType = cat[1];
  }

  const informationalModelQuery =
    RE_MODEL_TERMS.test(text)
    && RE_QUESTION_TERMS.test(text)
    && !RE_EXCLUSION_TERMS.test(text);

  if (overrideTaskType) {
    taskType = overrideTaskType;
  } else if (informationalModelQuery) {
    taskType = 'other';
  } else if (RE_BUGFIX.test(text)) {
    taskType = 'bugfix';
  } else if (RE_REFACTOR.test(text)) {
    taskType = 'refactor';
  } else if (RE_REVIEW.test(text)) {
    taskType = 'review';
  } else if (RE_DOCS.test(text)) {
    taskType = 'docs';
  } else if (RE_FEATURE.test(text)) {
    taskType = 'feature';
  }

  // Tech-support reclassification: a device/OS support prompt with no code
  // signals becomes "support" even if it contains the word "bug".
  if (!overrideTaskType && !informationalModelQuery && taskType !== 'other') {
    const hasCodeSignals = RE_CODE_SIGNALS.test(text);
    const hasTechSupportSignals = RE_TECH_SUPPORT_SIGNALS.test(text);
    if (hasTechSupportSignals && !hasCodeSignals) taskType = 'support';
  }

  if (managerMode === 'plan_only') {
    requiredSubagents = [];
    requiredSubagentAnyOf = [];
  }

  let docsRequired = false;
  switch (taskType) {
    case 'feature':
      if (managerMode !== 'plan_only') {
        requiredSubagents = uniq([...requiredSubagents, 't', 'cr']);
        requiredSubagentAnyOf = [['e', 'a']];
      }
      contextMessage = 'Treat this as a feature workflow.';
      docsRequired = true;
      break;
    case 'bugfix':
      if (managerMode !== 'plan_only') {
        requiredSubagents = uniq([...requiredSubagents, 't', 'cr']);
        requiredSubagentAnyOf = [['bug', 'e', 'dbg']];
      }
      contextMessage = 'Treat this as a bugfix workflow.';
      docsRequired = true;
      break;
    case 'refactor':
      if (managerMode !== 'plan_only') {
        requiredSubagents = uniq([...requiredSubagents, 't', 'cr']);
        requiredSubagentAnyOf = [['a', 'e']];
      }
      contextMessage = 'Treat this as a refactor workflow.';
      docsRequired = true;
      break;
    case 'review':
      if (managerMode !== 'plan_only') {
        requiredSubagents = uniq([...requiredSubagents, 'cr']);
      }
      contextMessage = 'Treat this as a review workflow.';
      break;
    case 'docs':
      if (managerMode !== 'plan_only') {
        requiredSubagents = uniq([...requiredSubagents, 'doc']);
      }
      contextMessage = 'Treat this as a docs workflow.';
      docsRequired = true;
      break;
    case 'support':
      contextMessage = 'Treat this as a support workflow.';
      break;
    default:
      break;
  }

  if (contextMessage) contextMessage = buildContextMessage(taskType, managerMode, contextMessage);

  // A benchmark dispatch contract (root-only marker) overrides the
  // category-default required roles: require exactly the listed specialist(s)
  // and clear any-of groups, so runner and hook agree on a single contract.
  const dispatchContract = parseDispatchContractMarker(text);
  if (dispatchContract) {
    requiredSubagents = dispatchContract.roles;
    requiredSubagentAnyOf = [];
    const roles = dispatchContract.roles.map((r) => '@' + r).join(', ');
    contextMessage =
      `Benchmark dispatch contract active (mode=${dispatchContract.mode}, root_only). ` +
      `Required specialist handoff before completion: ${roles}. ` +
      `Only the listed role(s) satisfy the contract; do not add category-default specialist handoffs. ` +
      `Run verification after changes and report changed files and remaining risks before stopping.${STOP_SAFE_HINT}`;
  }

  return {
    taskType,
    managerMode,
    requiredSubagents,
    requiredSubagentAnyOf,
    docsRequired,
    contextMessage,
    informationalModelQuery,
    overrideTaskType,
    // Benchmark dispatch-contract mode from the BENCHMARK_DISPATCH_CONTRACT
    // marker ('' when absent). Persisted to session state so the PreToolUse
    // EditWrite guard can enforce 'enforced' without re-reading the prompt.
    dispatchContractMode: dispatchContract ? dispatchContract.mode : '',
  };
}

function buildContextMessage(taskType, managerMode, base) {
  const orchestrate = managerMode === 'orchestrate';
  const planOnly = managerMode === 'plan_only';
  switch (taskType) {
    case 'feature':
      if (orchestrate) return `${base} Manager-led orchestration is active. Required before completion: successful verification or @t, plus @cr and one of @e/@a. Start the first required specialist handoff early instead of spending multiple turns in manager-only exploration. Keep the workflow moving through implementation, verification, review, and docs when behavior changes.${STOP_SAFE_HINT}`;
      if (planOnly) return `${base} Plan-only manager mode is active. Return a concrete execution plan without continuing implementation or specialist handoffs in this session.`;
      return `${base} Required before completion: successful verification or @t, plus @cr and one of @e/@a. Finish implementation, run verification successfully, address review findings, and update docs when behavior changes. release/deploy remains out of scope.${STOP_SAFE_HINT}`;
    case 'bugfix':
      if (orchestrate) return `${base} Manager-led orchestration is active. Required before completion: successful verification or @t, plus @cr and one of @bug/@e/@dbg. Start the first required specialist handoff early instead of spending multiple turns in manager-only exploration. Reproduce or describe the failure mode, implement the fix, execute regression verification, and update docs if behavior changed.${STOP_SAFE_HINT}`;
      if (planOnly) return `${base} Plan-only manager mode is active. Return a concrete bugfix plan without continuing implementation or specialist handoffs in this session.`;
      return `${base} Required before completion: successful verification or @t, plus @cr and one of @bug/@e/@dbg. Reproduce or describe the failure mode, implement the fix, execute regression verification, and update docs if behavior changed.${STOP_SAFE_HINT}`;
    case 'refactor':
      if (orchestrate) return `${base} Manager-led orchestration is active. Required before completion: successful verification or @t, plus @cr and one of @a/@e. Start the first required specialist handoff early instead of spending multiple turns in manager-only exploration. Keep scope to structure and maintainability, preserve behavior, run verification after changes, and decide whether docs need updates.${STOP_SAFE_HINT}`;
      if (planOnly) return `${base} Plan-only manager mode is active. Return a concrete refactor plan without continuing implementation or specialist handoffs in this session.`;
      return `${base} Required before completion: successful verification or @t, plus @cr and one of @a/@e. Keep scope to structure and maintainability, preserve behavior, run verification after changes, and summarize risks plus changed files before stopping.${STOP_SAFE_HINT}`;
    case 'review':
      if (orchestrate) return `${base} Manager-led orchestration is active. Required specialist handoff before completion: @cr. Start the code-reviewer handoff early instead of extending manager-only analysis. Focus on findings first, call out residual risks or testing gaps, and keep implementation out of scope unless the user explicitly asks for fixes.${STOP_SAFE_HINT}`;
      if (planOnly) return `${base} Plan-only manager mode is active. Return the review plan without continuing specialist handoffs in this session.`;
      return `${base} Required subagent handoff before completion: @cr. Focus on findings first, call out residual risks or testing gaps, and keep implementation out of scope unless the user explicitly asks for fixes.${STOP_SAFE_HINT}`;
    case 'docs':
      if (orchestrate) return `${base} Manager-led orchestration is active. Required specialist handoff before completion: @doc. Start the docwriter handoff early instead of extending manager-only analysis. Keep documentation accurate to current behavior, include examples when they materially help, and note any remaining drift or missing verification.${STOP_SAFE_HINT}`;
      if (planOnly) return `${base} Plan-only manager mode is active. Return the docs plan without continuing specialist handoffs in this session.`;
      return `${base} Required subagent handoff before completion: @doc. Keep documentation accurate to current behavior, include examples when they materially help, and note any remaining drift or missing verification.${STOP_SAFE_HINT}`;
    case 'support':
      if (planOnly) return `${base} Plan-only manager mode is active. Return the diagnostic plan without implementation or specialist handoffs in this session.`;
      return `${base} Keep this in advisory or troubleshooting mode unless the user explicitly requests repository changes. No workflow-specific specialist handoffs are required before completion.`;
    default:
      return base;
  }
}

/** task_type_requires_implementation_summary: feature|bugfix|refactor|review|docs. */
export function taskTypeRequiresImplementationSummary(taskType) {
  return taskType === 'feature' || taskType === 'bugfix' || taskType === 'refactor'
    || taskType === 'review' || taskType === 'docs';
}

/** task_type_requires_specialist_handoffs: feature|bugfix|refactor|review|docs|support. */
export function taskTypeRequiresSpecialistHandoffs(taskType) {
  return taskTypeRequiresImplementationSummary(taskType) || taskType === 'support';
}

/**
 * Map a loop-block prefix to its state field layout, or null if unknown.
 *
 * The `stop` prefix is a session-global scalar (the main agent has no
 * agent_id); the `subagent_stop` prefix is a per-agent map keyed by agent_id
 * so cross-agent accumulation can no longer terminate processing (ADR-0002).
 * When agent_id is absent, a shared `_session` key keeps the safety backstop
 * working for runtimes that omit agent_id.
 *
 * The two layouts are frozen module-level constants so every caller
 * (`loopBlockCount`, `recordLoopBlock`, `clearLoopBlockPatch`,
 * `emitLoopAwareBlock`) shares one reference instead of allocating a fresh
 * object per call — `loopBlockFields` is on the block hot path and may be
 * called more than once per block.
 */
const STOP_FIELDS = Object.freeze({
  countKey: 'stop_block_count',
  reasonKey: 'stop_block_reason',
  messageKey: 'stop_block_message',
  perAgent: false,
});
const SUBAGENT_STOP_FIELDS = Object.freeze({
  mapKey: 'subagent_stop_blocks',
  perAgent: true,
});

export function loopBlockFields(prefix) {
  switch (prefix) {
    case 'stop': return STOP_FIELDS;
    case 'subagent_stop': return SUBAGENT_STOP_FIELDS;
    default: return null;
  }
}

/**
 * The per-agent loop-block key: the agent's id when present, else the shared
 * `_session` backstop for runtimes that omit `agent_id`. Single source of truth
 * for the fallback (ADR 0006) — every per-agent loop-block site calls this.
 */
export function agentLoopKey(agentId) {
  return agentId || '_session';
}

/**
 * Read the current loop-block count for a prefix from a state object. The
 * scalar `stop` branch is the production read path — `hasPriorStopBlock` (the
 * ADR-0003 amendment gate) reads through it, so the count-read rule lives in one
 * place. The per-agent `subagent_stop` branch is model-completeness + a
 * test-pinned read contract: production carries the per-agent count forward via
 * `recordLoopBlock`'s returned `entry.count` (ADR-0005), not by re-reading state
 * here. It is kept for API symmetry and as a diagnostic/debug surface.
 */
export function loopBlockCount(state, prefix, agentId = null) {
  const f = loopBlockFields(prefix);
  if (!f) return 0;
  if (f.perAgent) {
    return Number(state?.[f.mapKey]?.[agentLoopKey(agentId)]?.count) || 0;
  }
  return Number(state?.[f.countKey]) || 0;
}

/**
 * Compute the next loop-block entry. If reason+message match the previous
 * values, the count increments; otherwise it resets to 1. Pure.
 *
 * For the per-agent `subagent_stop` prefix, returns `{ mapKey, key, entry }`
 * — the single changed key plus its new `{ count, reason, message }` entry,
 * with no full-map snapshot. The dispatcher persists `entry` via a single-key
 * `map_set` (ADR-0002 race fix), and `emitLoopAwareBlock` threads it straight
 * into `perKey`, so the merged map is never needed (ADR-0005: carry the entry
 * explicitly). For the session-global `stop` prefix, returns the scalar patch
 * (`{ [countKey], [reasonKey], [messageKey] }`) persisted as-is via `set_many`.
 */
export function recordLoopBlock(state, prefix, reason, message, agentId = null) {
  const f = loopBlockFields(prefix);
  if (!f) return null;
  if (f.perAgent) {
    const map = state?.[f.mapKey] || {};
    const key = agentLoopKey(agentId);
    const prev = map[key];
    const nextCount = (prev?.reason === reason && prev?.message === message)
      ? (Number(prev.count) || 0) + 1 : 1;
    return { mapKey: f.mapKey, key, entry: { count: nextCount, reason, message } };
  }
  const prevReason = state?.[f.reasonKey] ?? '';
  const prevMessage = state?.[f.messageKey] ?? '';
  const prevCount = Number(state?.[f.countKey]) || 0;
  const nextCount = (prevReason === reason && prevMessage === message) ? prevCount + 1 : 1;
  return {
    [f.countKey]: nextCount,
    [f.reasonKey]: reason,
    [f.messageKey]: message,
  };
}

/**
 * Patch that clears the session-global `stop` loop block (and policy-stall
 * state). Scalar-only: the per-agent `subagent_stop` clear is no longer routed
 * through this function — the dispatcher clears one agent key via a `map_delete`
 * event (see hook-dispatcher.mjs `handleSubagentStop`), which avoids the
 * last-writer-wins full-map clobber a `set_many`-based clear would reintroduce.
 */
export function clearLoopBlockPatch(prefix) {
  const f = loopBlockFields(prefix);
  if (!f || f.perAgent) return null;
  return {
    [f.countKey]: 0,
    [f.reasonKey]: '',
    [f.messageKey]: '',
    stalled_by_policy: false,
    policy_stall_reason: '',
  };
}

/**
 * True when there is evidence of a prior `stop` block this session: a non-zero
 * session-global stop-block count, or a terminal policy stall. ADR-0003
 * amendment: the `stop_hook_active` yield is gated on this so a runtime that
 * erroneously sets the flag on a first Stop invocation cannot silently disable
 * enforcement. Encapsulates the two-field policy check so the dispatcher states
 * policy rather than field names, and routes the read through `loopBlockCount`
 * (the declared single read path) instead of restating the scalar field inline.
 */
export function hasPriorStopBlock(state) {
  return loopBlockCount(state, 'stop') > 0 || state?.stalled_by_policy === true;
}

/**
 * A real user prompt starts a new attempt after a terminal stop-hook failure,
 * so the stop loop resets. Returns a structured reset applied on
 * UserPromptSubmit (after classification):
 *   - `scalar`: the session-global stop-loop + policy-stall fields, persisted
 *     as one `set_many`.
 *   - `mapClears`: per-agent maps to clear via `map_clear` events (ADR-0002
 *     amendment) — NOT folded into the scalar set_many. This keeps the invariant
 *     "all subagent_stop_blocks mutations flow through map_* events" with zero
 *     exceptions (model consistency). It is NOT a per-key race fix: a clear is
 *     intentionally whole-map (a new turn starts fresh), so a concurrent map_set
 *     appended before the clear is wiped just as a set_many would. The ADR-0002
 *     race fix proper is the per-key map_set/map_delete write path.
 *
 * The dispatcher emits the scalar patch and one `map_clear` per listed map.
 */
export function userPromptResetPatch() {
  return {
    scalar: {
      stop_block_count: 0,
      stop_block_reason: '',
      stop_block_message: '',
      stalled_by_policy: false,
      policy_stall_reason: '',
    },
    mapClears: ['subagent_stop_blocks'],
  };
}

/**
 * session_background_manager_pending: true only when a gated task is in
 * orchestrate mode with no code change yet, a backgrounded agent is in flight,
 * and the manager role has started. Pure; the dispatcher supplies the
 * transcript-derived `backgroundedAgent` flag and `startedRoles` list.
 */
export function sessionBackgroundManagerPending({ taskType, managerMode, codeChanged, backgroundedAgent, startedRoles }) {
  if (!taskTypeRequiresImplementationSummary(taskType)) return false;
  if (managerMode !== 'orchestrate') return false;
  if (codeChanged === true) return false;
  if (!backgroundedAgent) return false;
  if (!Array.isArray(startedRoles) || !startedRoles.includes('m')) return false;
  return true;
}

export { STOP_SAFE_HINT, TASK_TYPES };