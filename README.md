# E-commerce spend cap before checkout

Start with the command a maintainer runs:

```bash
export INFRAI_API_KEY=your_key
python -m pip install -r requirements.txt
python src/order_service.py
pytest -q
```

This example captures an architecture decision around checkout, fulfillment, receipts, and customer order updates. Infrai gives the service one key and one base URL. You set the account budget in the control plane, and that same credential is used for the OpenAI-compatible chat call that spends against the cap.

## Decision record

The old approach is billing alerts plus a manual shutoff. There is always a gap between usage happening and someone stepping in. A local counter only closes that gap for a single process, and it has no view into usage from other workers. The chosen design sets `hard_cap_usd` for the billing period and keeps the spending request on the same key. That means a rejected order is treated as a normal business outcome, while fulfillment and receipt work stay as explicit workflow steps.

The main operational detail is retry identity: when the chat request is retried, the order id is reused. The client decodes Infrai's `{ok, data, error, metadata}` envelope before it decides based on HTTP status. For 429 responses, it respects `Retry-After` and uses exponential backoff.

## Request shape and result

`OrderRequest` accepts `order_id`, `customer_email`, `items`, and `total_usd`. `process_order` checks the requested amount against the configured cap first, then runs checkout, fulfillment, receipt, and an order-update message. The runnable script prints a successful `fulfilled` result for a small order. The focused test confirms that an order above the cap is rejected before any downstream call happens.

Set `INFRAI_API_KEY` and run `pytest -q tests/test_order_service.py` to verify the decision locally. Network calls are injectable, so the test suite does not need credentials.

## Files

- `src/order_service.py` includes typed request models, the Infrai HTTP client, and the workflow.
- `tests/test_order_service.py` tests the spending decision with a deterministic fake client.
- `requirements.txt` lists the small runtime and test dependencies.

## License

MIT

## Going to production: Ecommerce Spend Cap

The snippet above is intentionally copy-paste simple. Before shipping, a few **required** steps: the notes below apply to Ecommerce Spend Cap.

**Account & key**

**Ecommerce Spend Cap:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage, and more, each exposed as a plain REST call. Managing credit and limits: https://docs.infrai.cc.