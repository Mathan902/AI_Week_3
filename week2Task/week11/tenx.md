**At 10× (20 req/min at today's busiest minute), nothing breaks. Latency breaks first, at about 46×: the 6-worker pool tops out at 6 / 3.9 s mean generation ≈ 92 req/min (measured: 84 req/min sustained, p99 7.6 s, in the traffic replay). The rate limit is at 2% (20 of 1,000 RPM, Haiku 5.5 Start tier), and cost at 10× is $5.30/month against a $500 Start-tier spend cap.**

---

The numbers behind the line:

- **Today's volume** (`week11_logq.py stages`): 700 queries over 15.8 days = 44.2/day; busiest day 63, busiest hour 10, busiest minute 2. 10× means 442/day and 20 req/min at peak.
- **Latency.** The traffic replay ran 700 real requests in 8 min 19 s with 6 workers, which is 84 req/min sustained, at generation p50 3.9 s / p99 7.6 s. That's already 4× the 10× peak, so 10× doesn't move p99. Capacity is about 6 workers / 3.9 s ≈ 92 req/min, or 46× today's busiest minute; past that, requests queue and p99 grows without bound. The busiest-minute figure (2) comes from a small sample, so real bursts at 10× could be several times 20 req/min, and that only brings the latency wall closer.
- **Rate limit** (Haiku 5.5, Start tier, platform.claude.com/docs/en/api/rate-limits): 1,000 RPM / 2,000,000 ITPM / 400,000 OTPM. Cache reads don't count toward ITPM. 10× peak with v4's 1,720 input / 247 output tokens, worst case all uncached, is 20 RPM (2%), 34,400 ITPM (1.7%) and 4,940 OTPM (1.2%).
- **Cost.** v4 measures $0.000399/query × 442/day = $0.18/day = $5.30/month, about 1% of the $500 monthly Start-tier cap.
- **Caveat.** Production here calls the model through the `claude` CLI, so each request pays about 1.5 s of process start-up (generation 3,427 ms vs API 1,968 ms on the incident trace). Moving generation to the Anthropic SDK in-process would cut mean latency and push the latency wall further out. Rate limit and cost would then be the next limits, at roughly 500× (1,000 / 2 RPM) and 940× ($500 / $0.53 a month) today.
