# Dashboard malformed diagnostic validation

Manual validation for the build dashboard error-boundary change:

1. Start the frontend with `npm run dev`.
2. Force `useDashboardStats()` to return a malformed payload such as `null`, an array, or `{ totalUsers: { bad: true } }`.
3. Open the dashboard route.
4. Expected result: the page renders `Dashboard data is malformed and could not be rendered safely.` inside an alert instead of crashing the whole React view.
5. Restore a normal stats object and confirm the existing statistic cards render unchanged.

This check intentionally verifies that raw diagnostic payload content is not dumped into the fallback UI.
