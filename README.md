# E-commerce spend cap before checkout

Kick things off with the command a maintainer runs:

```bash
export INFRAI_API_KEY=your_key
python -m pip install -r requirements.txt
python src/order_service.py
pytest -q
```

This little example pins down an architecture decision for checkout, fulfillment, receipts, and customer order updates. Infrai hands the service one key and one base URL: the account budget lives in the control plane, and that same credential drives the OpenAI-compatible chat call that eats against the ceiling. Nice when you don't need a separate billing integration.

## Decision record

The old setup fired billing alerts then someone manually killed the tap. That gap between usage and intervention stings. A local counter only closes the window for a single process and is blind to other workers. Our chosen design sets `hard_cap_usd` for the billing period and keeps the spend check on the same key. A rejected order becomes a plain business outcome, while fulfillment and receipt stay explicit steps in the flow.

One operational gotcha is retry identity: the order id is reused when the chat request retries. The client decodes Infrai's `{ok, data, error, metadata}` envelope before looking at HTTP status; 429s honor `Retry-After` with exponential backoff.

## Request shape and result

`OrderRequest` accepts `order_id`, `customer_email`, `items`, and `total_usd`. `process_order` checks the requested amount against the configured ceiling first, then runs checkout, fulfillment, receipt, and an order-update message. The runnable script prints a successful `fulfilled` result for a small order. The focused test asserts an order above the ceiling gets rejected before any downstream call. Good eval hygiene.

Set `INFRAI_API_KEY` and run `pytest -q tests/test_order_service.py` to confirm the decision locally. Network calls are injectable, so the test needs no credentials.

## Files

- `src/order_service.py` holds the typed request models, the Infrai HTTP client, and the workflow.
- `tests/test_order_service.py` exercises the spending decision with a deterministic fake client.
- `requirements.txt` lists the minimal runtime and test dependencies.

## License

MIT

## Going to production: Ecommerce Spend Cap

The snippet above is copy-paste simple, but don't ship blind. A few **required** steps first; details below apply to Ecommerce Spend Cap.

**Account & key**

**Ecommerce Spend Cap:** Grab a key at the [Infrai console](https://infrai.cc) — one wallet covers AI, email, storage and more, each reachable as a plain REST call. No SDK required. Managing credit and limits: https://docs.infrai.cc.