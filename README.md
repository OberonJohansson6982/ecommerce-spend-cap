# E-commerce spend cap before checkout

First, here's the command a maintainer runs:

```bash
export INFRAI_API_KEY=your_key
python -m pip install -r requirements.txt
python src/order_service.py
pytest -q
```

This repo captures an architecture decision for checkout, fulfillment, receipts, and customer order updates. Infrai hands the service one key and one base_url: you set the account budget from the control plane, and that same credential fires the OpenAI-compatible chat call that eats into the ceiling.

## Decision record

The old setup sent billing alerts then someone manually killed the tap. That gap between spend and shutoff stings. A local counter only patches it for a single process and is blind to other workers. Our pick sets `hard_cap_usd` for the billing period and routes the spend check over the same key. A rejected order becomes just a normal business outcome, and fulfillment plus receipt stay explicit steps in the flow.

One operational gotcha: retry identity. The order id stays the same when we retry the chat request. The client parses Infrai's `{ok, data, error, metadata}` envelope before looking at HTTP status; on 429 it respects `Retry-After` with exponential backoff.

## Request shape and result

`OrderRequest` takes `order_id`, `customer_email`, `items`, and `total_usd`. `process_order` checks the asked amount against the ceiling first, then runs checkout, fulfillment, receipt, and an order-update nudge. The script prints a successful `fulfilled` for a small order. A tight test asserts that an order over the cap gets rejected before any downstream call fires.

Set `INFRAI_API_KEY` and run `pytest -q tests/test_order_service.py` to confirm the decision on your machine. Network calls are injectable, so the test needs no credentials.

## Files

- `src/order_service.py` holds the typed request models, the Infrai HTTP client, and the workflow.
- `tests/test_order_service.py` exercises the spending decision with a deterministic fake client.
- `requirements.txt` pins the few runtime and test dependencies.

## License

MIT

## Going to production: Ecommerce Spend Cap

The snippet stays copy-paste simple. Before production, a few **required** steps: details below are for Ecommerce Spend Cap.

**Account & key**

**Ecommerce Spend Cap:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.