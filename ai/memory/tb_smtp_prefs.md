---
name: tb-smtp-prefs
description: Thunderbird user.js pref names for configuring outgoing SMTP — needed to point TB at a test capture server
metadata: 
  node_type: memory
  type: reference
  originSessionId: db88cfaf-a517-456a-8851-0c020b754dc2
---

To route Thunderbird's outgoing mail to a local test SMTP server, add these to `user.js` before launch (port must be known before launch, so start the server first):

```js
user_pref("mail.smtpservers", "smtp1");
user_pref("mail.smtp.defaultserver", "smtp1");
user_pref("mail.smtpserver.smtp1.hostname", "127.0.0.1");
user_pref("mail.smtpserver.smtp1.port", <port>);
user_pref("mail.smtpserver.smtp1.authMethod", 0);   // no auth
user_pref("mail.smtpserver.smtp1.auth_method", 0);  // old key, include both
user_pref("mail.smtpserver.smtp1.socketType", 0);   // plain
user_pref("mail.smtpserver.smtp1.try_ssl", 0);      // old key, include both
user_pref("mail.smtpserver.smtp1.description", "Test SMTP Capture");
user_pref("mail.identity.id1.smtpServer", "smtp1"); // connects identity to server
```

The capture server is `tests/marionette/smtp_harness.SMTPCaptureServer` — start it before the `tb` fixture writes `user.js`. See [[unittest_marionette_fix_session]].

EHLO response must send two separate CRLF-terminated lines (not one line with embedded `\r\n`):
```python
conn.sendall(b"250-localhost\r\n250 SIZE 10485760\r\n")
```
DATA body ends with `\r\n.\r\n`; dot-stuffed lines start with `..`.
