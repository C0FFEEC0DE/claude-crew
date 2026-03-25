# Refactor Workflow

## When
Need to refactor code.

## Steps

### 1. Explore
```
@explorer explore code to refactor
```

### 2. Review
```
@code-reviewer what needs refactoring
```

### 3. Design
```
@architect design improved structure
```

### 4. Refactor
Refactor the code while preserving behavior.

### 5. Verify
```
@tester run tests and report whether behavior stayed stable
```

### 6. Document
```
@docwriter update docs only if public behavior or operator guidance changed
```

### 7. Review
```
@code-reviewer review refactored code
```

## Command
Just say: "@manager refactor [module/file]"

Hooks enforce verification before completion.
