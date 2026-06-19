Good. The conftest looks correct. Files written:

- `tests/marionette/smtp_harness.py` — `SMTPCaptureServer`: threaded TCP listener, full SMTP state machine (EHLO/MAIL/RCPT/DATA/QUIT), dot-stuffing undo, `email.parser` header extraction, `wait_for_message()` / `clear()` / `shutdown()`
- `tests/marionette/conftest.py` — added `import smtp_harness`, `smtp_server` fixture, `smtp_server` param in `tb`, and SMTP `user_pref` lines (port injected via f-string concatenation)
- `tests/marionette/test_outgoing_smtp.py` — `TestOutgoingSMTP` with two tests: popup path and chip-menu path; each asserts `FORWARDING_ADDRESS` in `rcpt_to` list and `to_header`, and `RECIPIENT` absent from both