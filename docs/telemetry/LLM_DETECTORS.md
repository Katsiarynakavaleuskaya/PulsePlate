# LLM Detector Policy

## Current Detector Families

- `server_error`
  Trigger: response status `>=500`
- `low_confidence`
  Trigger: route sets `request.state.llm_confidence < 0.35`
- `schema_mismatch`
  Trigger: route marks `expected_response_kind=json` but response content-type is not JSON
- Explicit route-supplied detector hits
  Trigger: route sets `request.state.telemetry_detector_hits`

## Future Detector Families

- provider anomaly
- safety-rule tripwire
- structured output mismatch
- unexpected tool-call type

## Operating Rule

- Detector hits can request full capture.
- Full capture still writes only encrypted artifacts to vault storage.
- Spans retain detector names and pointer hashes only.
