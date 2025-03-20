"""
Integration tests for the resource manager and resolver.
"""

import os

import pytest

from resource_manager.resolver import DepBuilder
from resource_manager.resources import ResourceManager


class TestEndToEndWorkflow:
    """Integration tests for end-to-end resource dependency resolution."""

    def test_complete_workflow(self):
        """Test a complete resource manager workflow from creation to resolution."""
        # 1. Create a resource manager
        manager = ResourceManager()

        # 2. Define resources with dependencies
        manager.add_resource(
            "database",
            config={
                "desc": "Database service",
                "provides": ["database.main", "storage.persistent"],
            },
        )

        manager.add_resource(
            "cache",
            config={
                "desc": "Cache service",
                "provides": ["cache.memory", "storage.temporary"],
            },
        )

        manager.add_resource(
            "auth_service",
            config={
                "desc": "Authentication service",
                "requires": ["database.main"],
                "provides": ["auth.provider", "api.auth"],
            },
        )

        manager.add_resource(
            "api_gateway",
            config={
                "desc": "API Gateway",
                "requires": ["auth.provider", "cache.memory"],
                "provides": ["api.gateway"],
            },
        )

        manager.add_resource(
            "web_app",
            config={
                "desc": "Web Application",
                "requires": ["api.gateway", "storage.persistent", "storage.temporary"],
                "provides": ["ui.web"],
            },
        )

        # 3. Create a dependency resolver and resolve dependencies
        resolver = DepBuilder(resources=manager, feature_names=["ui.web"])
        resolver.resolve()

        # 4. Verify resolution was successful
        assert resolver.resolved
        assert resolver.dep_order is not None

        # 5. Verify the dependency order makes sense
        # Database and cache should come before auth_service and api_gateway
        db_idx = resolver.dep_order.index("database")
        cache_idx = resolver.dep_order.index("cache")
        auth_idx = resolver.dep_order.index("auth_service")
        api_idx = resolver.dep_order.index("api_gateway")
        web_idx = resolver.dep_order.index("web_app")

        # Database should come before auth_service
        assert db_idx < auth_idx

        # Cache should come before api_gateway
        assert cache_idx < api_idx

        # Auth and cache should come before api_gateway
        assert auth_idx < web_idx
        assert api_idx < web_idx

    def test_cyclic_dependency_detection(self):
        """Test that cyclic dependencies are detected and reported."""
        # Create a resource manager with cyclic dependencies
        manager = ResourceManager()

        # Resource A requires B, B requires C, C requires A - forming a cycle
        manager.add_resource(
            "resource_a",
            config={"provides": ["capability.a"], "requires": ["capability.b"]},
        )

        manager.add_resource(
            "resource_b",
            config={"provides": ["capability.b"], "requires": ["capability.c"]},
        )

        manager.add_resource(
            "resource_c",
            config={"provides": ["capability.c"], "requires": ["capability.a"]},
        )

        # Create resolver
        resolver = DepBuilder(resources=manager, feature_names=["capability.a"])

        # Resolution should fail due to cyclic dependency
        with pytest.raises(Exception) as excinfo:
            resolver.resolve()

        # Verify the error is related to cyclic dependency
        # The exact error might vary based on the implementation
        error_str = str(excinfo.value)
        assert any(term in error_str.lower() for term in ["cycle", "circular", "loop"])

    def test_complex_dependency_graph(self, tmp_path):
        """Test resolution of a complex dependency graph with multiple paths."""
        # Create a resource manager with a complex dependency graph
        manager = ResourceManager()

        # Define a more complex graph structure
        resources = {
            "database_primary": {"provides": ["db.primary"]},
            "database_replica": {
                "requires": ["db.primary"],
                "provides": ["db.replica"],
            },
            "cache_service": {"provides": ["cache.main"]},
            "auth_service": {"requires": ["db.primary"], "provides": ["auth.provider"]},
            "user_service": {
                "requires": ["db.replica", "cache.main"],
                "provides": ["service.user"],
            },
            "content_service": {
                "requires": ["db.primary", "cache.main"],
                "provides": ["service.content"],
            },
            "api_gateway": {
                "requires": ["auth.provider", "service.user", "service.content"],
                "provides": ["api.gateway"],
            },
            "web_frontend": {"requires": ["api.gateway"], "provides": ["ui.web"]},
            "mobile_frontend": {"requires": ["api.gateway"], "provides": ["ui.mobile"]},
        }

        # Add all resources
        for name, config in resources.items():
            manager.add_resource(name, config=config)

        # Create resolver for both web and mobile UI
        resolver = DepBuilder(resources=manager, feature_names=["ui.web", "ui.mobile"])
        resolver.resolve()

        # Verify resolution was successful
        assert resolver.resolved
        assert resolver.dep_order is not None

        # Verify dependency order
        dep_order = resolver.dep_order

        # Basic dependency checks based on the graph
        assert dep_order.index("database_primary") < dep_order.index("database_replica")
        assert dep_order.index("database_primary") < dep_order.index("auth_service")
        assert dep_order.index("auth_service") < dep_order.index("api_gateway")
        assert dep_order.index("api_gateway") < dep_order.index("web_frontend")
        assert dep_order.index("api_gateway") < dep_order.index("mobile_frontend")

        # Generate a visualization if not in CI environment
        if not os.environ.get("CI"):
            try:
                resolver.gen_graph(output_file=str(tmp_path / "complex_graph.png"))
            # pylint: disable=broad-exception-caught
            except Exception:
                # Skip graph generation if it fails
                pass

    def test_partial_resolution(self):
        """Test resolving only part of the dependency graph."""
        # Create a resource manager
        manager = ResourceManager()

        # Define resources
        resources = {
            "database": {"provides": ["db.main"]},
            "auth_service": {"requires": ["db.main"], "provides": ["auth.provider"]},
            "user_service": {"requires": ["db.main"], "provides": ["service.user"]},
            "admin_panel": {
                "requires": ["auth.provider", "service.user"],
                "provides": ["ui.admin"],
            },
            "public_website": {"requires": ["service.user"], "provides": ["ui.public"]},
        }

        # Add all resources
        for name, config in resources.items():
            manager.add_resource(name, config=config)

        # Resolve only the public website dependencies
        resolver1 = DepBuilder(resources=manager, feature_names=["ui.public"])
        resolver1.resolve()

        # Verify public website resolution
        assert "public_website" in resolver1.dep_order
        assert "user_service" in resolver1.dep_order
        assert "database" in resolver1.dep_order

        # Admin panel should not be needed
        assert "admin_panel" not in resolver1.dep_order

        # Resolve only the admin panel dependencies
        resolver2 = DepBuilder(resources=manager, feature_names=["ui.admin"])
        resolver2.resolve()

        # Verify admin panel resolution
        assert "admin_panel" in resolver2.dep_order
        assert "auth_service" in resolver2.dep_order
        assert "user_service" in resolver2.dep_order
        assert "database" in resolver2.dep_order
