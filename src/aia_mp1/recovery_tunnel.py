"""Read-only ownership contract for the Windows SSH forwarding process."""

from urllib.parse import urlsplit

from .recovery_process import preflight_owned


def observe_tunnel(experiment, read_windows):
    """Compare OS process/listener facts from a trusted Windows observation."""
    policy = experiment["transport_policy"]
    tunnel = experiment.get("owned_tunnel")
    if not isinstance(tunnel, dict) or set(tunnel) != {
        "ssh_executable",
        "ssh_host_alias",
        "ssh_destination",
        "local_port",
        "remote_port",
    }:
        raise ValueError("frozen tunnel identity is required")
    endpoint = urlsplit(policy["endpoint"])
    if (
        endpoint.scheme != "http"
        or endpoint.hostname != "127.0.0.1"
        or endpoint.port != tunnel["local_port"]
        or endpoint.path != "/v1"
        or endpoint.username
        or endpoint.password
        or endpoint.query
        or endpoint.fragment
        or tunnel["remote_port"] != experiment["owned_process"]["port"]
        or any(
            type(tunnel[name]) is not int or not 1 <= tunnel[name] <= 65535
            for name in ("local_port", "remote_port")
        )
        or any(
            not isinstance(tunnel[name], str) or not tunnel[name].strip()
            for name in ("ssh_executable", "ssh_host_alias", "ssh_destination")
        )
    ):
        raise ValueError("tunnel endpoint does not match frozen ports and destination")
    observation = read_windows(tunnel)
    if not isinstance(observation, dict) or set(observation) != {
        "pid",
        "listener_pid",
        "executable",
        "argv",
        "started",
    }:
        raise ValueError("Windows process observation is incomplete")
    argv = observation["argv"]
    expected_forward = f"127.0.0.1:{tunnel['local_port']}:127.0.0.1:{tunnel['remote_port']}"
    if (
        type(observation["pid"]) is not int
        or observation["pid"] <= 1
        or observation["listener_pid"] != observation["pid"]
        or observation["executable"] != tunnel["ssh_executable"]
        or not isinstance(argv, list)
        or argv.count("-L") != 1
        or argv[argv.index("-L") + 1 : argv.index("-L") + 2] != [expected_forward]
        or argv.count("-o") < 2
        or "BatchMode=yes" not in argv
        or f"HostKeyAlias={tunnel['ssh_host_alias']}" not in argv
        or argv[-1] != tunnel["ssh_destination"]
        or not isinstance(observation["started"], str)
        or not observation["started"].strip()
    ):
        raise ValueError("SSH tunnel owner, forwarding or destination differs")
    return observation


def preflight_with_tunnel(ledger, packet_root, key, read_remote, read_windows, *, transport=None):
    """Bracket the Mac and HTTP preflight with the same owned Windows tunnel."""
    manifest, _, _, head = ledger.read()
    before = observe_tunnel(manifest["experiment"], read_windows)
    result = preflight_owned(ledger, packet_root, key, read_remote, transport=transport)
    after = observe_tunnel(manifest["experiment"], read_windows)
    if before != after or ledger.read()[3] != head:
        raise ValueError("SSH tunnel or journal changed across preflight")
    return {**result, "owned_tunnel": before}
