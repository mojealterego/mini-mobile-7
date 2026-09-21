# Project-72 Backup and Recovery

## Scope

The canonical subscriber database, durable idempotency database and optional eSIM metadata database are separate persistence domains. Backups must preserve them independently. External secret stores are not backed up by this repository procedure.

## Backup

Run on the private management host:

```bash
export MM7_MONGODB_URI='mongodb://...'
export MM7_IDEMPOTENCY_DB_URI='mongodb://...'
# Only when eSIM metadata uses a separate database:
export MM7_ESIM_DB_URI='mongodb://...'
bash scripts/project-72-backup.sh /secure/backup/mm7-$(date -u +%Y%m%dT%H%M%SZ)
```

The backup script:

- requires both canonical and idempotency URIs;
- refuses remote MongoDB unless `MM7_BACKUP_ALLOW_REMOTE=1` is explicitly set;
- creates restricted backup directories/files;
- produces SHA-256 checksums;
- excludes raw authentication material, private keys and external secret-store contents;
- records a manifest identifying the backup domains.

Do not place production URIs containing credentials in shell history or documentation. Prefer a protected service environment or secret manager.

## Restore acceptance

Restore into an isolated MongoDB instance, never directly over the production database on the first pass.

1. Restore the canonical archive.
2. Restore the idempotency archive separately.
3. Restore eSIM metadata only when that domain is configured.
4. Verify MongoDB connectivity and expected database/collection names.
5. Verify unique indexes for canonical `subscriber_id` and `imsi`.
6. Verify canonical schema/version fields and the deterministic seven-subscriber catalog.
7. Verify idempotency records retain their request fingerprint and terminal result semantics.
8. Verify eSIM metadata contains no raw activation URI or matching ID.
9. Run `make assurance-test` against the isolated restored environment where integration configuration permits.
10. Perform authoritative Open5GS readback only after the restored canonical state is approved for the target deployment.

A backup restore is not evidence of live telecom operation. `VERIFIED` remains dependent on the normal authorization, execution, authoritative readback and postcondition chain.

## Recovery rule

Never resolve an uncertain telecom side effect by blindly replaying the operation. Use the durable idempotency record and authoritative target readback first. A reservation without a terminal result remains fail-closed by design.

If a projection and canonical state disagree, classify drift and use a separately authorized repair operation if one is later implemented. Do not silently overwrite canonical state from the projection.

## Evidence

For each accepted backup/restore test retain:

- UTC timestamp;
- backup manifest and checksums;
- isolated MongoDB version;
- collection/index validation output;
- assurance-test result;
- operator/change reference;
- final disposition.

Do not store secret values in the evidence bundle.
