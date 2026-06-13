# Contributing to HEARD

HEARD started as a Bachelor's thesis and is now an open project. Contributions
are very welcome — a bug report, a one-line fix, a new simulator scenario, a
whole firmware feature. This file explains how to make that as painless as
possible for both of us.

## Licensing

By contributing code to HEARD in any form — a pull request on GitHub, a patch by
email, a snippet pasted into an issue — you agree to release it under the
**Apache License 2.0**, the same license that covers the rest of the project
(see [LICENSE](LICENSE)). There is no CLA to sign; opening the pull request *is*
the agreement.

## Before you write a lot of code

This is the one thing I'll ask you to take seriously.

If your change is **small** — a bug fix, a typo, a missing bounds check, one more
test — just send the pull request. No need to ask first.

If your change is **big** — a new message type, a different relay strategy, a new
transport, anything that changes how the protocol or the device behaves — please
**open an issue first and describe what you want to do and, more importantly,
why.** Tell me the use case. A feature is accepted because it fits HEARD
conceptually, not because the code is good: a beautiful patch for something that
doesn't belong will still be declined, and I'd hate for you to find that out
after a weekend of work. A short conversation up front saves everyone the
disappointment.

The [ROADMAP](ROADMAP.md) is the public plan. If your idea is already there, say
so in the issue; if it isn't, that's fine — let's talk about whether it should
be.

## Simplicity wins

Code is read far more often than it is written, and on a safety device it has to
be understood before it can be trusted. When two solutions both work, I'll take
the simpler one — fewer moving parts, fewer lines, less cleverness — almost every
time. Please don't add configuration, abstraction or dependencies "in case we
need them later." We'll add them when we actually do.

## How to submit a patch

1. Fork the repo on GitHub.
2. Create a topic branch: `git checkout -b my-feature`.
3. Make your change, with a test if it's testable (most protocol and path logic
   is — see below).
4. Push to your fork and open a pull request against `main`.
5. Make sure CI is green. That's the bar.

Keep a pull request to one logical change. A focused 20-line diff gets reviewed
in minutes; a 2,000-line diff that does five things at once sits for weeks.

## The simulator is the gate

HEARD's protocol code (`ConnectionManager`, `Connection`) is compiled,
*unmodified*, into a Python module and regression-tested against real GPX tracks.
**If you touch protocol or path logic, the simulator must still pass** — and if
you add behaviour, add a test for it. This is what lets us trust changes to a
device people's safety depends on, without a 3-device field walk for every
commit.

```bash
cd code/simulator
pip install -r requirements.txt
cmake -B build -DPYTHON_EXECUTABLE="$(which python3)"
cmake --build build
cp build/heard_sim*.so .
pytest -v
```

The firmware itself only received **minimal, non-breaking changes** to make this
possible (a handful of methods marked `virtual`). Please keep that discipline:
don't fork the logic between the real firmware and the simulator — the whole
point is that the simulator runs the *real* code. If you need a seam for testing,
add the smallest one that does the job.

CI runs three jobs, and all three must pass:

- **simulator** — builds the C++ module and runs `pytest`.
- **firmware** — `pio run` for both `dispositivo_madre` (Core) and
  `dispositivo_figlio` (Node).
- **web** — syntax-checks the viewer's ES modules.

So before you push, at a minimum build the firmware you touched
(`pio run -d code/dispositivo_madre`) and run the simulator tests.

## A note on language

The early firmware has Italian identifiers and comments (`dispositivo_madre`,
`dispositivo_figlio`, …); the docs and newer code are in English. Write **new**
code and comments in English. But please don't send pull requests that only
rename existing Italian symbols across the tree — large cosmetic diffs are hard
to review and bury the real history. If you're already changing a file
substantially, tidying its names as part of that work is welcome.

## Good places to start

- **Radio-model fitting** and the **scenario library** are the two friendliest
  entry points — both are listed under
  [ROADMAP § 2](ROADMAP.md#2-better-simulator) and need no hardware.
- The **standalone Node build**
  ([#1](https://github.com/luciobaiocchi/heard/issues/1)) is the biggest open
  firmware milestone.
- To get oriented: the [README](README.md) for the *why*, the
  [simulator README](code/simulator/README.md) and
  [SIMULATION.md](code/simulator/SIMULATION.md) for how it all works, and the
  [build video](https://www.youtube.com/watch?v=rSgT1LedNBk) for the hardware.

## Security

If you find a vulnerability — in the protocol, the firmware, anything — please
**don't open a public issue.** Report it privately through GitHub's
*Security → Report a vulnerability* (private advisory) so it can be fixed before
it's disclosed.

## Finally

This is a small project, run mostly by one person around other work, so I'm
sometimes slow to answer a pull request or an issue. It's never lack of interest
— a friendly ping after a couple of weeks is completely fair. Thanks for helping
make HEARD better.
