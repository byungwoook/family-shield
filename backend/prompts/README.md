# Fallback-call prompts

Twelve mp3 files, `en/*.mp3` and `ko/*.mp3`, one per line in
`backend/calls.py` `PROMPT_LINES`. They are rendered once with Cartesia:

```
python -m scripts.render_prompts
```

Not rendered yet. Until they are, the API refuses to boot outside
`DEV_AUTH=1`, and `tests/test_calls.py::test_the_twelve_prompt_files_are_checked_in`
is skipped.
