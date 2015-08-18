---
title: "MozPromise: A Better Tool for Asynchronous C++"
date:  2015-08-18
tags:
- mozilla
---

Last time, I argued that [shared mutable state should be considered harmful]({% post_url 2015-07-17-must-be-this-tall-to-write-multi-threaded-code %}). To avoid it, threads need to own their data and communicate asynchronously.

The traditional approach to asynchronous programming involves a lot of callbacks: every potentially-asynchronous operation needs to bundle continuation logic as a callback function which gets invoked when the operation completes. This is great in theory, but in practice has a lot of downsides:

* The control flow is scattered across the callbacks, making the program logic harder to follow. Worse, this difficulty scales linearly with the number of asynchronous operations, creating a perpetual disincentive to make more things asynchronous.
* The control flow can end mysteriously when an API forgets to invoke the callback. Debugging these cases is much more painful than debugging a synchronous hang, because there's no backtrace.
* There tends to be a lot of boilerplate to marshall control flow in and out of messages, and this boilerplate can be easy to get wrong.

These problems span languages and runtimes, but are particularly visible in the Web Platform, whose run-to-completion model forces most interesting APIs to be asynchronous. After a lot of experimentation with different ways to improve the situation, Web developers recently coalesced around [Promises](https://promisesaplus.com/) as the prevailing idiom for managing asynchronicity. And while Promises certainly have their detractors, most people in the JavaScript community seem to agree that they were a good idea. So why don't we have something like that in C++?

The answer is complicated. Recent editions of the C++ standard library [include a thing called a Promise](http://en.cppreference.com/w/cpp/thread/promise), but it doesn't look much like a JavaScript Promise, in large part because C++ itself has no concept of an Event Loop. Gecko has one though, so last November I [started building](https://bugzilla.mozilla.org/show_bug.cgi?id=1097823) some machinery to mimic the idioms of JavaScript promises in our C++ multimedia stack. This became MediaPromise, was later [renamed to MozPromise](https://bugzilla.mozilla.org/show_bug.cgi?id=1184634), and finally [moved from dom/media/ to xpcom/](https://bugzilla.mozilla.org/show_bug.cgi?id=1188976).

MozPromises work great, and I already forget how we lived without them. A number of other organizations and researchers have been [barking up](https://code.facebook.com/posts/1661982097368498) the [same tree](http://stellar-group.org/2015/06/hpx-and-cpp-dataflow/) this year, which indicates that we'll likely see a lot more of this kind of thing very soon. The MozPromise API was a quick-and-dirty job, and I expect the industry will iterate on these patterns and eventually produce something more elegant and general. That being said, the core ideas of MozPromise have proven themselves to be exceedingly useful in enabling asynchronicity and parallelism, and I think they're worth sharing.

###The Basics

A method whose result may be computed asynchronously returns a `MozPromise`. More specifically, it returns an `nsRefPtr<MozPromise<ResolveType, RejectType>>`, which is templated on the type of values that we want to propagate upon success or failure. Returning a smart pointer directly from a method is generally frowned upon, but we do it anyway. This enables us to compactly follow the MozPromise-returning method with a `Then()` call, similar to what we'd do in JavaScript:

    mProducer->RequestFoo()
             ->Then(mThread, __func__, this,
                    &ThisClass::OnFooResolved,
                    &ThisClass::OnFooRejected);

`Then()` takes a strong reference to a callback object (`this` in the case above), and guarantees that either `OnFooResolved(ResolveType)` or `OnFooRejected(RejectType)` will eventually be invoked as an asynchronous event on `mThread`. We pass `__func__` here and elsewhere so that the built-in logging can print out the entire history of control flow (this turns out to be quite useful).

The above already offers several useful advantages over traditional callback-based asynchronicity:

* The exact callback method is selected by the caller at call time, and not exposed to the underlying API at all. This eliminates boilerplate interfaces, `enum`s, and all the other junk that's normally needed to hook up and invoke a callback across loosely-coupled modules.
* The callback is guaranteed to be invoked asynchronously _on the thread that the caller intended_, without any additional work on the part of the callee. This eliminates common re-entrancy and thread-safety pitfalls.
* Hangs are easy to diagnose, because we have an object (the MozPromise) which tracks the request we made. The logging facilities make it simple to locate the caller that allocated the MozPromise, even when it's buried deeply in unfamiliar code.
* Mandatory first-class error handling.

Even with those advantages, the above code still requires the reader to jump to a different line to follow the control flow. This is often fine, but gets cumbersome when `OnFooResolved` is one or two lines of code. Fortunately, C++ lambdas allow us to support an alternate overload of `Then()` with inline callbacks:

    mProducer->RequestFoo()
             ->Then(mThread, __func__,
                    [...] (ResolveType aVal) { ... },
                    [...] (RejectType aVal) { ... });

Note that the resolve/reject values are always optional, so they may be omitted from the callback signature when unnecessary.

MozPromises are also chainable, provided that the types match up:

    mProducer->RequestFoo()
             ->Then(mThread, __func__,
                    [...] (ResolveType aVal) { ... },
                    [...] (RejectType aVal) { ... })
             ->CompletionPromise()
             ->Then(mOtherThread, __func__,
                    [...] (ResolveType aVal) { ... },
                    [...] (RejectType aVal) { ... });


This works much like you'd expect from JavaScript: the first callback can itself return a MozPromise, to which the second `Then()` is indirectly applied. Unlike JavaScript though, callers must explicitly invoke `CompletionPromise()` to access the thenable. This allows us to optimize some things in the common case where it isn't needed. More importantly, it permits us to do something more interesting with the direct return value of `Then()` - more on that in the section on disconnection below.

### InvokeAsync

The core difficulty of owned-data multi-threading comes when logic on thread `A` needs to interact with data owned by thread `B`. This is where MozPromise really shines, with the aid of a small helper called `InvokeAsync`:

    InvokeAsync(mOtherThread, [MozPromise-Returning Method])->Then(...)

`InvokeAsync` dispatches a runnable to an arbitrary thread `B` to invoke a method that returns a MozPromise. Next, it returns a separate MozPromise of the same type to its caller on thread `A`. When the target method executes, the returned MozPromise is chained to the one that was returned to the caller on thread `A`, such that resolution and rejection are propagated through.

This allows for safe and transparent cross-thread procedure calls: thread `A` can invoke a method on thread `B` and use the result directly, whether or not `A == B`. In other words, _MozPromises hide the details of message-passing and offer uniform, programmer-friendly ergonomics for same-thread and cross-thread procedure calls_. This dramatically reduces the cost of dividing program logic across multiple threads, and puts the fruits of parallelism much more within reach.

### Disconnection

MozPromise callbacks are cancellable up until the moment they are invoked, which is very powerful when you want to interrupt the operation of a long, asynchronous pipeline.

Consider the case of seeking a media element in Gecko. The request originates from a user action (manipulating the video controls), which invokes a setter on HTMLMediaElement on the Main Thread. This forwards request to the Decoder State Machine Thread, which queues up work on the Media Decode Thread, which is usually delegated to an OS-specific Platform Decoder Thread.

This presents a serious problem when the user interrupts the action and tries to seek somewhere else before the original seek has completed. There's a lot of inertia in the pipeline, and we have no way to stop it instantaneously. The first operation may have already completed, and the result might already be on its way back, so we risk getting confused if we initiate a second operation.

So we ended up writing code like this:

    mQueuedSeekTarget = newSeekTarget;
    mReader->DispatchCancelSeekTask();
    // Wait for the previous seek to succeed or be canceled.
    // When everything is finished, we'll check mQueuedSeekTarget
    // and start seeking again.
    return;

This is clearly suboptimal, and we can do better with MozPromises.

I mentioned earlier that `Then()` does not return another MozPromise. This is because it returns a `MozPromise::Request`, which is a handle to the callback invocation scheduled by `Then()`. Callers that care can store this value, and invoke `Disconnect()` if they no longer wish to receive the callback. This allows us to handle interrupt seeks much more elegantly:

    mSeekRequest.DisconnectIfExists();
    mReader->DispatchCancelSeekTask();
    // Move on with life \o/
    mSeekRequest.Begin(
      InvokeAsync(mReader, &Reader::Seek)
      ->Then(...)
    );

We use disconnection heavily in Gecko's media stack, and it is exceedingly useful in handling interruptions, error conditions, and shutdown.

### Conclusion

MozPromises solved a lot of tricky problems for the Media Playback Team, and I'd encourage other Gecko hackers to give them a spin. I also welcome thoughts and feedback from the wider community of developers and theorists - I'm sure there are heaps of improvements to be made, and I would be especially interested in concrete suggestions that are practical to implement.

The latest version of the code can be found [here](https://dxr.mozilla.org/mozilla-central/source/xpcom/threads/MozPromise.h), and a snapshot of the code at the time this piece was written can be found [here](https://hg.mozilla.org/integration/mozilla-inbound/file/bd4464cd4be8/xpcom/threads/MozPromise.h). Patches welcome!
