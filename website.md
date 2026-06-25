# Website Audit: Where You're Underselling Yourself

Full page-by-page analysis of pratikdhanave.github.io — what's strong, what's weak, and what's actively hurting your credibility.

---

## Executive Summary

Your portfolio has **strong technical content** but three systemic problems:

1. **Identity fragmentation** — You're called 4 different titles across 8 pages
2. **Credibility killers** — Placeholder/fabricated content on Speaking and Certifications pages
3. **Buried impact** — Your most impressive numbers (57% FinOps savings, 30K TPS, 1M+ users, 9 years GSoC, 5 countries) are scattered and never aggregated

---

## Page-by-Page Findings

### 1. HOMEPAGE (index.html) — Grade: B+

**What's strong:**
- Hero layout with photo is professional
- "Delivered Impact at Scale" section is compelling
- ADK-to-Microsoft Agent Framework migration series is well-positioned
- Skills grid is comprehensive

**What's underselling you:**

| Issue | Current | Should Be |
|-------|---------|-----------|
| Title inconsistency | `<title>` says "AI Engineer" but hero says "Senior Software Engineer" | Pick ONE strong title, use it everywhere |
| Geographic scope buried | Only "Pune, India" visible | Your clients span 5 countries (India, Philippines, Australia, UAE, Saudi Arabia) — this is international work |
| Blog count mismatch | Footer says "View All Articles (29+)" | You have 107+ articles — the 29 is only the new markdown-sourced posts, but a visitor doesn't know that |
| Newsletter placeholder | "Join over 500 professionals" | If fabricated, remove entirely. Placeholder subscriber counts destroy trust |
| Contact section hierarchy | Lists "Senior Engineer" before "Staff Engineer" | Lead with Staff — you've already done Staff-level work (led teams of 4-10, set architecture standards, productized a service offering) |
| Presentation video context | Just "Google Cloud Next 2022" | Add: audience size, venue significance, that this was a Google-selected speaker slot not a self-submitted CFP |
| No aggregate impact line | Impact numbers scattered across 6 cards | Add ONE line: "57% FinOps saved | 30K+ TPS | 1M+ users served | 5 countries | 40+ engineers mentored" |

---

### 2. ABOUT (about/index.html) — Grade: C

**This is your weakest content page.** It reads like a first draft — 4 generic sections, no photo, missing half your story.

