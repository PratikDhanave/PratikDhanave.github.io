# Integration and Deployment in Customer Environments

*The demo ran on your laptop with clean data — production means the customer's messy systems, their security rules, and their data as it actually is, which is where most forward deployed work is really won.*

Between a prototype the customer loves (post 3) and a solution they can rely on lies the least glamorous and most decisive stretch of forward deployed work: making it run in *their* environment, against *their* data, under *their* constraints. This is where "it worked in the demo" meets reality. Handle it well and you become indispensable; handle it naively and the goodwill you earned evaporates in a string of incidents.

## The data is worse than they told you

Every FDE learns this the hard way: the sample data you prototyped on was the clean version. Production data has missing fields, inconsistent formats, duplicate records, values that violate the schema, timezone chaos, encodings from the 1990s, and a "miscellaneous" category that turns out to hold 30% of the rows. The customer often doesn't know how messy their own data is — the mess lives in the workarounds their people apply by hand.

- **Profile the real data early.** Before you promise anything, run the actual dataset through a profiling pass — null rates, distinct values, format variance, outliers. Surprises found now are cheap.
- **Design for dirtiness.** Validate at the boundary, quarantine bad records instead of crashing, and make the failure *visible* (a rejects report) rather than silent.
- **Get the edge cases from the humans.** The analyst who's been doing this by hand knows every exception. That knowledge is the spec for your data handling.

**The gotcha:** prototyping on a hand-cleaned sample hides the real work — the 20% of records that don't fit the happy path is where 80% of the deployment effort goes. Profile production data before you estimate.

## Integration: you don't control the systems

An FDE almost never gets to build on a greenfield. You integrate with the customer's existing systems — a legacy database you can only read, an ERP with an idiosyncratic API, a file drop on an SFTP server, a system whose "API" is a nightly CSV export. You adapt to them, not the other way around.

- **Discover the real interfaces.** The documented API and the working API differ; the actual integration path is often "talk to the one engineer who knows how the export really works."
- **Prefer loose coupling.** Read from a replica, consume a file, subscribe to an event — anything that doesn't require the customer to change a system they can't or won't touch.
- **Expect rate limits, downtime, and change.** Their systems weren't built for your load, and they'll change without telling you. Build defensively: retries, backoff, idempotency, and monitoring so you learn about a broken feed before the customer does.

## Security and compliance are non-negotiable

In a customer environment, security is not a feature you add later — it's a gate you pass or you don't deploy at all. Data residency ("this data cannot leave our region/our tenant"), access controls, audit logging, encryption, approved-vendor lists, and change-management processes are real walls. The FDE who designed a slick solution that sends data to an unapproved external service has built something that can never go live. Learn these constraints during discovery (post 2), design within them, and involve the customer's security team *early* — they can be your ally or your veto.

**The gotcha:** a technically perfect solution that violates a security or data-residency rule is worth zero — it will never be deployed. Treat the customer's security team as a stakeholder to engage in week one, not an obstacle to route around at go-live.

## Deployment: where it runs and who runs it

Where the solution lives shapes everything: their cloud, their on-prem servers, an air-gapped network, your platform accessed remotely. Each has different constraints on tooling, connectivity, and updates. Two questions matter most:

- **How do you deploy and update it?** In a locked-down environment you may not have a CI/CD pipeline, SSH, or internet access — deployment might be handing an artifact to their ops team through a change window. Plan for their process, not yours.
- **Who operates it after you leave?** An FDE engagement ends; the software persists. If the customer's team will run it, it needs to be operable by them — documented, monitored, and not dependent on tribal knowledge only you hold.

```text
demo (your laptop, clean data)
   │  profile real data · adapt to their systems · pass security · fit their deploy process
   ▼
production (their environment, real data, their operators)
```

## Observability and handover

The moment your solution touches production data, you need to see what it's doing: structured logs, health checks, and alerts on the things that break (a feed stops, error rates spike, a downstream system changes its format). Two reasons — you want to find problems before the customer does, and when you hand over, the operators need those same signals to run it without you. A clean handover (runbook, monitoring, a documented "here's what breaks and how to fix it") is what lets an FDE actually *leave* an engagement instead of being its permanent life support.

**The gotcha:** an FDE who never documents or hands over becomes a single point of failure — every incident, forever, routes to them, and they can never take on new work. Build for handover from the start, or the success of your last engagement becomes the ceiling on your next one.

## A deployment example

The bed-placement prototype worked on a clean nightly export of one unit. Production surfaces everything the sample hid:

- **The data:** the live EHR feed has beds stuck in "cleaning" for days (nobody updated the status), patient records with missing isolation flags, and two wards that encode "occupied" differently. The prototype's happy path assumed none of this.
- **The integration:** there's no real-time API — you get an HL7/flat-file feed every few minutes, so the "live" suggestion is really "a few minutes stale," which you must surface honestly.
- **Security:** the data can't leave the hospital network, so the slick managed service you prototyped with is off the table; it has to run on their infrastructure, reviewed by their security team.
- **Operations:** after you leave, the ward's IT team runs it — so it needs a runbook, alerts when the feed stops, and a "rejects" report for records it couldn't parse.

The gap between the Wednesday demo and this is *the deployment*, and it's usually most of the total effort. Handling it — profiling the dirty feed, degrading gracefully on bad records, fitting the security and ops constraints — is what turns a beloved prototype into something the hospital can actually rely on at 3am.

**The gotcha:** promising a go-live date based on how fast the prototype came together is the classic FDE miss — the prototype was 20% of the work. Estimate *after* profiling the real feed and learning the security and deployment constraints, not from the demo.

## Key takeaways

- **Production data is dirtier than the sample** — profile the real dataset early, design for dirtiness, and mine the humans for edge cases.
- You **integrate with systems you don't control** — prefer loose coupling and build defensively for rate limits, downtime, and silent change.
- **Security, compliance, and data residency are gates, not features** — design within them and engage the customer's security team in week one.
- Plan for **their deployment process and their operators**, not your familiar CI/CD and SSH.
- **Observability + a clean handover** (runbook, monitoring) is what lets you leave an engagement instead of becoming its permanent life support.
- "It worked in the demo" and "it runs reliably in production" are separated by exactly this invisible work — budget for it.

## Further reading

- [Google SRE Book — monitoring, releases, and operating production systems](https://sre.google/books/) — the operability an FDE deployment needs.
- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/) — security, reliability, and operational-excellence constraints in customer clouds.
- [Martin Fowler — Data Quality and integration patterns](https://martinfowler.com/) — dealing with messy, real-world data and systems you don't own.
