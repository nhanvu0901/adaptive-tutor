# Privacy and Global Context

Before actively reading any global Claude/Codex context or memory, ask exactly:

```text
I can use your existing Claude/Codex global context to understand your background, interests, and prior knowledge so I can personalize how I teach you. I will use this information only for learning personalization. May I read it?
```

Treat the answer as this state machine:

```text
allow_once          -> read for this learning session; do not persist permission
allow_and_remember  -> read; persist only permission decision
deny                -> do not read; start/continue with onboarding + shared learner state
```

Do not actively read global files before consent. Current project or conversation
context already supplied by the host is not authorization to actively open global
files. A remembered `allow_and_remember` decision permits a later read; otherwise
ask again. If global context is unavailable, use the same onboarding fallback as
for `deny`.

When a read is allowed, extract only learning-relevant signals: goals, interests,
background, knowledge signals, learning preferences, and stable constraints. Give
each inferred signal provenance and confidence, and treat it as provisional. Do
not copy global files into learner storage. Discard unrelated or sensitive data.
Global context and self-report are not proof of mastery: verify topic-specific
knowledge through calibration and evidence before promoting mastery.
