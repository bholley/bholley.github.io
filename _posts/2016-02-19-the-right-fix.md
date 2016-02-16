---
title: "On the Right Fix, and Why the Bugzilla Breach Made Me Proud"
date:  2016-02-19
tags:
- mozilla
---

At Mozilla, we keep security-sensitive bug reports confidential until the information in them is no longer dangerous. This week we’re opening to the public a group of security bugs that document a major engineering effort to remove the rocket science of writing secure browser code and make Firefox’s front-end, DOM APIs, and add-on ecosystem secure by default. It removed a whole class of security bugs in Firefox - and helped mitigate the impact of a bug-tracker breach last summer.


### The Easy Fix and the Right Fix

Software bugs generally have an easy fix and a right fix, which are often not the same. The easy fix is faster to ship, but inspires less confidence that the problem is gone for good. Too many easy fixes make for brittle and unmaintainable code, but too many right fixes mean you never ship. This tradeoff is at the heart of software engineering.

For security-sensitive software bugs, the tradeoff looks different: there is a global community of adversaries trying very hard to trigger incorrect behavior. If it can break, it will break, and the cost to users can be enormous. Spot-fixing unsafe behavior at a single call-site can often do more harm than good, because it invites an army of watchful eyes to scour the codebase for similar instances of the same pattern. They don’t need to find all of them, just one.

Sometimes the right fix is out of reach. For example, completely eliminating memory hazards in a browser engine would require [rewriting everything in a memory-safe language like Rust](https://servo.org/), which isn’t going to happen overnight. And so, to limp along, browser vendors have lots of engineers and lots of machines fuzzing day and night to try to find memory hazards before the black hats do. Discovering them this way is far preferable to discovering them as zero-days, but it’s still an enormously expensive way to tackle one particular class of bugs, and can only catch bugs _after_ they’ve landed in the tree.

This is all to say that it is worth quite a lot of effort to find and implement the right fix to security bugs. And that’s exactly what we did with Slaughterhouse.

### The Slaughterhouse Story

Late in 2013, I became concerned about a series of reports from a handful of external security researchers. These were all technically bugs in the parts of Firefox that are implemented in JavaScript - the front-end, add-ons, and various DOM APIs - and it was tempting to hand them to the appropriate developers to fix, along with a scolding for doing things wrong. But the worrisome thing was that the security issues at play - mostly variants of the [Confused Deputy Problem](https://en.wikipedia.org/wiki/Confused_deputy_problem) - were extremely subtle. Avoiding them required a degree of expertise and paranoia that couldn’t realistically be assumed for every single person hacking on the JS inside Firefox, to say nothing of add-on authors whose code we don’t control.

The right fix was to make the platform safe by default. This was, unfortunately, easier said than done. There were gobs and gobs of pre-existing code running on the platform, and so we couldn’t simply disable the ever-widening set of interaction patterns we had determined to be questionable. Instead, we had to figure out a way to _make_ it safe while preserving the semantics that people were depending on.

To make this work, we needed to make large, cross-cutting changes to a lot of core pieces of the platform - The JavaScript engine, the DOM, Xray Wrappers, Chrome Object Wrappers (COWs), WebIDL, JetPack, GreaseMonkey, and quite a bit more. The name “Slaughterhouse” was a tongue-in-cheek reference to “killing all the COWs,” along with a nod to the overall gravity of the situation.

We launched Slaughterhouse on October 22nd 2013, and declared victory exactly one year later. Over that year, we landed hundreds of patches across numerous components and products, coordinating a lot of careful and creative engineering work that I’m really proud of. The technical details are too much to delve into here, but they are quite cool: the final result is a very advanced  [Object Capability system](https://en.wikipedia.org/wiki/Object-capability_model) that uses a membrane layer of [ES6 Proxies](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Proxy) to achieve strong security guarantees while preserving compatibility with existing code. For the curious, more details can be found in a [talk](https://air.mozilla.org/safe-by-default/) I gave on the subject in Portland, the documentation of our [script security architecture](https://developer.mozilla.org/en-US/docs/Mozilla/Gecko/Script_security) and [Xray Wrappers](https://developer.mozilla.org/en-US/docs/Xray_vision), and finally, for the detail-oriented, the [complete dependency tree in Bugzilla](https://bugzilla.mozilla.org/showdependencytree.cgi?id=929539).


### Avoiding the Worst of the Breach

This past August, Mozilla discovered that an attacker had compromised a privileged Bugzilla account and [used it to obtain access to a number of security-sensitive issue reports](https://blog.mozilla.org/security/2015/09/04/improving-security-for-bugzilla/). The attacker who breached Bugzilla was particularly interested in the kind of Confused Deputy bugs that Slaughterhouse was designed to eliminate, and searched Bugzilla for them specifically. When the attacker gained access to Bugzilla, we were just landing the final pieces of Slaughterhouse on Nightly, and had already shipped large parts of it to the Release audience of Firefox. Of the high-severity bugs that the attacker found, more than 80% had been fixed on Release by the time of access, and most of the others had fixes in the pipe on pre-Release channels. Moreover, any proof-of-concept exploits that the attacker found in Bugzilla  would likely have been dead-ends, since we fixed the problems at the source in a way that would also fix any similar-but-different vulnerabilities lurking nearby.

When we learned of the breach, I waited with bated breath to hear how many of the high-severity bugs accessed by the attacker we had yet to fix in our Release channel. A few days later, the lead on the investigation pulled me aside with a grin:

[“Two f***ing bugs!”](https://www.mozilla.org/en-US/security/known-vulnerabilities/firefox-40.0/#firefox40.0.3)
