# [T2] TCP half-open mitigation

Tune Envoy HTTP/2 PING and TCP keepalives to detect silent client disconnects in <5s.

**Owner:** Platform / edge  
**Validation:** `generated_vs_delivered_tokens` waste metric drops under synthetic disconnect load
