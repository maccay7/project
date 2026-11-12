#!/usr/bin/env bash
# Fails if test-only branches or debug artifacts leak into production code.
set -euo pipefail
cd "$(dirname "$0")/.."
fail=0

# 1. NODE_ENV test branches outside test files
if grep -rn "NODE_ENV.*['\"]test['\"]" frontend/src --include='*.js' --include='*.vue' --include='*.ts' \
    | grep -v '__tests__\|\.test\.\|\.spec\.'; then
  echo "FAIL: NODE_ENV test branch in production src"; fail=1
fi

# 2. debugger statements
if grep -rn "debugger;" frontend/src backend --include='*.js' --include='*.vue' --include='*.py'; then
  echo "FAIL: debugger statement found"; fail=1
fi

# 3. Hardcoded portfolio constants in production code
if grep -rEn "497376|374387\.64" frontend/src backend --include='*.js' --include='*.vue' --include='*.py' \
    | grep -v '__tests__\|\.test\.\|\.spec\.'; then
  echo "FAIL: hardcoded workbook value in production code"; fail=1
fi

# 4. Trace/debug print markers
if grep -rn "RATE-TRACE\|BENCHMARK-TRACE" backend frontend/src 2>/dev/null | grep -v pycache; then
  echo "FAIL: leftover trace logging"; fail=1
fi

if [ "$fail" -eq 0 ]; then echo "audit_production: clean"; fi
exit "$fail"
