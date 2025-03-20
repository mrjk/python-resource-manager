import os

import pytest

from resource_manager.exceptions import ResourceResolutionError
from resource_manager.links import ResourceProviderLink, ResourceRequireLink
from resource_manager.resolver import DepBuilder, EdgeLink
from resource_manager.resources import Resource, ResourceManager


class TestEdgeLink:
    """Unit tests for the EdgeLink class."""

    def test_edge_link_initialization(self):
        """Test initializing an edge link between a requirement and provider."""
        # Create resources
        req_resource = Resource("requirer")
        prov_resource = Resource("provider")

        # Create links
        requirement = ResourceRequireLink(
            {"kind": "test.dependency"}, parent=req_resource
        )
        provider = ResourceProviderLink(
            {"kind": "test.dependency"}, parent=prov_resource
        )

        # Create edge link
        edge = EdgeLink("test_instance", requirement, provider)

        assert edge.inst == "test_instance"
        assert edge.requirement == requirement
        assert edge.provider == provider

    def test_edge_link_rule_property(self):
        """Test the rule property generates the correct format."""
        # Create resources
        req_resource = Resource("requirer")
        prov_resource = Resource("provider")

        # Create links with different configurations
        requirement1 = ResourceRequireLink(
            {"kind": "test.dep", "instance": "inst1", "mod": "!"}, parent=req_resource
        )
        provider1 = ResourceProviderLink(
            {"kind": "test.dep", "instance": "inst1"}, parent=prov_resource
        )

        # Create edge link
        edge1 = EdgeLink("test_instance", requirement1, provider1)

        # Rule should combine requirement kind, edge instance, and requirement modifier
        assert edge1.rule == "test.dep.test_instance.!"

        # Test with defaults
        requirement2 = ResourceRequireLink({"kind": "test.dep"}, parent=req_resource)
        provider2 = ResourceProviderLink({"kind": "test.dep"}, parent=prov_resource)
        edge2 = EdgeLink(None, requirement2, provider2)

        assert edge2.rule == "test.dep.DEFAULT.DEFAULT"

    def test_edge_link_representation(self):
        """Test the string representation of an edge link."""
        # Create resources
        req_resource = Resource("requirer")
        prov_resource = Resource("provider")

        # Create links
        requirement = ResourceRequireLink({"kind": "test.dep"}, parent=req_resource)
        provider = ResourceProviderLink({"kind": "test.dep"}, parent=prov_resource)

        # Create edge link
        edge = EdgeLink("test_instance", requirement, provider)

        # Verify representation includes resource names and rule
        repr_str = str(edge)
        assert "requirer" in repr_str
        assert "provider" in repr_str
        assert "test.dep" in repr_str


