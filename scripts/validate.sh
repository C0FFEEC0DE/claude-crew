#!/bin/bash
# Validation script for claude-crew repository
# Checks: JSON validity, agent frontmatter, broken internal links

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

ERRORS=0

echo "=== Validation Script ==="
echo "Repository: $REPO_ROOT"
echo ""

# Function to report errors
report_error() {
    echo "ERROR: $1"
    ERRORS=$((ERRORS + 1))
}

# ===========================================================
# 1. Validate all JSON files
# ===========================================================
echo "--- Checking JSON files ---"

JSON_FILES=$(find "$REPO_ROOT" -name "*.json" -type f 2>/dev/null)
if [ -z "$JSON_FILES" ]; then
    echo "No JSON files found"
else
    for json_file in $JSON_FILES; do
        if ! jq empty "$json_file" 2>/dev/null; then
            report_error "Invalid JSON: $json_file"
        else
            echo "OK: $json_file"
        fi
    done
fi

echo ""

# ===========================================================
# 2. Validate agent .md files frontmatter
# ===========================================================
echo "--- Checking agent frontmatter ---"

AGENT_DIR="$REPO_ROOT/claudecfg/agents"
if [ -d "$AGENT_DIR" ]; then
    for agent_file in "$AGENT_DIR"/*.md; do
        [ -f "$agent_file" ] || continue

        filename=$(basename "$agent_file")

        # Check if file starts with frontmatter
        if ! head -1 "$agent_file" | grep -q "^---$"; then
            report_error "Missing frontmatter start in $filename"
            continue
        fi

        # Extract frontmatter (between first --- and second ---)
        frontmatter=$(sed -n '/^---$/,/^---$/p' "$agent_file" | tail -n +2 | head -n -1)

        # Check required fields
        for field in "name" "alias" "description" "type"; do
            if ! echo "$frontmatter" | grep -q "^${field}:"; then
                report_error "Missing '$field' in $filename frontmatter"
            fi
        done

        if [ $? -eq 0 ]; then
            echo "OK: $filename"
        fi
    done
else
    echo "Agent directory not found: $AGENT_DIR"
fi

echo ""

# ===========================================================
# 3. Check for broken internal links
# ===========================================================
echo "--- Checking internal links ---"

# Find all markdown files
MD_FILES=$(find "$REPO_ROOT" -name "*.md" -type f 2>/dev/null)

for md_file in $MD_FILES; do
    # Get directory of current file for relative path resolution
    md_dir=$(dirname "$md_file")

    # Match markdown links: [text](path) and reference links: [text][ref]
    # We only check inline links with paths
    while IFS= read -r line; do
        # Extract links: [text](path) - markdown inline links
        while IFS= read -r link; do
            [ -z "$link" ] && continue

            # Skip external URLs
            if [[ "$link" =~ ^https?:// ]]; then
                continue
            fi

            # Skip anchors
            if [[ "$link" =~ ^# ]]; then
                continue
            fi

            # Skip mailto
            if [[ "$link" =~ ^mailto: ]]; then
                continue
            fi

            # Resolve relative path
            if [[ "$link" =~ ^/ ]]; then
                # Absolute from repo root
                target="$REPO_ROOT$link"
            else
                # Relative from current file
                target="$md_dir/$link"
            fi

            # Remove anchor part if present
            target="${target%%#*}"

            # Remove trailing slash
            target="${target%/}"

            # Check if target exists
            if [ ! -e "$target" ]; then
                # Try with .md extension if not found
                if [ ! -e "${target}.md" ]; then
                    report_error "Broken link in $md_file: $link (resolved to: $target)"
                fi
            fi
        done < <(echo "$line" | grep -oP '\]\([^)]+\)' | sed 's/\](\(.*\)/\1/' | tr -d ')' || true)
    done < "$md_file"
done

echo ""

# ===========================================================
# Summary
# ===========================================================
echo "=== Summary ==="
if [ $ERRORS -eq 0 ]; then
    echo "All checks passed!"
    exit 0
else
    echo "Found $ERRORS error(s)"
    exit 1
fi