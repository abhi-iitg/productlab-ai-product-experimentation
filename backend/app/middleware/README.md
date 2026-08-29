# middleware

- `request_id.py` — `RequestIDMiddleware` accepts an incoming
  `X-Request-ID` header or generates a UUID4, stores it on
  `request.state.request_id`, and echoes it back on the response.
