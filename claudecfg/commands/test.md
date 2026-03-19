# /test

Run testing session.

## When to use
- Need to write tests
- Check existing ones
- Coverage dropped
- Regression

## Process
1. Find what to test
2. Unit → Integration → E2E
3. AAA pattern (Arrange, Act, Assert)
4. Name describe('...')
5. One assertion per test

## Important
- Tests should be isolated
- Don't test internals — only API
- Mock external dependencies
- 100% coverage is not the goal