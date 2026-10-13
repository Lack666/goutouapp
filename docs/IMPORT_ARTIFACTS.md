# Temporary import artifacts — Phase 5D

Current9D supplement: cleanup scans all metadata states through bounded keysets,
locks Job before Artifact, cancels expired/missing-source unfinished Jobs, unlinks
before publishing final metadata, and retries failures/inconsistent terminal states.
Scheduled local execution and actual maintenance process death are tested with9C
physical accounting. Metadata never proves bytes freed. The new operator loop is
opt-in; production monitored scheduling remains NOT DEPLOYED. See
RETENTION_MAINTENANCE and DATA_DELETION_CONTRACT; historical5D sections follow.

`ImportArtifactStore` is the application storage boundary. Its methods cover
create/write stream, open/read stream, stat, delete, exists and expired-orphan
cleanup. `LocalFilesystemImportArtifactStore` is the development and single
server implementation. The configured `CHAT_IMPORT_ARTIFACT_ROOT` is private,
not statically served. A random 32-character hex key determines the path;
the client filename is never used. Keys are validated before any lookup, and
symlink files are refused. An upload writes to a new `.part` file, then becomes
a completed `.bin` file only after flush and close. There is no overwrite API.

PostgreSQL stores only owner, opaque key, format, byte count, SHA-256, state,
creation time and expiry. The Job has a unique, composite owner/artifact
foreign key. No raw transcript is stored in a PostgreSQL blob. The default
limit is 100 MiB and the default retention is 72 hours. Configure
`MAX_CHAT_IMPORT_BYTES`, `CHAT_IMPORT_RETENTION_HOURS` and
`CHAT_IMPORT_ARTIFACT_ROOT` in server settings. File content is read and
written in 64 KiB chunks. A receive guard stops oversized multipart bodies
before Starlette finishes spooling them, with 1 MiB reserved for form framing;
the route enforces the exact file size. Invalid JWT and basic invalid fields are rejected
before creating a server artifact. Oversized, interrupted, empty and fatal
parse uploads delete their partial or completed file and create no Job.

Successful formal import deletes the raw file and marks artifact metadata
`deleted`; Job receipt, provenance hashes and RelationshipMessages remain.
Same-Job replay reads only the durable Job receipt. An exact duplicate ready
Job remains ready under 5C's dataset policy; its own artifact expires normally
unless cancelled. A failed database merge keeps the source for retry and
rolls back all formal rows. Cancel commits the Job transition, then deletes
its file. If deletion fails or the process crashes between DB commit and file
deletion, explicit maintenance retries it.

`ImportWorkflowService.cleanup_expired()` is the maintenance operation.
It cancels jobs whose active artifact has expired, deletes expired and
terminal-job files, and sweeps unreferenced `.bin` and `.part` files older than
one hour. The sweep covers crash windows before artifact metadata commit and
after file deletion failure. Run it periodically from an operator-owned
process; **automatic scheduling is deferred**. A service deployment must use
a private writable root with appropriate OS permissions and durable local
storage for the configured retention window. Multi-instance/object-store
deployment is deferred.

Run one cleanup pass from the repository root with the same server settings:

```powershell
uv --cache-dir .cache/uv --no-managed-python run --locked --env-file .env python apps/server/import_artifact_cleanup.py
```

It prints counts only. Do not point it at a different server's artifact root.

The 5C staging table is PostgreSQL `TEMP ... ON COMMIT DROP`, created and
filled inside the same merge transaction. Success or exception ends that
transaction and removes staging rows; a process crash closes the connection.
Cancelling a ready Job has no staging rows to clean. Artifact maintenance
does not alter formal RelationshipMessages. Ordinary logs never include raw
source, multipart body, token or speaker inventory. See
[ADR 0025](adr/0025-import-artifact-api.md).
