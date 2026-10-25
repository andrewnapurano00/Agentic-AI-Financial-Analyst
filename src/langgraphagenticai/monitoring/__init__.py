"""AX-08 offline foundations. Production monitoring has no activation path."""

ACTIVATION_GATES = (
    "Production authenticated identity is not verified.",
    "Durable authorized worker/job isolation is not verified.",
    "Advisor evidence reuse, source entitlements and corporate-action adapters are not verified.",
)


def activate_monitoring():
    raise ValueError("Monitoring remains disabled: " + " ".join(ACTIVATION_GATES))
