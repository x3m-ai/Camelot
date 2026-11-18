# Install a Morgana Agent

Use the canonical procedure in the [Morgana manual — Deploy a Windows Agent](../../morgana/README.md#82-deploy-a-windows-agent).

1. Open Morgana and go to **Agents → + Deploy Agent**.
2. Copy the generated Windows command.
3. Run it as Administrator on the authorized target.
4. Confirm the `MorganaAgent` service and the Agent row in Morgana.

The command uses `https://<SERVER_HOST>:8888` and a Morgana API key. Do not reuse a concrete lab IP, and do not share the key. The current release has no per-agent approval queue and does not validate the server certificate; use only on a trusted exercise network.