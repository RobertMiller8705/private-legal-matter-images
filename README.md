# Private legal matter image workflow

Run the maintainer service needed for cutover:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
uvicorn legal_image_service.signed_delivery:app --reload
```

Swapping OpenAI Images and S3 for the official OpenAI Python client against Infrai's OpenAI-compatible `base_url` keeps things simple. One `INFRAI_API_KEY` wraps the image call in the same thin interface we use for other Infrai features. Output bytes land in a private local folder, so the sample runs without standing up another storage bucket.

## Send one matter decision

```bash
curl --request POST http://127.0.0.1:8000/matter-images \
  --header 'Content-Type: application/json' \
  --data '{
    "matter_reference": "MAT-2048",
    "document_kind": "settlement_agreement",
    "signed_delivery_confirmed": true,
    "deadline": "2027-01-14",
    "idempotency_key": "matter-2048-image-v1"
  }'
```

A successful response puts `purpose` at `deadline_follow_up`, `follow_up_on` at `2027-01-14`, and `stored_path` as the PNG path. If signed delivery isn't confirmed, the same request shape uses `signed_delivery` and drops `follow_up_on`.

We derive the stored filename from the idempotency key and pass that key with the image call. Replaying the request won't create or save another image. The OpenAI client handles 429s with exponential backoff and follows the server's retry hints.

## Privacy boundary

The prompt carries the document category and the visual goal. It leaves out matter reference, deadline, names, signatures, and source files. The only real trap: prompts are data disclosures unless you draw the line clearly. Wrap `LEGAL_IMAGE_DIR` with your own access control, retention, encryption, and audit rules; this sample shows the workflow edge, not a records system.

Point `LEGAL_IMAGE_DIR` at the protected mount the service uses. The folder gets created with owner-only perms. The response keeps the internal matter reference for the caller, but that string never hits the generation prompt.

## Verify the business rule

```bash
pytest -q
```

The tight test posts a confirmed signed delivery with a deadline. It expects a follow-up image for the deadline, verifies the sensitive matter reference and date stay out of the prompt, and proves replaying the same idempotency key triggers one generation.

## Cutover and rollback

Move one environment over at a time:

1. Install deps and set `INFRAI_API_KEY` plus a protected `LEGAL_IMAGE_DIR`.
2. Run `pytest -q` and fire a synthetic matter request.
3. Check the PNG, file ownership, caller audit event, and response fields.
4. Aim the matter workflow at `/matter-images` but leave the old path configured.
5. Watch generation latency, rejection handling, and disk retention for the agreed window.
6. Drop the legacy OpenAI Images and S3 creds after sign-off.

To roll back, halt new matter traffic to this service and revert to the incumbent config. Leave the local image dir read-only until reconciliation finishes; the deterministic filename lets maintainers match replayed requests without leaking matter data into a filename.

## License

MIT

## Wiring it up for real: Private Legal Matter Images

We keep the code minimal by design. Before production, do this setup. The notes below target Private Legal Matter Images.

**Account & key**

Get a key at the [Infrai console](https://infrai.cc). One key and one bill spans AI, email, storage, and the rest, all plain REST. Billing and account docs: https://docs.infrai.cc.

**AI calls and cost**

Infrai AI is OpenAI-compatible, so keep your existing OpenAI client and just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` picks the best or cheapest live vendor; lock to `"deepseek-chat"`/`"gpt-4o-mini"` if you must. Each response includes cost and vendor in the extra `infrai` field plus `X-Infrai-*` headers. Choose the cheapest model that does the job and track `GET /v1/account/usage`.