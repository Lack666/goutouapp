# Privacy logging policy — Phase 9B

Application output whitelist: logger name, severity and reviewed fixed event.
Approved messages: `Unhandled server error`; `Import artifact cleanup deferred;
maintenance retry required`. Unknown/parameterized messages become `Server event
details suppressed`. Arguments, exception text/info, stack info and extra fields
are stripped before application handlers. No request/private metadata is added.

Uvicorn access logging remains disabled; its exception/stack filter removes
private details before formatting. Startup/stop diagnostics remain. SQLAlchemy
uses hide_parameters and no echo. Arbitrary third-party loggers, operator
debuggers and external collectors are not universally sanitized. Production
collectors/retention/rotation, key custody and OS ACLs remain deployment work.

Future metrics may use separately reviewed closed event enums, HTTP status,
latency buckets, random request correlation IDs and limit counts. Business IDs,
operation keys and token hashes are unsuitable correlations. These extra fields
are design allowances, not currently implemented telemetry.

Never record Authorization/JWT/API keys, chat/Memory content, import bytes or
private filenames/paths, prompts or SQL/stack sensitive parameters. Fixed error
envelopes omit validation input/HTTP detail; generic500 logs fixed text. Mobile
discards raw errors in favor of allowlisted codes/IDs and fixed messages. Session
snapshots omit tokens. SecureStore credentials stay out of EXPO_PUBLIC variables,
bundle assets, logs, dialogs, screenshots and automatic traces.

Agent REST/SSE failure codes omit provider arguments and input prompts. ENOSPC
at artifact begin currently yields generic500, with no Job/completed artifact;
this is not a disk-alert system. A real bounded exhausted DB pool yields503
without SQL/pool internals. Fault tests do not prove aggregate resilience (R-07).

Native helper credentials stay in anonymous pipes and protected input. Its
private subprocess wrapper suppresses args/stdout/stderr/chained errors for
timeouts, process and OS failures. New9B fake secret markers are generated at
runtime and never stored in Git; tests examine Python traceback and PowerShell/
native failure formatting. Smoke captures no screenshot or credential trace.
Native UI evidence contains deliberate synthetic fixture text and is not a
production logging schema. Real user inputs require a separate helper review.

Coverage: test_privacy_logging.py, retained real-socket Uvicorn/SQL/upload tests,
test_security_9b_tooling.py, Mobile error/session suites, read-only evidence scan
and the separately documented manual review.
