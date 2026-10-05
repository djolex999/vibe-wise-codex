# Development

The skill is self-contained: scripts import only siblings and the standard library;
references and the original MIT notice travel with a standalone install. Keep
`.codex-plugin/plugin.json` consistent with README installation and skill naming.
Python helpers preserve the upstream lookup and reset semantics. Do not introduce
Claude-specific environment variables, lifecycle payloads, or tool names.

Run `python3 -B -m unittest discover -s tests -v` from the repository root. The reset
suite retains upstream behavioral coverage; context tests exercise the actual CLI.
Packaging tests copy the skill outside the repository and run both helpers there.

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

Reset requires exclusive use of the notes by convention. Fingerprints detect changes
before replacement, not arbitrary concurrent writers after the final check. Each
note replacement is atomic but the three-file reset is not transactional. Keep
complete backups and report partial failures rather than claiming rollback.
