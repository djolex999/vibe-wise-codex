# Reset learning notes

Run only for an explicit reset request, using the current project's absolute cwd
and this skill's installed directory. Safely quote paths and tokens.

1. Preview without writing:
   `python3 <skill-directory>/scripts/reset.py --cwd <absolute-project-cwd>`.
   If `no_notes`, explain there is nothing to reset. On an error, report and stop;
   do not improvise deletion or switch projects.
2. Show the preview's project/state paths, files, and backup destination. Ask in
   chat whether to reset those learning notes or cancel, unless the user already
   explicitly confirmed that exact preview. Wait for an explicit reply. Invoking
   the skill or granting tool permissions alone is not reset confirmation.
3. After confirmation, rerun with the same cwd and
   `--confirm <preview-confirmation-token>`. If notes or target changed, obtain a
   fresh preview and confirmation. Do not reuse the stale token.
4. On `reset`, report the backup path and restart minimal onboarding. Preserve
   source code. Discard previous learning preferences, mastery, and pending choices;
   rebuild the map from actual code. On failure, report the backup path if provided
   and inspect active notes before continuing; never claim reset completed.

Backups contain the original profile, progress, and map. The helper prepares all
backups first and replaces each note atomically, but the three-file reset is not a
transaction. A replacement failure can leave partial fresh state; retain the backup.
Do not reset while another session edits the same notes. The fingerprint detects
changes before replacement but cannot lock out arbitrary external writers.
