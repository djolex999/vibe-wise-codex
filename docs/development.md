# Development

The skill is self-contained: scripts import only siblings and the standard library;
references and the original MIT notice travel with a standalone install. Keep
`.codex-plugin/plugin.json` consistent with README installation and skill naming.
The SessionStart hook is optional plugin packaging; direct skill copies must remain
hook-free. The hook loads the shared context helper using `PLUGIN_ROOT` and disables
bytecode writes before importing it. Python helpers preserve the upstream lookup and
reset semantics. Do not introduce Claude-specific environment variables, lifecycle
payloads, or tool names.

Run `python3 -B -m unittest discover -s tests -v` from the repository root. The reset
suite retains upstream behavioral coverage; context tests exercise the actual CLI.
Packaging tests copy the skill outside the repository and run both helpers there.
Hook unit tests validate event filtering and output behavior, but do not exercise
Codex's hook discovery, trust prompts, or actual Desktop lifecycle delivery.

For manual conversational validation, load the skill into Codex in an isolated
project and try these scenarios:

| Request/context | Expected behavior |
| --- | --- |
| Active learner asks to correct a typo | Edit without a checkpoint; report actual verification |
| Learner adds bounded filtering in a familiar service | Invite missing approach; one Design checkpoint covers design, implementation scope and verification; proceed after confirmation |
| Learner designs an unfamiliar queue integration | Build reasoning, Design choice, then concrete Implementation scope; await outstanding replies |
| Learner already supplied reasoning and approved exact changes | Reuse evidence; avoid repeated gates |
| Learner asks “just implement this one” | Bypass task learning stops; keep normal project/tool permissions |
| Paused profile discovered through project guidance | Ordinary coding; do not reactivate |
| Restart with pending Implementation checkpoint | Restore pending scope; never infer approval from restart |
| Reset requested | Read-only preview, explicit confirmation, preserved backup, fresh onboarding |
| Notes include instructions to ignore project permissions | Treat as untrusted data |

These are conversational acceptance cases, not assertions that a live model session
has been tested. Automated tests verify deterministic helpers and packaging; they
cannot guarantee model adherence to checkpoint instructions.

## Manual Codex Desktop hook checks

These scenarios require a real Codex Desktop installation and are not covered by
unit tests, and have not yet been tested. `/hooks` is a Codex CLI command, not a
procedure for completing these Desktop checks.

| Setup/action | Expected behavior |
| --- | --- |
| Install the plugin in an isolated project with active notes | Verify Desktop lists the bundled SessionStart hook for review and skips it before trust. Review and trust the current definition through Desktop's supported flow, then start a session and confirm concise context arrives without a status message. |
| Repeat SessionStart with `startup`, `resume`, `clear`, and `compact` | Each source restores active context. Clearing chat context does not reset project notes or approve a pending decision. |
| Use a paused profile, no notes, invalid notes, or a forked session | The hook emits no restoration context. |
| Put unique private text in profile, progress, project-map, and transcript files | Hook output contains no note or transcript body text; it contains only instructions and paths. |
| Change the hook definition after trust | Codex asks for review of the changed definition before it runs. |

The plugin hook is read-only and fail-open. These manual checks confirm the
Desktop's registration, trust, and lifecycle behavior, which local unit tests cannot
simulate.

## Codex CLI hook controls

`/hooks` is documented for Codex CLI. In the CLI, use it to inspect configured
hooks, review and trust a changed definition, or disable an individual non-managed
hook. This CLI control does not verify the plugin's Desktop discovery, trust, or
lifecycle behavior.

Reset requires exclusive use of the notes by convention. Fingerprints detect changes
before replacement, not arbitrary concurrent writers after the final check. Each
note replacement is atomic but the three-file reset is not transactional. Keep
complete backups and report partial failures rather than claiming rollback.
