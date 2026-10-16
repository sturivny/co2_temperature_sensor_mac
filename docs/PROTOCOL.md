# Device protocol (firmware 0.1.1)

## USB

115200 baud, newline-delimited UTF-8 JSON. One owner per port. The firmware can
emit unsolicited `measurement` objects every five seconds. Ignore unrelated
object types when waiting for a command response; ignore non-JSON boot logs.
The input line limit is 768 bytes; JSON request storage is 1024 bytes.

| Request `cmd` | Parameters | Response `type` |
|---|---|---|
| `status` | none | `status` |
| `scan` | none | `scan`, decimal `addresses` array |
| `set_time` | `unix_s` >= 1735689600 | `ack`, `ok` or `error` |
| `configure` | `ssid`, `password`, `token` | `configured`, `ok`, `device_id`, `host` |
| `history` | `after` (default 0), `limit` (1–64) | `history` |

Configuration limits: nonempty SSID up to 32 bytes, password up to 64 bytes,
API token 32–64 bytes. Generate a random token locally; never commit an actual
request containing credentials. Configuration is available only over USB.
Unknown commands / invalid requests return `type: ack` plus `error`.

Status fields: `firmware`, `device_id`, `host`, `boot`, `uptime_s`, `unix_s`,
`sensor_started`, `oled_found`, `sda`, `scl`, `error`, `wifi_connected`, `ip`,
`paired`, `co2`, `temperature`, `humidity`, `age_s`, and `journal`.
Before a first reading `co2` and `age_s` are null; temperature/humidity may be
absent. `age_s` determines freshness. Journal fields: `healthy`, `capacity`,
`count`, `oldest_seq`, `newest_seq`, `interval_s`.

History fields: `device_id`, `oldest_seq`, `newest_seq`, `requested_after`,
`gap`, `next_after`, `more`, `read_ok`, `records`. Each record contains `seq`,
`unix_s`, `boot`, `uptime_s`, `co2`, `temperature`, `humidity`.

Request sequences strictly greater than `after`, ingest idempotently, then
continue from `next_after` while `more`. Reject `read_ok=false`, mismatched
device identity, mismatched `requested_after`, or a nonadvancing cursor when
`more=true`. A gap means the requested early range has already been overwritten;
it is not permission to invent records.

## HTTP

Both endpoints are GET and require `Authorization: Bearer <local-token>`:

- `/api/status`
- `/api/history?after=0&limit=64`

Bodies match USB status/history objects. Missing/wrong authorization returns
401. Other routes, including `/`, return 404. No password or API key is echoed
by successful provisioning or status. No CORS/browser UI, TLS, remote relay,
or network configuration endpoint is implemented.
