import importlib

import pytest
from chiru.event.model import DispatchedEvent
from chiru.gateway.event import OutgoingGatewayEvent
from chiru.models.base import DiscordObject


@pytest.mark.parametrize(
    "namespace,exported,parent",
    [
        ("chiru.gateway", "chiru.gateway.event", OutgoingGatewayEvent),
        ("chiru.event", "chiru.event.model", DispatchedEvent),
        ("chiru.models", "chiru.models.channel", DiscordObject),
    ],
)
def test_all_event_types_are_exported(namespace, exported, parent):
    package_module = importlib.import_module(namespace)
    event_module = importlib.import_module(exported)

    errors: list[AttributeError] = []
    for name, what in vars(event_module).items():
        if not isinstance(what, type):
            continue

        if issubclass(what, parent):
            try:
                getattr(package_module, name)
            except AttributeError as e:
                errors.append(e)

    if errors:
        raise ExceptionGroup("Missing re-exports", errors)
