#!/bin/bash
# Copy beside project/ in the frozen paired prompt bundle, then invoke with bash.
set -eu
root="$(cd "$(dirname "$0")" && pwd)"
if [ "$(uname -sm)" != 'Darwin arm64' ]; then exit 2; fi
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export UV_PROJECT_ENVIRONMENT="$HOME/.local/share/aia-mp1-tools/qwen35-v14-comparison-v1-venv"
cd "$root/project"
uv sync --locked
uv run --locked python tools/v14_comparison.py verify "$root"
if /usr/sbin/lsof -nP -iTCP:8081 -sTCP:LISTEN >/dev/null 2>&1; then
  printf '%s\n' 'STOP: Port 8081 occupied; existing service preserved.' >&2
  exit 1
fi
mkdir -p "$root/runtime"
(set -C; printf '%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$root/runtime/invocation-started.txt")
model="$(uv run --locked python -c 'import json,sys; print(json.load(open(sys.argv[1]))["models"][0]["model"])' "$root/plan.json")"
printf '%s\n' "$$" > "$root/runtime/launcher.pid"
server_pid=''
server_started=false
finish() {
  status=$?
  trap - EXIT
  stopped=true
  if [ -n "$server_pid" ]; then
    if kill -0 "$server_pid" 2>/dev/null; then
      parent="$(/bin/ps -o ppid= -p "$server_pid" | /usr/bin/tr -d ' ')"
      if [ "$parent" = "$$" ]; then
        kill -TERM "$server_pid" 2>/dev/null || :
        for ((check=0; check<30; check++)); do
          if ! kill -0 "$server_pid" 2>/dev/null; then break; fi
          sleep 1
        done
        if kill -0 "$server_pid" 2>/dev/null; then
          parent="$(/bin/ps -o ppid= -p "$server_pid" | /usr/bin/tr -d ' ')"
          if [ "$parent" = "$$" ]; then
            kill -KILL "$server_pid" 2>/dev/null || :
          else
            stopped=false
            status=1
          fi
        fi
        wait "$server_pid" 2>/dev/null || :
        if kill -0 "$server_pid" 2>/dev/null; then stopped=false; status=1; fi
      else
        stopped=false
        status=1
      fi
    else
      wait "$server_pid" 2>/dev/null || :
    fi
  fi
  printf '{"run_exit_code":%s,"owned_server_started":%s,"owned_server_stopped":%s}\n' \
    "$status" "$server_started" "$stopped" > "$root/runtime/owned-server-status.json"
  exit "$status"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP
/opt/homebrew/bin/llama-server --model "$model" --host 127.0.0.1 --port 8081 \
  --ctx-size 16384 --parallel 1 --reasoning on --reasoning-format deepseek --reasoning-budget 4096 \
  > "$root/runtime/server.log" 2>&1 &
server_pid=$!
server_started=true
printf '%s\n' "$server_pid" > "$root/runtime/owned-server.pid"
ready=0
for ((check=0; check<120; check++)); do
  if ! kill -0 "$server_pid" 2>/dev/null; then exit 1; fi
  if /usr/bin/curl --fail --silent --max-time 2 http://127.0.0.1:8081/health >/dev/null; then
    ready=1; break
  fi
  sleep 2
done
if [ "$ready" -ne 1 ]; then exit 1; fi
uv run --locked python tools/v14_comparison.py execute "$root"
