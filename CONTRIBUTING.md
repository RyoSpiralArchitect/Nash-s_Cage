# Contributing

Changes are welcome when they make assumptions, failure modes, or execution easier to inspect.

## Claim-boundary rule

The repository is currently **F0**. A code change, passing CI, lower irreversible-entry rate, or cleaner visualization does not justify a claim about the real climate system or a real institution. Pull requests should distinguish:

- what changed in the implementation;
- what changed in the toy's output;
- what, if anything, was learned about the internal mechanism;
- what remains unsupported outside the model.

## Before opening a pull request

```bash
make verify
```

When the manuscript changes and TeX is available:

```bash
make paper
```

When model logic or the reference configuration changes intentionally:

```bash
make experiment
make verify
```

Any intentional change to a release-tracked file must update `RELEASE_MANIFEST.json`. Never weaken verification by treating an absent required file as a skipped success.

## Design expectations

- Preserve common episode environments across arms unless the experiment explicitly studies unpaired designs.
- Add a declared configuration field rather than a hidden constant when the quantity is experimentally meaningful.
- Reject unknown configuration keys instead of silently ignoring them.
- Report false-positive and false-negative trigger behavior together.
- Keep capture, justice, delay, and observation error visible rather than folding them into one opaque score.
- Add tests for deterministic behavior, boundary conditions, and failure detection.
- Update the receipt and reference comparison when outputs change.
- Avoid adding third-party runtime dependencies unless the capability cannot be implemented transparently with the standard library.

## Manuscript changes

Keep v0.1 preserved. New revisions should use a new versioned filename, update the date and header, compile without undefined references, and be visually inspected after rendering.

## Licensing note

No license has been selected in this repository. Contributions should not add a license or copy externally licensed code without an explicit project decision.
