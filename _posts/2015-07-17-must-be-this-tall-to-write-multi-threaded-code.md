---
title: "Must be This Tall to Write Multi-Threaded Code"
date:  2015-07-17
tags:
- mozilla
---

[David Baron](http://dbaron.org/) put this up in Mozilla's San Francisco office a while back:

![Must be This Tall to Write Multi-threaded Code](/images/posts/thistall.jpg)

This is cute way of saying that writing safe concurrent code is, at present, rocket science. This is unfortunate, because the future of computing is shaping up to be all about concurrency. Fundamental engineering constraints like power usage are steering microprocessor manufacturers away from single-core architectures. If the fastest chips have `N` cores, a mostly-single-threaded program can only harness `(1/N)`th of the available resources. As `N` grows (and it is growing), parallel programs will win.

We want to win, but we'll never get there if it's rocket science (despite the industry-leading density of rocket scientists hacking on Gecko). Buggy multi-threaded code creates race conditions, which are _the_ most dangerous and time-consuming class of bugs in software. And while we have some [new superpowers](http://rr-project.org/) to help us react when they inevitably occur, debugging racey code is still incredibly costly. To succeed, we need to prevent races from happening in the first place.

Why do races occur? Opinions differ, but I argue the following:

__Races are endemic to most large software projects because the traditional synchronization primitives are inadequate for large-scale systems__.

Let me explain.

Small-scale systems are easy to build and maintain. So long as the details can all fit in the heads of a small number of programmers, it's relatively easy to shuffle things around to meet requirements and verify that all the pieces interact properly.

Large-scale systems are a different story. Many cooks in many interdependent kitchens necessitate strong, _assertable_ rules that allow programmers to reason about the unknowable. These rules provide a baseline level of order, but to be truly useful, they need to be _predictable_: different programmers should be able to invent similar or identical rules by deriving them from a small set of core principles, such that everyone can make reasonable predictions about the high-level behavior of code they haven't read.

Software engineering at this level is an art, whose core mission is to find the right abstraction - one that naturally offers guidance and solutions for the problems that need to be solved (_especially_ the ones that don't exist yet). The wrong abstraction is painful and error-prone. The right one is a [never ending stream of goodness](https://bholley.wordpress.com/2012/05/04/at-long-last-compartment-per-global/) from which all answers flow.

Locks don't lend themselves to these sorts of elegant principles. The programmer needs to scope the lock just right so as to protect the data from races, while simultaneously avoiding (a) the deadlocks that arise from overlapping locks and (b) the erasure of parallelism that arise from megalocks. The resulting invariants end up being documented in comments:

    // These variables are protected by monitor X:
    ...

    // These variables are only accessed on thread Y:
    ...

And so on. When that code is undergoing frequent changes by multiple people, the chances of it being correct and the comments being up to date are slim.

There's a familiar story that has repeated itself many times throughout Gecko's history:

1. Engineering leadership sees benefits to accessing some component on multiple threads, and kicks off an effort to make it thread-safe.
2. The component becomes incredibly complex and difficult to maintain. Quality suffers, engineers avoid touching it, and improvements slow to a trickle.
3. The component is now plagued with problems. The owner comes up with an elegant new design that solves most of the problems, but needs to forbid multi-threaded access to make it work. This is deemed a good trade-off by everyone, and the component becomes non-thread-safe once again.

At first glance, this constant retreat from thread-safety by seasoned programmers looks pretty grim for a multi-core future. However, these programmers aren't fleeing concurrency itself - _they're fleeing concurrent access to the same data_. That is to say, __safe and scalable parallelism is achievable by minimizing or eliminating concurrent access to shared mutable state__.

In this approach, threads own their data, and communicate with message-passing. This is easier said than done, because the language constructs, primitives, and design patterns for building system software this way are still in their infancy. [Rust](http://rustlang.org/) is designed from the ground up to facilitate this, and [uses its type system](http://doc.rust-lang.org/book/concurrency.html) to enforce single ownership of data. We're [already using some Rust in Gecko](https://news.ycombinator.com/item?id=9740429), but we're not going to be rid of C++ anytime soon. So it's critical to explore ways to incrementally add safe concurrency in C++.

During the first half of this year, I did a tour of duty with the Multimedia Playback Team to help rebuild the heavily-threaded decoding and playback pipeline to be less racey. To solve the problems I encountered there, I built some new tools and primitives that ended up being game-changers in our ability to easy write easy and correct concurrent code.

More on that next time.
