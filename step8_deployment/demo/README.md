# Local HTTP demonstration

`http_execution.json` records responses from a real localhost Flask run using the declared synthetic request on 18 September 2026. `DIAL_ALERT_Step8_HTTP_Demo.gif` is an animated playback of those recorded responses, not a screen capture and not a clinical demonstration.

Re-run the HTTP evidence capture from the repository root with:

```bash
python src/record_step8_demo.py
```

It starts the local app, queries health, submits the synthetic request, saves responses, and stops the server. Port 8000 must be available. No live patient inputs are needed.
