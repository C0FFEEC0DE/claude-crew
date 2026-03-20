# Release Workflow

## When
Preparing for release.

## Steps

### 1. Docs
```
@docwriter update documentation
```

### 2. Review
```
@code-reviewer full review
```

### 3. Tests
```
@tester ensure all tests pass
```

### 4. Cleanup
```
@housekeeper pre-release cleanup
```

## Command
Just say: "@manager prepare release"