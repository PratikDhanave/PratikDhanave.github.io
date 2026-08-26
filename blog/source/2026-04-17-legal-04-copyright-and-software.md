# Copyright and Software

*Every line of code you write is, the instant you write it, protected by copyright — automatically, with no registration required. That surprises many engineers, and its implications run deep: copyright is the legal foundation of who owns software, why you can't just copy others' code, and why software licenses (which grant permission around copyright) exist at all. Understanding copyright as it applies to code is the single most relevant piece of IP knowledge for a working engineer. (Educational, not legal advice.)*

**Copyright** is the IP type most relevant to software — it protects *code* as creative expression. This post covers how copyright applies to software, what it does and doesn't protect (expression vs ideas), *who owns* the copyright (work-for-hire and IP assignment — crucial for engineers), and fair-use basics. It builds on the IP overview and is foundational for the licensing post (licenses grant permission around copyright). (Educational, not legal advice — copyright law is complex and jurisdiction-specific; consult a lawyer for real decisions.)

## Copyright and code

**Copyright** protects *original creative works of expression* — and *software code* counts as such a work, so code is protected by copyright:

- **Code is protected by copyright.** Copyright protects *original works of authorship* fixed in a tangible form — and *software source code* (and compiled code) qualifies as such a *creative work*. So *code is copyrighted* — the author/owner has copyright over it (rights to copy, distribute, modify, etc.). Code is a copyrighted work. Your code is protected expression.
- **Copyright is automatic.** Crucially, copyright arises *automatically* when you *create* the work — you *don't* need to register it or add a notice (though registration/notice add benefits in some jurisdictions). The moment you *write* code, it's *copyrighted* (by default, by whoever owns it — below). No registration needed for the basic protection. Copyright is automatic on creation. Written = copyrighted.
- **This has big implications.** Because code is automatically copyrighted, you *can't* just *copy* others' code (it's protected — copying without permission infringes), and *your* code is *protected* (others can't copy it without permission). This is *why* you need *licenses* (permission to use others' code — the licensing post) and why copying code isn't free-for-all. Copyright is the *legal basis* of software ownership and licensing. Copyright underlies software ownership and licensing. It's why licenses exist.

Code is protected by copyright automatically (the moment it's written, no registration needed) as an original creative work — which is why you can't freely copy others' code (infringement) and your code is protected, and why licenses (permission around copyright) exist. Copyright is the legal foundation of software ownership. But *what exactly* copyright protects has an important nuance.

## What copyright protects (expression, not ideas)

A crucial nuance: copyright protects the *expression* (the specific code), *not* the underlying *ideas, functions, or algorithms* — the "idea-expression distinction":

- **Copyright protects expression, not ideas.** Copyright protects the *specific expression* — the actual *code as written* — but *not* the underlying *ideas, methods, algorithms, or functionality*. So the *particular code* is protected, but the *idea/function* it implements is *not* (by copyright). This "idea-expression distinction" is fundamental to copyright. Expression protected, ideas not. The specific code, not the concept.
- **You can reimplement functionality (generally).** A consequence: you *can* generally *reimplement* the same *functionality* in *your own code* (your own expression) *without* infringing copyright — because copyright protects the *expression* (the specific code), not the *idea/function*. Copying the *code* infringes; independently writing *your own code* for the *same function* generally doesn't. (This is why clean-room reimplementations exist.) Reimplement the idea in your own code, generally OK. Same function, different code.
- **But copying code (expression) infringes.** Conversely, *copying the actual code* (the expression) *does* infringe copyright (without permission/license) — you can't just copy someone's code. The distinction: *copying the code* = infringement; *reimplementing the function yourself* = generally not. Copying expression infringes; reimplementing the idea doesn't. Don't copy the code itself.
- **The line can be subtle (get advice).** The idea-expression line can be *subtle* (how much can you borrow before it's copying expression? what about structure?), and it's *jurisdiction-dependent*. For real situations near the line, get legal advice. The concept is clear; the boundary can be fuzzy. The line is subtle — get advice near it. Fuzzy boundary, real stakes.

Copyright protects the *expression* (the specific code as written), not the underlying *ideas, algorithms, or functionality* (the idea-expression distinction) — so copying actual code infringes, but generally you can reimplement the same functionality in your own code without infringing (the boundary can be subtle). Beyond *what's* protected, the crucial question for engineers is *who owns* the copyright.

## Who owns the copyright: work-for-hire and IP assignment

The most practically important copyright question for engineers is *ownership* — and the key concepts are **work-for-hire** and **IP assignment**:

- **Work made for hire: employer often owns it.** A crucial rule: code you create *as an employee* (in the scope of your job) is typically a *"work made for hire"* — meaning your *employer* (not you) owns the copyright. So *code you write at work* usually belongs to your *employer*, not you. Employees generally don't own the code they write for their job. Employers usually own employees' work-product code. What you build at work isn't yours.
- **IP assignment agreements.** Employment (and contractor) agreements typically include *IP assignment* clauses — *assigning* the IP you create *to the company* (making explicit that the company owns your work-product IP). So you likely *signed away* ownership of your work-product IP to your employer (via your employment agreement — the contracts post). IP assignment agreements transfer your IP to the company. You signed it over.
- **Contractors are different (get it in writing).** For *contractors/freelancers* (not employees), the default ownership rules *differ* (a contractor may *retain* copyright unless it's *assigned* by contract) — so if you *hire* a contractor to build something, you need a *written assignment* to *own* the result (otherwise the contractor might own it!). This is a common, costly mistake (assuming you own what you paid a contractor to build without a written assignment). Contractor IP needs written assignment. Get ownership in writing.
- **This matters for employees and founders.** Understanding ownership matters for *employees* (know that your work-product IP is usually your employer's) and *founders* (ensure the company *owns* the IP — via proper agreements with employees and contractors, so IP isn't accidentally owned by individuals). IP ownership is a critical, often-overlooked issue. Get IP ownership right (a "get a lawyer" area). Papering IP ownership matters.

The crucial copyright question for engineers is ownership: code created as an *employee* is typically a "work made for hire" owned by the *employer*, and employment/contractor agreements include *IP assignment* clauses transferring IP to the company — while *contractors* may retain copyright unless it's assigned in writing (so hiring a contractor needs a written assignment to own the result). Getting IP ownership right is critical for employees and founders. A final copyright concept is fair use.

## Fair use (briefly)

**Fair use** is a limited exception allowing *some* use of copyrighted material *without* permission — but it's narrow, fact-specific, and often misunderstood:

- **Fair use permits limited unlicensed use.** *Fair use* (in some jurisdictions; other terms elsewhere) is a *legal exception* allowing *limited* use of copyrighted material *without* the owner's permission in certain circumstances (like commentary, criticism, education, research). It's a *narrow exception* to the need for permission. A limited exception to copyright. Some use without permission.
- **It's narrow and fact-specific.** Fair use is *not* a broad "I can use anything" — it's *narrow* and *highly fact-specific* (courts weigh factors like purpose, nature, amount used, and market effect, case by case). Whether something is fair use is *often unclear* and decided case-by-case. Don't assume fair use covers your use. Fair use is narrow and uncertain. Not a broad free pass.
- **It's often misunderstood.** Fair use is *widely misunderstood* — people assume it covers far more than it does (assuming any non-commercial or attributed use is fair — often false). *Don't rely on* fair use casually; it's a *limited, uncertain* exception, and misjudging it risks infringement. For real situations relying on fair use, get legal advice. Don't overestimate fair use. It's less than people think.

Copyright is the IP type most relevant to software: code is automatically copyrighted (protecting the *expression*, not the ideas/functions — so copying code infringes but reimplementing generally doesn't), ownership usually goes to the *employer* (work-for-hire, IP assignment — with contractors needing written assignment), and fair use is a narrow, often-misunderstood exception. Understanding copyright is the most relevant IP knowledge for engineers. Next: patents, trademarks, and trade secrets. (Educational, not legal advice.)

## Key takeaways

- Code is protected by copyright *automatically* (the moment it's written, no registration needed) as an original creative work — which is why you can't freely copy others' code (copying infringes), your code is protected, and licenses (permission around copyright) exist; copyright is the legal foundation of software ownership.
- Copyright protects the *expression* (the specific code as written), *not* the underlying ideas, algorithms, or functionality (the idea-expression distinction) — so copying actual code infringes, but generally you can *reimplement the same functionality in your own code* without infringing (though the boundary can be subtle and jurisdiction-dependent).
- The crucial ownership question: code created as an *employee* (in your job's scope) is typically a "work made for hire" owned by the *employer*, and employment/contractor agreements include *IP assignment* clauses transferring your IP to the company — so your work-product code usually belongs to your employer, not you.
- Contractors differ — a contractor may *retain* copyright unless it's assigned in writing — so hiring a contractor to build something requires a *written assignment* to own the result (a common, costly mistake is assuming you own what you paid for without it); getting IP ownership right is critical for employees and founders (a "get a lawyer" area).
- Fair use is a *narrow, fact-specific, often-misunderstood* exception allowing *limited* unlicensed use of copyrighted material in certain circumstances (commentary, education) — it's decided case-by-case (weighing purpose, amount, market effect), covers far less than people assume, so don't rely on it casually (get advice for real situations).

## Further reading

- [Copyright (Wikipedia)](https://en.wikipedia.org/wiki/Copyright)
- [Intellectual property overview (previous post)](/blog/posts/legal-03-intellectual-property-overview.html)
- [Originality and copyright — respecting others' work (this blog's own rule)](/blog/posts/legal-01-why-legal-basics-matter.html)
