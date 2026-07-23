"""Tests for binding precedence, NONE remap, and explain traces."""

import pytest

from resource_manager.binding import REMAP_NONE, BindingTrace
from resource_manager.exceptions import ResourceLinkError
from resource_manager.links import ResourceProviderLink, ResourceRequireLink
from resource_manager.resolver import DepBuilder


@pytest.fixture
def proxy_providers():
    """Providers shaped like paasify_plugin_proxy / net_proxy."""
    return [
        ResourceProviderLink({"kind": "paasify_plugin_proxy", "instance": "docker"}),
        ResourceProviderLink({"kind": "paasify_plugin_proxy", "instance": "traefik"}),
        ResourceProviderLink({"kind": "paasify_plugin_proxy", "instance": "default"}),
        ResourceProviderLink({"kind": "net_proxy", "instance": "pub"}),
        ResourceProviderLink({"kind": "net_proxy", "instance": "int"}),
    ]


class TestBindingPrecedence:
    """pin > remap > default_alias > schema."""

    def test_pin_beats_remap(self, proxy_providers):
        req = ResourceRequireLink({"kind": "paasify_plugin_proxy", "instance": "docker"})
        trace = req.match_provider_traced(
            proxy_providers, remap_rules={"paasify_plugin_proxy": "traefik"}
        )
        assert trace.reason == "pin"
        assert trace.resolved_instance == "docker"
        assert len(trace.matches) == 1
        assert trace.matches[0].instance == "docker"

    def test_remap_beats_default(self, proxy_providers):
        req = ResourceRequireLink({"kind": "paasify_plugin_proxy", "mod": "?"})
        trace = req.match_provider_traced(
            proxy_providers, remap_rules={"paasify_plugin_proxy": "traefik"}
        )
        assert trace.reason == "remap"
        assert trace.resolved_instance == "traefik"
        assert trace.matches[0].instance == "traefik"

    def test_default_alias_when_no_remap(self, proxy_providers):
        req = ResourceRequireLink({"kind": "paasify_plugin_proxy", "mod": "!"})
        trace = req.match_provider_traced(proxy_providers)
        assert trace.reason == "default_alias"
        assert trace.resolved_instance == "default"
        assert len(trace.matches) == 1

    def test_schema_when_no_default_provider(self):
        providers = [
            ResourceProviderLink({"kind": "db", "instance": "mysql"}),
            ResourceProviderLink({"kind": "db", "instance": "postgres"}),
        ]
        req = ResourceRequireLink({"kind": "db", "mod": "!"})
        with pytest.raises(ResourceLinkError) as exc_info:
            req.match_provider_traced(providers)
        err = exc_info.value
        assert err.binding_trace is not None
        assert err.binding_trace.reason == "schema"
        assert len(err.binding_trace.candidates) == 2
        assert "reason=schema" in str(err)

    def test_schema_single_provider_without_default(self):
        providers = [
            ResourceProviderLink({"kind": "db", "instance": "mysql"}),
        ]
        req = ResourceRequireLink({"kind": "db", "mod": "!"})
        trace = req.match_provider_traced(providers)
        assert trace.reason == "schema"
        assert trace.resolved_instance is None
        assert len(trace.matches) == 1
        assert trace.matches[0].instance == "mysql"


class TestRemapNone:
    """NONE / None unbinds without inventing .default."""

    def test_none_string_optional_unbound(self, proxy_providers):
        req = ResourceRequireLink({"kind": "paasify_plugin_proxy", "mod": "?"})
        trace = req.match_provider_traced(
            proxy_providers, remap_rules={"paasify_plugin_proxy": REMAP_NONE}
        )
        assert trace.reason == "unbound"
        assert trace.resolved_instance is None
        assert trace.matches == []
        assert trace.remap_value == REMAP_NONE

    def test_none_python_optional_unbound(self, proxy_providers):
        req = ResourceRequireLink({"kind": "paasify_plugin_proxy", "mod": "?"})
        instance, matches = req.match_provider(
            proxy_providers, remap_rules={"paasify_plugin_proxy": None}
        )
        assert instance is None
        assert matches == []

    def test_none_singular_fails_with_trace(self, proxy_providers):
        req = ResourceRequireLink({"kind": "paasify_plugin_proxy", "mod": "!"})
        with pytest.raises(ResourceLinkError) as exc_info:
            req.match_provider_traced(
                proxy_providers, remap_rules={"paasify_plugin_proxy": "NONE"}
            )
        assert exc_info.value.binding_trace.reason == "unbound"
        assert "unbound" in str(exc_info.value)


class TestNetProxyMixed:
    """UC5-style: independent kind remaps / pins."""

    def test_default_net_int_pin_pub(self, proxy_providers):
        remap = {
            "paasify_plugin_proxy": "traefik",
            "net_proxy": "int",
        }
        plugin = ResourceRequireLink({"kind": "paasify_plugin_proxy", "mod": "?"})
        net = ResourceRequireLink({"kind": "net_proxy", "instance": "pub", "mod": "?"})

        plugin_trace = plugin.match_provider_traced(proxy_providers, remap_rules=remap)
        net_trace = net.match_provider_traced(proxy_providers, remap_rules=remap)

        assert plugin_trace.reason == "remap"
        assert plugin_trace.resolved_instance == "traefik"
        assert net_trace.reason == "pin"
        assert net_trace.resolved_instance == "pub"


class TestDepBuilderExplain:
    """Binding traces collected during resolve."""

    def test_explain_bindings_after_resolve(self):
        resources = {
            "proxy_traefik": {"provides": ["paasify_plugin_proxy.traefik"]},
            "proxy_docker": {
                "provides": [
                    "paasify_plugin_proxy.docker",
                    "paasify_plugin_proxy.default",
                ]
            },
            "app_svc": {
                "provides": ["app_svc.web"],
                "requires": ["paasify_plugin_proxy.?"],
            },
        }
        builder = DepBuilder(
            resources=resources,
            feature_names=["app_svc.web"],
            remap_rules={"paasify_plugin_proxy": "traefik"},
        )
        builder.resolve()

        explains = builder.explain_bindings()
        plugin_traces = [
            t for t in explains if t["kind"] == "paasify_plugin_proxy"
        ]
        assert plugin_traces
        assert plugin_traces[0]["reason"] == "remap"
        assert plugin_traces[0]["resolved_instance"] == "traefik"
        assert isinstance(builder.binding_traces[0], BindingTrace)
