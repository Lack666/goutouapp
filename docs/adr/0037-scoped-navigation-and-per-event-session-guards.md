# ADR 0037: scoped navigation and per-event session guards

Accepted for Phase 9B, 2026-10-13. Import History and Memory cursors previously
represented positions without a scope. SQL remained owner-filtered, so this was
not an observed cross-owner disclosure. Malformed Memory UUID components could
also escape as AttributeError/500. Transport checked session epochs around a
whole SSE response; controllers separately cancelled/guarded callbacks, but the
transport itself could deliver a late callback before rejecting the response.

Keep existing services, query ordering and public DTOs. Version the two opaque
cursors at v2 and bind them to a SHA-256 digest of owner/domain and exact optional
Person/Relationship filters. Require typed components and finite bounded input;
legacy/mismatched cursors return the existing invalid-cursor response. Refresh
obtains a new cursor. The digest is navigation consistency, not authentication
or integrity protection: independently owned queries remain the authority.
There is no fixed-snapshot guarantee. Resource/Agent cursors already bind scope.

Check the captured session epoch before every accepted transport SSE callback,
in addition to existing cancellation/controller guards. Reject stale events and
clean up the reader. No durable pending-operation store or replay policy changes.

Application logging accepts only reviewed fixed event descriptions and strips
arguments, exception/stack data and extra fields. Keep Uvicorn access disabled
and its exception filter. No raw-message observability or new infrastructure.

Evidence: test_authorization_security.py, test_privacy_logging.py and
Mobile authPrivacy.test.ts, retained controller/native and full root gates.
