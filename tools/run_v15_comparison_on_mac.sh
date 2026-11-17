#!/bin/bash
# Native inference only. The frozen Python client runs in WSL over an SSH tunnel.
set -eu
root="$(cd "$(dirname "$0")" && pwd)"
if [ "$(uname -sm)" != 'Darwin arm64' ]; then exit 2; fi
if /usr/sbin/lsof -nP -iTCP:8081 -sTCP:LISTEN >/dev/null 2>&1; then
  echo 'STOP: Port 8081 occupied; existing service preserved.' >&2; exit 1
fi
mkdir -p "$root/runtime"
(set -C; date -u > "$root/runtime/invocation-started.txt")
printf '%s\n' "$$" > "$root/runtime/launcher.pid"
server_pid=''
finish() {
  status=$?
  trap - EXIT
  stopped=true
  if [ -n "$server_pid" ] && kill -0 "$server_pid" 2>/dev/null; then
    parent="$(/bin/ps -o ppid= -p "$server_pid" | /usr/bin/tr -d ' ')"
    if [ "$parent" = "$$" ]; then
      kill -TERM "$server_pid"
      for ((check=0; check<30; check++)); do
        if ! kill -0 "$server_pid" 2>/dev/null; then break; fi
        sleep 1
      done
      if kill -0 "$server_pid" 2>/dev/null; then
        parent="$(/bin/ps -o ppid= -p "$server_pid" | /usr/bin/tr -d ' ')"
        if [ "$parent" = "$$" ]; then kill -KILL "$server_pid"; else stopped=false; status=1; fi
      fi
      wait "$server_pid" 2>/dev/null || :
    else stopped=false; status=1
    fi
  fi
  printf '{"run_exit_code":%s,"owned_server_stopped":%s}\n' "$status" "$stopped" > "$root/runtime/owned-server-status.json"
  exit "$status"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP
/opt/homebrew/bin/llama-server --model /Users/chadjosewski/Models/MP1/Qwen3.5-122B-A10B-Q4_K_M/Qwen_Qwen3.5-122B-A10B-Q4_K_M-00001-of-00002.gguf \
  --host 127.0.0.1 --port 8081 --ctx-size 16384 --parallel 1 \
  --reasoning on --reasoning-format deepseek --reasoning-budget 4096 \
  > "$root/runtime/server.log" 2>&1 &
server_pid=$!
printf '%s\n' "$server_pid" > "$root/runtime/owned-server.pid"
for ((check=0; check<2880; check++)); do
  if [ -f "$root/STOP" ]; then exit 0; fi
  if ! kill -0 "$server_pid" 2>/dev/null; then exit 1; fi
  sleep 5
done
echo 'Four-hour maximum server lifetime reached.' >&2
exit 1
