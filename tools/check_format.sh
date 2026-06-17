#!/bin/bash
# check_format.sh - Verify all files match .editorconfig settings
# Added to diagnostic build pipeline per issue #58

set -e

EDITORCONFIG=".editorconfig"
VIOLATIONS=0

if [ ! -f "$EDITORCONFIG" ]; then
    echo "ERROR: .editorconfig not found"
    exit 1
fi

check_file() {
    local file="$1"
    local indent_style="$2"
    local indent_size="$3"

    if [ ! -f "$file" ]; then
        return
    fi

    # Check for mixed tabs/spaces
    if [ "$indent_style" = "space" ]; then
        if grep -P "^\t" "$file" > /dev/null 2>&1; then
            echo "VIOLATION: $file has tabs but should use spaces"
            VIOLATIONS=$((VIOLATIONS + 1))
        fi
    elif [ "$indent_style" = "tab" ]; then
        if grep -P "^    " "$file" > /dev/null 2>&1; then
            echo "VIOLATION: $file has spaces but should use tabs"
            VIOLATIONS=$((VIOLATIONS + 1))
        fi
    fi

    # Check for trailing whitespace
    if grep -P " +$" "$file" > /dev/null 2>&1; then
        echo "VIOLATION: $file has trailing whitespace"
        VIOLATIONS=$((VIOLATIONS + 1))
    fi

    # Check for missing final newline
    if [ -s "$file" ] && [ "$(tail -c 1 "$file" | wc -l)" -eq 0 ]; then
        echo "VIOLATION: $file missing final newline"
        VIOLATIONS=$((VIOLATIONS + 1))
    fi
}

echo "Checking .editorconfig compliance..."

# Python files
for f in $(find . -name "*.py" -not -path "./.git/*" -not -path "./node_modules/*" 2>/dev/null); do
    check_file "$f" "space" 4
done

# TypeScript/JavaScript files
for f in $(find . -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" 2>/dev/null | grep -v node_modules | grep -v .git); do
    check_file "$f" "space" 2
done

# Go files
for f in $(find . -name "*.go" -not -path "./.git/*" 2>/dev/null); do
    check_file "$f" "tab" 4
done

# C/H files
for f in $(find . -name "*.c" -o -name "*.h" 2>/dev/null | grep -v .git); do
    check_file "$f" "tab" 4
done

# Java files
for f in $(find . -name "*.java" -not -path "./.git/*" 2>/dev/null); do
    check_file "$f" "space" 4
done

# Shell scripts
for f in $(find . -name "*.sh" -o -name "*.bash" 2>/dev/null | grep -v .git); do
    check_file "$f" "tab" 4
done

# Lua files
for f in $(find . -name "*.lua" -not -path "./.git/*" 2>/dev/null); do
    check_file "$f" "tab" 4
done

if [ $VIOLATIONS -gt 0 ]; then
    echo ""
    echo "Found $VIOLATIONS formatting violations"
    exit 1
else
    echo "All files match .editorconfig settings"
    exit 0
fi
