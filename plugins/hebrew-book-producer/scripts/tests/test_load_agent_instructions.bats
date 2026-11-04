#!/usr/bin/env bats
# Tests for load-agent-instructions.sh.

setup() {
  TMP="$(mktemp -d)"
  cd "${TMP}"
  REPO="$(cd "${BATS_TEST_DIRNAME}/../../../.." && pwd)"
  LOADER="${REPO}/plugins/hebrew-book-producer/scripts/load-agent-instructions.sh"
  mkdir -p .ctx
}

teardown() {
  rm -rf "${TMP}"
}

@test "no book.yaml: warns and exits 0" {
  run bash "${LOADER}" lector_reader
  [ "${status}" -eq 0 ]
  [[ "${output}" == *"no book.yaml"* ]] || [[ "${output}" == *"skipping"* ]]
}

@test "book.yaml without agent_instructions: warns and exits 0" {
  printf 'genre: philosophy\n' > book.yaml
  run bash "${LOADER}" lector_reader
  [ "${status}" -eq 0 ]
  [[ "${output}" == *"skipping"* ]] || [[ "${output}" == *"no agent_instructions"* ]]
}

@test "cached file present: skips fetch (idempotent)" {
  printf 'agent_instructions:\n  lector_reader: "cmDOESNOTEXIST"\n' > book.yaml
  printf 'cached content\n' > .ctx/lector-reader-instructions.md
  before_mtime=$(stat -f %m .ctx/lector-reader-instructions.md 2>/dev/null || stat -c %Y .ctx/lector-reader-instructions.md)
  run bash "${LOADER}" lector_reader
  [ "${status}" -eq 0 ]
  after_mtime=$(stat -f %m .ctx/lector-reader-instructions.md 2>/dev/null || stat -c %Y .ctx/lector-reader-instructions.md)
  [ "${before_mtime}" -eq "${after_mtime}" ]
}

@test "valid id: fetches from Trove and caches" {
  command -v trove >/dev/null 2>&1 || skip "trove CLI not installed"
  # Use a real Trove ID — the writer's guide.
  printf 'agent_instructions:\n  test_role: "cmok9h0m10ahik30zt8yt0lt2"\n' > book.yaml
  run bash "${LOADER}" test_role
  [ "${status}" -eq 0 ]
  [ -s .ctx/test-role-instructions.md ]
  size=$(wc -c < .ctx/test-role-instructions.md)
  [ "${size}" -gt 100 ]
}
