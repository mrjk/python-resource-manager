"""
Unit tests for the resource manager and resolver.
"""

import pytest

from resource_manager.exceptions import (
    ResourceConfigError,
    ResourceLinkError,
)
from resource_manager.links import (
    ResourceLink,
    ResourceProviderLink,
    ResourceRequireLink,
)
from resource_manager.resources import Resource

# pylint: disable=too-few-public-methods


class TestResourceLink:
    """Unit tests for the ResourceLink base class."""

    def test_link_initialization_with_dict(self):
        """Test initializing a link with a dictionary config."""
        link = ResourceLink({"kind": "test_kind", "instance": "instance1"})

        assert link.kind == "test_kind"
        assert link.instance == "instance1"
        assert link.mod is None

    def test_link_initialization_with_string(self):
        """Test initializing a link with a string rule."""
        link = ResourceLink("test_kind.instance1")

        assert link.kind == "test_kind"
        assert link.instance == "instance1"
        assert link.mod is None
        assert link.raw_value == "test_kind.instance1"

    def test_link_initialization_with_modifier(self):
        """Test initializing a link with a modifier in the rule."""
        link = ResourceLink("test_kind.instance1.!")

        assert link.kind == "test_kind"
        assert link.instance == "instance1"
        assert link.mod == "!"

    def test_link_initialization_invalid_format(self):
        """Test that initialization with invalid format raises an error."""
        with pytest.raises(ResourceConfigError):
            ResourceLink("test_kind.instance1.extra")

    def test_rule_property(self):
        """Test the rule property returns the correct format."""
        link1 = ResourceLink({"kind": "test_kind", "instance": "instance1"})
        assert link1.rule == "test_kind.instance1.DEFAULT"

        link2 = ResourceLink({"kind": "test_kind"})
        assert link2.rule == "test_kind.ANY.DEFAULT"

    def test_resource_property(self):
        """Test the resource property returns the parent resource."""
        resource = Resource("test_resource")
        link = ResourceLink({"kind": "test_kind"}, parent=resource)

        assert link.resource == resource


class TestResourceProviderLink:
    """Unit tests for the ResourceProviderLink class."""

    def test_provider_link_initialization(self):
        """Test initializing a provider link."""
        provider = ResourceProviderLink({"kind": "capability"})

        assert provider.kind == "capability"
        assert isinstance(provider, ResourceLink)


class TestResourceRequireLink:
    """Unit tests for the ResourceRequireLink class."""

    @pytest.fixture
    def provider_links(self):
        """Fixture providing a list of provider links for testing."""
        return [
            ResourceProviderLink({"kind": "db", "instance": "default"}),
            ResourceProviderLink({"kind": "db", "instance": "mysql"}),
            ResourceProviderLink({"kind": "db", "instance": "postgres"}),
            ResourceProviderLink({"kind": "cache", "instance": "redis"}),
            ResourceProviderLink({"kind": "auth", "instance": "oauth"}),
        ]

    def test_require_link_match_exact(self, provider_links):
        """Test matching a requirement to an exact provider."""
        requirement = ResourceRequireLink({"kind": "db", "instance": "mysql"})

        # Match exact provider
        instance, matches = requirement.match_provider(provider_links)

        assert instance == "mysql"
        assert len(matches) == 1
        assert matches[0].kind == "db"
        assert matches[0].instance == "mysql"

    def test_require_link_match_kind_only(self, provider_links):
        """Test matching a requirement by kind only."""

        requirement = ResourceRequireLink({"kind": "db", "mod": "!"})

        # Match by kind only
        instance, matches = requirement.match_provider(provider_links)

        # Should match the default
        assert instance == requirement.default_providers_name
        assert len(matches) == 1  # Only default db provider

    def test_require_link_with_modifiers(self, provider_links):
        """Explicit link modifiers win over default_mode='one' (resolver default)."""
        # "!" — exactly one of the remapped default instance
        req_one = ResourceRequireLink("db.!")
        _instance, matches = req_one.match_provider(
            provider_links, default_mode="one"
        )
        assert len(matches) == 1
        assert matches[0].instance == "default"

        # "?" — zero matches allowed
        req_optional = ResourceRequireLink("missing.?")
        _instance, matches = req_optional.match_provider(
            provider_links, default_mode="one"
        )
        assert matches == []

        # "+" — one or more of remapped default instance
        req_many = ResourceRequireLink("db.+")
        _instance, matches = req_many.match_provider(
            provider_links, default_mode="one"
        )
        assert len(matches) == 1
        assert matches[0].instance == "default"

        # "*" — zero matches allowed (catalog apps with no web_app providers)
        req_any = ResourceRequireLink("missing.*")
        _instance, matches = req_any.match_provider(
            provider_links, default_mode="one"
        )
        assert matches == []

    def test_explicit_star_mod_allows_zero_matches_with_default_mode_one(self):
        """Regression: web_app.* must not be forced to exactly-one by default_mode."""
        requirement = ResourceRequireLink("web_app.*")
        _instance, matches = requirement.match_provider([], default_mode="one")
        assert matches == []

    def test_explicit_question_mod_allows_zero_matches_with_default_mode_one(self):
        """Regression: KIND.? must honor optional cardinality over default_mode."""
        requirement = ResourceRequireLink("expose_admin.?")
        _instance, matches = requirement.match_provider([], default_mode="one")
        assert matches == []

    def test_absent_mod_still_uses_default_mode_one(self):
        """When the link has no modifier, default_mode='one' still applies."""
        requirement = ResourceRequireLink("web_app")
        with pytest.raises(ResourceLinkError, match="exactly one provider"):
            requirement.match_provider([], default_mode="one")

    def test_explicit_bang_still_requires_one_with_default_mode_one(self):
        """Explicit ! must keep failing on zero matches."""
        requirement = ResourceRequireLink("web_app.!")
        with pytest.raises(ResourceLinkError, match="exactly one provider"):
            requirement.match_provider([], default_mode="one")

    def test_require_link_validation_errors(self, provider_links):
        """Test validation errors when modifiers' requirements aren't met."""
        # Test "!" (one) modifier with no matches
        req_one = ResourceRequireLink("missing.!")
        with pytest.raises(ResourceLinkError):
            req_one.match_provider(provider_links, default_mode="one")

        # Test "+" (one_or_many) modifier with no matches
        req_many = ResourceRequireLink("missing.+")
        with pytest.raises(ResourceLinkError):
            req_many.match_provider(provider_links, default_mode="one")

    def test_remapping_rules(self, provider_links):
        """Test requirement remapping rules."""
        requirement = ResourceRequireLink({"kind": "db"})

        # Define remap rules to prefer postgres
        remap_rules = {"db": "postgres"}

        # Match with remapping
        instance, matches = requirement.match_provider(
            provider_links, remap_rules=remap_rules
        )

        assert instance == "postgres"
        assert len(matches) == 1
        assert matches[0].instance == "postgres"
