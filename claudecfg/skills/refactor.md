# /refactor

Run refactoring session with the Housekeeper agent.

## When to use
- Code duplication
- Functions too long (>50 lines)
- Bad variable names
- Tests became fragile
- Technical debt cleanup

## Usage
```
/refactor [what to refactor]
```

## Examples
```
/refactor the auth module
/refactor extract common logic from services
/refactor rename variables in user controller
```

## Agent
Invokes @housekeeper (The Cleaner) who will:
1. Identify refactoring targets
2. Propose clean, incremental changes
3. Ensure tests still pass
4. Leave code cleaner than found
5. Report what was changed
