"""
Performance benchmarks for the resource manager and resolver.
"""

import pytest

from resource_manager.resolver import DepBuilder
from resource_manager.resources import ResourceManager


def generate_large_resource_set(size):
    """Generate a large set of resources for performance testing."""
    resources = {}

    # Create base resources
    for i in range(size // 10):
        resources[f"base_{i}"] = {"provides": [f"base.capability_{i}"], "requires": []}

    # Create mid-level resources
    for i in range(size // 5):
        base_deps = [f"base.capability_{i % (size // 10)}"]
        resources[f"mid_{i}"] = {
            "provides": [f"mid.capability_{i}"],
            "requires": base_deps,
        }

    # Create top-level resources
    for i in range(size - len(resources)):
        # Each top resource depends on 1-3 mid resources
        mid_deps = [
            f"mid.capability_{(i + j) % (size // 5)}"
            for j in range(min(3, (size // 5)))
        ]
        resources[f"top_{i}"] = {
            "provides": [f"top.capability_{i}"],
            "requires": mid_deps,
        }

    return resources


@pytest.mark.benchmark
class TestResourceManagerPerformance:
    """Performance benchmarks for the ResourceManager class."""

    def test_add_resource_performance(self, benchmark):
        """Benchmark adding a resource to the manager."""

        def setup():
            return ResourceManager(), "test_resource", {"provides": ["capability"]}

        def add_resource(manager, name, config):
            manager.add_resource(name, config=config, force=True)

        benchmark(add_resource, *setup())

    def test_add_multiple_resources_performance(self, benchmark):
        """Benchmark adding multiple resources to the manager."""

        def setup():
            return ResourceManager(), generate_large_resource_set(10)

        def add_resources(manager, resources):
            manager.add_resources(resources, force=True)

        benchmark(add_resources, *setup())

    def test_get_resource_performance(self, benchmark):
        """Benchmark retrieving a resource from the manager."""

        def setup():
            manager = ResourceManager()
            resources = generate_large_resource_set(100)
            manager.add_resources(resources)
            return manager, list(resources.keys())[50]  # Get a resource in the middle

        def get_resource(manager, name):
            return manager.get_resource(name)

        benchmark(get_resource, *setup())

    def test_get_resources_by_scope_performance(self, benchmark):
        """Benchmark retrieving resources by scope."""

        def setup():
            manager = ResourceManager()
            resources = generate_large_resource_set(100)

            # Add resources with different scopes
            for i, (name, config) in enumerate(resources.items()):
                scope = f"scope_{i % 5}"
                manager.add_resource(name, scope=scope, config=config)

            return manager, "scope_2"  # Get resources from a specific scope

        def get_resources_by_scope(manager, scope):
            return manager.get_resources(scope=scope)

        benchmark(get_resources_by_scope, *setup())


@pytest.mark.benchmark
class TestResolverPerformance:
    """Performance benchmarks for the DepBuilder class."""

    @pytest.mark.parametrize("size", [10, 30, 30])
    def test_resolution_performance(self, benchmark, size):
        """Benchmark dependency resolution with different graph sizes."""

        def setup():
            resources = generate_large_resource_set(size)
            # Use a feature from a top-level resource for resolution
            feature = f"top.capability_{size // 2}"
            return resources, [feature]

        def resolve_dependencies(resources, feature_names):
            resolver = DepBuilder(resources=resources, feature_names=feature_names)
            resolver.resolve()
            return resolver.dep_order

        benchmark(resolve_dependencies, *setup())

    def test_resolution_with_complex_graph(self, benchmark):
        """Benchmark resolution with a complex dependency graph."""

        def setup():
            # Create a more complex dependency structure
            resources = {}

            # Create a network of resources with multiple dependencies
            for i in range(20):
                provides = [f"service.{i}"]
                # Create dependencies to form a complex graph
                requires = []

                # Each resource depends on the previous 3 (if they exist)
                for j in range(1, 4):
                    if i - j >= 0:
                        requires.append(f"service.{i-j}")

                resources[f"resource_{i}"] = {
                    "provides": provides,
                    "requires": requires,
                }

            return resources, ["service.19"]  # Request the last service

        def resolve_complex_graph(resources, feature_names):
            resolver = DepBuilder(resources=resources, feature_names=feature_names)
            resolver.resolve()
            return resolver.dep_order

        benchmark(resolve_complex_graph, *setup())

    # def test_graph_generation_performance(self, benchmark, tmp_path):
    #     """Benchmark generating dependency graphs."""
    #     def setup():
    #         resources = generate_large_resource_set(50)
    #         resolver = DepBuilder(resources=resources, feature_names=[f"top.capability_{10}"])
    #         resolver.resolve()
    #         return resolver, str(tmp_path / "benchmark_graph.png")

    #     def generate_graph(resolver, output_file):
    #         try:
    #             resolver.gen_graph(output_file=output_file)
    #         except Exception:
    #             # Skip if graph generation fails (e.g., no graphviz)
    #             pass

    #     benchmark(generate_graph, *setup())
