# Gateway Policy Examples

These are controller-specific examples for wiring the invariant gateway contract:

1. call admission before engine dispatch
2. pass `X-Tenant-ID` and `X-Request-ID`
3. propagate admission metadata (`X-Priority-Class`, `X-Served-Model`)
4. support alias translation either in-controller or through an adapter
5. propagate client cancellation upstream

The examples are **not live proof**. Apply only after replacing placeholders and
checking the selected controller's exact CRD version.