**Missing entirely:**
- Your headshot (it's on the homepage but not here)
- International scope — you worked with Globe (Philippines), AFL (Australia), Bancnet (UAE/Saudi), AT&T/Ericsson (US/EU). That's a global career, not "I worked at Searce in Pune"
- 107+ published articles — you're a prolific technical author, not just a coder
- Multi-vendor open source collaboration (AT&T, Ericsson, Microsoft)
- Regulatory domain expertise (PCI-DSS, SOC 2, ISO 27001, ADGM, DIFC, SAMA, KYC/AML)
- AWS certification (only Google and Ardan Labs listed)
- The fact that you built a voice AI system for Kinetic India (shows breadth beyond backend)

**Highlight cards are too few:** Only 4 cards (speaking, Tata, OSS, Bodh). Missing: GSoC 9-year mentoring, team leadership, international teams, 107+ articles.

---

### 3. RESUME (resume/index.html) — Grade: B

**What's strong:**
- Well-structured ATS-friendly format
- Skills grid is comprehensive
- Projects section has good detail

**What's underselling you:**

| Issue | Current | Should Be |
|-------|---------|-----------|
| Job title at Searce | "Senior Software Developer" | "Senior Software Engineer / Cloud Architect" (matches homepage and your actual scope) |
| Phone number exposed | `+91 7276469649` in HTML (line 499) | We removed it from JSON-LD but it's still visible in the contact row. Remove it — use email + LinkedIn only |
| No "Download PDF" button | Nothing | Critical for recruiters. Add a prominent PDF download |
| No aggregate impact summary | Dense text paragraphs | Add a "By the Numbers" row at top: 57% FinOps savings, 30K TPS, 1M+ users, 40+ mentored, 9 yrs GSoC |
| Gap unexplained | May 2020 to Jun 2021 (no role listed) | Either explain or tighten the dates |
| Missing Litmus IoT | Not on resume | It's on the Projects page — inconsistency |

---

### 4. SPEAKING (speaking/index.html) — Grade: D (CREDIBILITY RISK)

**This is actively hurting you.** Two of your three entries are fabricated/placeholder:

| Entry | Problem |
|-------|---------|
| "Building Production Multi-Agent AI Systems" — Engineering Leadership Podcast | Says "Coming Soon" with a "Request Episode" link. There is no podcast. This looks fake. |
| "Enterprise Governance for AI Systems" — Cloud Architecture Magazine | Links to your own blog post, not an actual magazine. "Cloud Architecture Magazine" doesn't appear to be a real publication. This is misleading. |

**Only your Google Cloud Next 2022 talk is real.** One genuine conference talk is respectable — padding it with fictional entries makes everything look suspicious.

**Recommendation:** Remove the fake entries. Replace with:
- GSoC mentoring (2017-2026) — this IS public speaking/teaching
- Searce internal brown-bag sessions on AI/architecture
- The presentation video (embed it here too — it's on homepage and gallery but NOT on the speaking page)
- Blog as a form of technical communication (107+ published articles)

---

### 5. MENTORING (mentoring/index.html) — Grade: A-

**Your strongest page.** Well-structured timeline, clear stats, good proof chain.

**Minor issues:**
- Recognition section on homepage says "10+ students" but mentoring page says "40+" — inconsistency (40+ is correct, fix the homepage)
- Could link to actual GSoC project pages for stronger proof
- No testimonials or quotes from mentees

---

### 6. PROJECTS (projects/index.html) — Grade: B+

**What's strong:**
- Metric rows (TPS, latency, cost reduction) are excellent
- Good separation of OSS vs. client work

**What's underselling you:**
- Bancnet metrics show "SOMA" — should be "SAMA" (Saudi Arabian Monetary Authority) — **typo**
- No aggregate impact dashboard at the top
- Missing: Collaboration context with AT&T/Ericsson/Microsoft (shown on mentoring but not here)
- Missing: Cross-link to detailed project pages (Genie, Bodh, HarbourBridge pages exist but aren't prominent)

---

### 7. CERTIFICATIONS (certifications/index.html) — Grade: D (CREDIBILITY RISK)

**This page has the opposite problem of Speaking — instead of fabricated entries, it has entries so vague they look fake.**

| Entry | Problem |
|-------|---------|
| "Professional Certification" (2020) | What certification? From whom? |
| "Professional Certification" (2023) | Issuer says "Multi-Agent AI Expertise" — this isn't a real credential name |
| "Certificate of Completion" (2023) | For what? From where? |
| "Professional Credential" (May 2023) | Completely generic |
| "Achievement Award" (2023) | From whom? For what? |

**Missing actual important certifications:**
- Google Cloud Generative AI Leader (mentioned on resume but not here with proper name)
- AWS Certified Generative AI Developer - Professional (on resume, not here)
- Ardan Labs Ultimate Go / Ultimate Services Go (on resume, not here)
- Google Cloud Specialization - Data Engineering, Big Data, and ML (on resume, not here)

**The nav is also structurally different** from every other page (inline `<a>` tags instead of `<ul>/<li>` — looks inconsistent).

**OG description still says "2017-2020"** for GSoC — should be "2017-2026".

---

### 8. GALLERY (gallery/index.html) — Grade: A-

**Solid page.** Photos are well-organized, lightbox works, video is embedded.

Minor: Group photo could identify who's in it.

---

## Cross-Cutting Issues

### 1. Identity Fragmentation (CRITICAL)
You use 4 different titles across the site:

| Page | Title Used |
|------|-----------|
| index.html `<title>` | "AI Engineer & Cloud Architect" |
| index.html hero | "Senior Software Engineer & Cloud Architect" |
| resume.html | "Senior Software Developer" |
| about.html subtitle | "Multi-Agent AI Engineer" |
| JSON-LD everywhere | "Senior Software Engineer & Cloud Architect" |

**Pick one. Use it everywhere.** Recruiters who see different titles on different pages assume you're confused about your own positioning.

### 2. International Scope is Invisible
Your client work spans 5+ countries:
- **India** — Tata Group, Kinetic India
- **Philippines** — Globe Telecom (30K TPS)
- **Australia** — AFL Brownlow (100K+ votes)
- **UAE/Saudi Arabia** — Bancnet Open Banking (ADGM, DIFC, SAMA)
- **US/EU** — AT&T, Ericsson, Microsoft (open source collaboration)

This is nowhere aggregated. Most engineers with your experience have only worked in 1-2 geographies. **Five countries is a differentiator.** Put it in the hero.

### 3. Fake/Placeholder Content Damages Trust
- Speaking page: 2 of 3 entries are fictional
- Newsletter: "500 professionals" if fabricated
- Certifications: 5 entries with no actual cert names

**Remove anything that isn't real.** One genuine conference talk is better than one real talk + two fake ones.

### 4. No PDF Resume Download
For a professional portfolio targeting recruiters, this is table stakes. Add a prominent "Download PDF" button on the resume page.

---

## Recommended Fix Priority

### P0 — Fix Immediately (credibility risks)
1. Remove fictional Speaking entries (podcast, magazine)
2. Fix Certifications page — add real cert names, remove vague entries
3. Unify title across all pages
4. Remove phone number from resume HTML (line 499)
5. Fix "SOMA" typo on projects page (should be "SAMA")
6. Fix GSoC dates in certifications OG description (2020 → 2026)

### P1 — High Impact (underselling)
7. Add aggregate impact line to homepage hero ("57% FinOps saved | 30K TPS | 1M+ users | 5 countries | 40+ mentored")
8. Rewrite About page with international scope, photo, full story
9. Add video embed to Speaking page
10. Fix blog article count (29+ → 107+)
11. Fix "Senior Software Developer" on resume → "Senior Software Engineer"
12. Add "Download Resume PDF" button
13. Fix certifications nav to match site-wide pattern
14. Fix "10+ students" → "40+ students" on homepage recognition section

### P2 — Polish
15. Remove or make newsletter real (remove "500 professionals" if fabricated)
16. Add aggregate impact dashboard to Projects page top
17. Add Kinetic India + Litmus IoT to resume
18. Cross-link Speaking ↔ Mentoring pages
19. Contact section: lead with "Staff Engineer" before "Senior Engineer"
20. Add presentation context (audience size, Google-selected speaker)

---

## The One-Line Version

**You've done Staff-level international work across 5 countries, mentored 40+ engineers for 9 years, achieved 57% FinOps savings for one of India's largest conglomerates, and authored 107+ technical articles — but your site presents you as a senior engineer from Pune with one conference talk and some vague certifications.**
