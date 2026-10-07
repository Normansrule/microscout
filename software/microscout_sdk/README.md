> STATUS: DRAFT - UNVERIFIED - requires human review at Gate G6 (pre-hardware; simulator only)

# microscout - Python SDK and simulator

```python
import microscout
with microscout.connect("sim") as drone:
    drone.takeoff(1.0)
    drone.flip("back")
    drone.land()
```

- `pip install -e ".[dev]"`, then `pytest` (23 tests) and `microscout demo`.
- Full guide: [docs/guide/program.md](../../docs/guide/program.md). Flying guide: [docs/guide/fly.md](../../docs/guide/fly.md).
- Examples: `examples/01_hello_flight.py` … `05_lqr_position.py`.
- The simulator's parameters mirror `review/G1/calc/budgets.py` (`tests/test_params.py` checks they agree). They are estimates until identified from real flight logs.
- `connect("udp://…")` raises a clear error until the firmware (milestone M7) exists; the draft message format is in [docs/protocol.md](../../docs/protocol.md).

Licence: MIT (`software/LICENSE`).
