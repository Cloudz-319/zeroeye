# Dashboard Diagnostic Payload Manual Check

This check covers the build dashboard malformed-payload fallback for issue #2.

1. Start the frontend with a mocked `/api/v1/dashboard/stats` response that omits a required numeric field, for example `{"totalUsers": 10}`.
2. Open the dashboard route.
3. Confirm the page renders `Dashboard diagnostics are unavailable because the payload is malformed.` instead of a blank screen or thrown React error.
4. Change the mocked response to include all required numeric fields: `totalUsers`, `activeSessions`, `trialsCompleted`, `avgResponseTime`, `errorRate`, and `uptime`.
5. Reload the dashboard and confirm the stat cards render the same labels and values as before.