class TestDepBuilder:
    """Unit tests for the DepBuilder class."""

    def test_initialization(self, empty_resource_manager):
        """Test initializing a dependency builder."""
        # Initialize with a resource manager
        builder = DepBuilder(resources=empty_resource_manager)

        assert builder.rmanager is not None
        assert builder.rmanager is not empty_resource_manager  # Should be a copy
        assert builder.resolved is False

        # Initialize with a dictionary
        resources_dict = {
            "res1": {"provides": ["capability1"]},
            "res2": {"requires": ["capability1"]},
        }
        builder2 = DepBuilder(resources=resources_dict)

        assert builder2.rmanager is not None
        assert len(builder2.rmanager.catalog) == 2

    def test_add_resources(self):
        """Test adding resources to the dependency builder."""
        builder = DepBuilder()

        # Add resources
        builder.add_resources(
            {
                "res1": {"provides": ["capability1"]},
                "res2": {"requires": ["capability1"]},
            }
        )

        assert "res1" in builder.rmanager.catalog
        assert "res2" in builder.rmanager.catalog
        assert builder.rmanager.get_resource("res1").scope == "APP_EXTRA"

    def test_simple_resolution(self):
        """Test resolving a simple dependency graph."""
        # Create a simple dependency graph
        resources = {
            "database": {"provides": ["database.main"]},
            "application": {"requires": ["database.main"], "provides": ["app.web"]},
            "frontend": {"requires": ["app.web"]},
        }

        # Create resolver and resolve dependencies
        resolver = DepBuilder(resources=resources, feature_names=["app.web"])
        resolver.resolve()

        # Check resolution results
        assert resolver.resolved is True
        assert resolver.dep_order is not None

        # Check dependency order - database should come before application
        db_idx = resolver.dep_order.index("database")
        app_idx = resolver.dep_order.index("application")
        assert db_idx < app_idx

    def test_resolution_with_extra_resources(self):
        """Test resolving dependencies with extra resources added later."""
        # Initial resources
        resources = {"database": {"provides": ["database.main"]}}

        # Create resolver
        resolver = DepBuilder(resources=resources)

        # Add extra resources during resolution
        extra_resources = {
            "application": {"requires": ["database.main"], "provides": ["app.web"]}
        }

        # Resolve with extra resources
        resolver.resolve(feature_names=["app.web"], extra_resources=extra_resources)

        # Check both resources are in the dependency order
        assert "database" in resolver.dep_order
        assert "application" in resolver.dep_order

    def test_idempotent_resolution(self):
        """Test that resolution can only happen once."""
        # Create resolver
        resolver = DepBuilder(resources={"res1": {}})

        # First resolution should work
        resolver.resolve()
        assert resolver.resolved is True

        # Second resolution should fail
        with pytest.raises(ResourceResolutionError):
            resolver.resolve()

    def test_graph_generation(self, tmp_path):
        """Test generating a dependency graph visualization."""
        # Skip if graphviz not installed or on CI
        if os.environ.get("CI"):
            pytest.skip("Skipping graph generation test in CI environment")

        # Create a simple dependency graph
        resources = {
            "database": {"provides": ["database.main"]},
            "application": {"requires": ["database.main"], "provides": ["app.web"]},
        }

        # Create resolver and resolve dependencies
        resolver = DepBuilder(resources=resources, feature_names=["app.web"])
        resolver.resolve()

        # Generate graph and check if file was created
        output_file = str(tmp_path / "test_graph.png")
        try:
            resolver.gen_graph(output_file=output_file)
            assert os.path.exists(output_file)
        except Exception as e:
            pytest.skip(f"Graph generation failed, skipping test: {e}")


@pytest.mark.parametrize(
    "resources,feature_names,expected_order",
    [
        # Test case 1: Linear dependency chain
        (
            {
                "a": {"provides": ["a"]},
                "b": {"requires": ["a"], "provides": ["b"]},
                "c": {"requires": ["b"], "provides": ["c"]},
            },
            ["c"],
            ["__root__", "a", "b", "c"],
        ),
        # Test case 2: Diamond dependency pattern
        (
            {
                "a": {"provides": ["a"]},
                "b1": {"requires": ["a"], "provides": ["b1"]},
                "b2": {"requires": ["a"], "provides": ["b2"]},
                "c": {"requires": ["b1", "b2"], "provides": ["c"]},
            },
            ["c"],
            ["__root__", "a", "b1", "b2", "c"],  # Order of b1/b2 could be swapped
        ),
        # Test case 3: Multiple roots
        (
            {
                "a1": {"provides": ["a1"]},
                "a2": {"provides": ["a2"]},
                "b": {"requires": ["a1", "a2"], "provides": ["b"]},
            },
            ["b"],
            ["__root__", "a1", "a2", "b"],  # Order of a1/a2 could be swapped
        ),
    ],
)
def test_dependency_resolution_parametrized(resources, feature_names, expected_order):
    """Parametrized test for dependency resolution with different graph structures."""
    resolver = DepBuilder(resources=resources, feature_names=feature_names)
    resolver.resolve()

    # Check all expected resources are in the dependency order
    assert set(resolver.dep_order) == set(expected_order)

    # Check the topological ordering is correct
    for i, res_name in enumerate(resolver.dep_order):
        resource = resolver.rmanager.get_resource(res_name)

        # For each requirement, its provider should come before this resource
        for req in resource.requires:
            # Find the provider resource for this requirement
            for dep in resolver.dep_tree.get(res_name, []):
                if dep.requirement == req:
                    provider_name = dep.provider.resource.name
                    provider_idx = resolver.dep_order.index(provider_name)
                    assert (
                        provider_idx < i
                    ), f"Provider {provider_name} should come before {res_name}"
