# Security policy

## Supported versions

lexiqr follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html);
security fixes land on the latest release line.

| Version | Supported |
|---------|-----------|
| latest release | ✅ |
| anything older | ❌ — upgrade first |

## Reporting a vulnerability

**Do not open a public issue for a security problem.** Instead, use GitHub's
private vulnerability reporting: **Security → Report a vulnerability** on this
repository. That opens a private advisory thread with the maintainer.

Please include what you can of:

- the affected version and a minimal reproduction (a lexicon file and a prompt
  are usually enough — lexiqr's behaviour is deterministic, so a reproduction
  travels well);
- the impact you believe it has (lexiqr parses untrusted lexicon documents and
  untrusted prompt text, so malformed-input handling is in scope);
- any suggested fix.

You should get an initial response within a week. Once a fix ships, the
advisory is published and the fix is noted in [CHANGELOG.md](CHANGELOG.md)
under the release that carries it.

## Scope notes

lexiqr's input boundary is deliberately small and documented: prompts are
bounded by `MAX_PROMPT_LENGTH`, surface forms by `MAX_SURFACE_FORM_LENGTH`,
lexicon documents are validated on load, and adversarial Unicode (combining
floods, bidi controls, lone surrogates) is handled in bounded time — see the
[Input limits](README.md#input-limits) section of the README. Anything that
makes those bounds not hold — a hang, a crash, or unbounded memory on hostile
input — is a security bug and very much worth reporting.
