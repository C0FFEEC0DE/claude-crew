# Bug Fix Workflow

## When
Found a bug → need to fix it.

## Steps

### 1. Explore
```
@explorer understand the bug area
```

### 2. Find
```
@bugbuster find the root cause
```

### 3. Design Fix
```
@architect design the fix for [root cause]
```

### 4. Implement
Implement the fix in code.

### 5. Verify
```
@tester run regression tests for the fix and report pass/fail
```

### 6. Document
```
@docwriter document the bug fix if behavior, interface, or operator workflow changed
```

### 7. Review
```
@code-reviewer review the fix
```

## Commands

**Get plan:**
```
@manager fix bug in [area]
```

Hooks enforce the final verification gate before task completion.
