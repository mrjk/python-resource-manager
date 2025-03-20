import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from resource_manager.exceptions import ResourceResolutionError
from resource_manager.links import ResourceProviderLink, ResourceRequireLink
from resource_manager.resolver import DepBuilder
from resource_manager.resources import Resource, ResourceManager

# Define strategies for generating test data


@st.composite
def resource_names(draw):
    """Strategy to generate valid resource names."""
    return draw(
        st.text(
            alphabet=st.characters(
                whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters="_"
            ),
            min_size=1,
            max_size=20,
        ).filter(lambda x: x and not x[0].isdigit())
    )


@st.composite
def capability_names(draw):
    """Strategy to generate capability/requirement names."""
    prefix = draw(resource_names())
    suffix = draw(resource_names())
    return f"{prefix}.{suffix}"


@st.composite
def resource_configs(
    draw, min_provides=0, max_provides=5, min_requires=0, max_requires=5
):
    """Strategy to generate resource configurations."""
    num_provides = draw(st.integers(min_value=min_provides, max_value=max_provides))
    num_requires = draw(st.integers(min_value=min_requires, max_value=max_requires))

    provides = draw(
        st.lists(
            capability_names(),
            min_size=num_provides,
            max_size=num_provides,
            unique=True,
        )
    )
    requires = draw(
        st.lists(
            capability_names(),
            min_size=num_requires,
            max_size=num_requires,
            unique=True,
        )
    )

    return {"provides": provides, "requires": requires}


@st.composite
def resource_collections(draw, min_resources=1, max_resources=10):
    """Strategy to generate collections of resources."""
    num_resources = draw(st.integers(min_value=min_resources, max_value=max_resources))
    names = draw(
        st.lists(
            resource_names(),
            min_size=num_resources,
            max_size=num_resources,
            unique=True,
        )
    )

    resources = {}
    for name in names:
        # Ensure at least one resource provides capabilities
        if len(resources) == 0:
            config = draw(resource_configs(min_provides=1))
        else:
            config = draw(resource_configs())
        resources[name] = config

    return resources


@st.composite
def resolvable_resource_collections(draw):
    """Strategy to generate resource collections that can be resolved."""
    # Start with a base resource that provides a capability
    base_name = draw(resource_names())
    base_capability = draw(capability_names())

    resources = {base_name: {"provides": [base_capability], "requires": []}}

    # Add a chain of dependent resources
    num_chain = draw(st.integers(min_value=1, max_value=5))
    current_capability = base_capability

    for i in range(num_chain):
        resource_name = draw(resource_names().filter(lambda x: x not in resources))
        new_capability = draw(capability_names())

        resources[resource_name] = {
            "provides": [new_capability],
            "requires": [current_capability],
        }

        current_capability = new_capability

    # The last capability in the chain is our target feature
    feature_names = [current_capability]

    # Optionally add some more resources with random dependencies
    num_extra = draw(st.integers(min_value=0, max_value=3))
    for i in range(num_extra):
        resource_name = draw(resource_names().filter(lambda x: x not in resources))
        provided = list(resources.values())
        all_capabilities = [cap for res in provided for cap in res.get("provides", [])]

        # Only require capabilities that are provided by other resources
        num_requires = draw(
            st.integers(min_value=0, max_value=min(3, len(all_capabilities)))
        )
        requires = draw(
            st.sampled_from(all_capabilities) if all_capabilities else st.just([])
        )

        resources[resource_name] = {
            "provides": [draw(capability_names())],
            "requires": requires if isinstance(requires, list) else [requires],
        }

    return resources, feature_names


class TestResourceManagerProperties:
    """Property-based tests for the ResourceManager class."""

    @given(name=resource_names(), config=resource_configs())
    @settings(max_examples=50)
    def test_add_resource_properties(self, name, config):
        """Test that any valid resource can be added to a manager."""
        manager = ResourceManager()

        # Add the resource
        manager.add_resource(name, config=config)

        # Verify it was added correctly
        assert name in manager.catalog
        resource = manager.get_resource(name)

        # Check provides links were created correctly
        assert len(resource.provides) == len(config["provides"])
        for i, provider in enumerate(resource.provides):
            assert provider.kind in config["provides"][i]

        # Check requires links were created correctly
        assert len(resource.requires) == len(config["requires"])
        for i, requirement in enumerate(resource.requires):
            assert requirement.kind in config["requires"][i]

    @given(resources=resource_collections(min_resources=2, max_resources=10))
    @settings(max_examples=5)
    def test_add_resources_properties(self, resources):
        """Test that collections of resources can be added to a manager."""
        manager = ResourceManager()

        # Add all resources
        manager.add_resources(resources)

        # Verify all resources were added
        for name in resources:
            assert name in manager.catalog

            resource = manager.get_resource(name)
            config = resources[name]

            assert len(resource.provides) == len(config["provides"])
            assert len(resource.requires) == len(config["requires"])


class TestResolverProperties:
    """Property-based tests for the DepBuilder class."""

    @given(data=resolvable_resource_collections())
    @settings(max_examples=5)
    def test_resolution_properties(self, data):
        """Test resolution with generated resource collections."""
        resources, feature_names = data

        # Create resource manager and add resources
        manager = ResourceManager()
        for name, config in resources.items():
            manager.add_resource(name, config=config)

        # Create resolver and resolve
        resolver = DepBuilder(resources=manager, feature_names=feature_names)
        resolver.resolve()

        # Verify resolution was successful
        assert resolver.resolved
        assert resolver.dep_order is not None

        # Check that all resources with requirements have their providers
        # appear before them in the dependency order
        for i, res_name in enumerate(resolver.dep_order):
            resource = resolver.rmanager.get_resource(res_name)

            # For each requirement, find its provider
            for req in resource.requires:
                # Find matching provider resource(s)
                providers = []
                for other_name in resolver.dep_order:
                    if other_name == res_name:
                        continue

                    other = resolver.rmanager.get_resource(other_name)
                    for prov in other.provides:
                        if prov.kind == req.kind:
                            providers.append(other_name)

                # If we found providers, they should come before this resource
                for provider_name in providers:
                    provider_idx = resolver.dep_order.index(provider_name)
                    assert (
                        provider_idx < i
                    ), f"Provider {provider_name} should come before {res_name}"


class TestEdgeCases:
    """Tests for edge cases in the resource manager system."""

    def test_empty_resolver(self):
        """Test resolution with an empty resource manager."""
        resolver = DepBuilder()

        # Resolution should succeed but not include any resources
        resolver.resolve()
        assert resolver.resolved
        assert resolver.dep_order is not None
        assert len(resolver.dep_order) == 1

    def test_unrequired_features(self):
        """Test resolution with features that aren't required by anything."""
        manager = ResourceManager()

        # Add resources that provide features but aren't required
        manager.add_resource("resource1", config={"provides": ["feature1", "feature2"]})

        manager.add_resource("resource2", config={"provides": ["feature3"]})

        # Resolve with a feature that is provided but not required
        resolver = DepBuilder(resources=manager, feature_names=["feature1"])
        resolver.resolve()

        # Resolution should succeed and include only resource1
        assert resolver.resolved
        assert "resource1" in resolver.dep_order
        assert "resource2" not in resolver.dep_order
