#!/bin/bash
# Dedicated Mac Qwen server for the source-free paired control. No Herd edits.
set -euo pipefail
root="$1"
model=/Users/chadjosewski/Models/MP1/Qwen3.5-122B-A10B-Q4_K_M/Qwen_Qwen3.5-122B-A10B-Q4_K_M-00001-of-00002.gguf
if [ "$(uname -sm)" != 'Darwin arm64' ]; then exit 2; fi
if /usr/sbin/lsof -nP -iTCP:8082 -sTCP:LISTEN >/dev/null 2>&1; then
  echo 'STOP: Dedicated port 8082 is occupied.' >&2
  exit 1
fi
mkdir -p "$root"
(set -C; printf '%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$root/started.txt")
printf '%s\n' "$$" > "$root/launcher.pid"
server_pid=''
finish() {
  status=$?
  trap - EXIT
  if [ -n "$server_pid" ] && kill -0 "$server_pid" 2>/dev/null; then
    parent="$(/bin/ps -o ppid= -p "$server_pid" | /usr/bin/tr -d ' ')"
    if [ "$parent" = "$$" ]; then
      kill -TERM "$server_pid" 2>/dev/null || :
      for ((attempt=0; attempt<30; attempt++)); do
        if ! kill -0 "$server_pid" 2>/dev/null; then break; fi
        sleep 1
      done
      if kill -0 "$server_pid" 2>/dev/null; then
        parent="$(/bin/ps -o ppid= -p "$server_pid" | /usr/bin/tr -d ' ')"
        if [ "$parent" = "$$" ]; then kill -KILL "$server_pid" 2>/dev/null || :; else status=1; fi
      fi
      wait "$server_pid" 2>/dev/null || :
    else
      status=1
    fi
  fi
  printf '{"exit_code":%s,"server_pid":"%s"}\n' "$status" "$server_pid" > "$root/stopped.json"
  exit "$status"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
/opt/homebrew/bin/llama-server --model "$model" \
  --host 127.0.0.1 --port 8082 --ctx-size 16384 --parallel 1 \
  --reasoning on --reasoning-format deepseek --reasoning-budget 4096 \
  > "$root/server.log" 2>&1 &
server_pid=$!
printf '%s\n' "$server_pid" > "$root/server.pid"
for ((check=0; check<3600; check++)); do
  if [ -f "$root/STOP" ]; then exit 0; fi
  if ! kill -0 "$server_pid" 2>/dev/null; then exit 1; fi
  sleep 5
done
echo 'Five-hour maximum server lifetime reached.' >&2
exit 1
