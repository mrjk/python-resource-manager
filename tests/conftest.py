from typing import Dict

import pytest

from resource_manager.resolver import DepBuilder
from resource_manager.resources import Resource, ResourceManager


@pytest.fixture
def empty_resource_manager():
    """Fixture providing an empty ResourceManager instance."""
    return ResourceManager()


@pytest.fixture
def basic_resource():
    """Fixture providing a basic Resource instance."""
    return Resource(
        "test_resource",
        scope="test",
        provides=[{"kind": "test_capability"}],
        requires=[{"kind": "test_dependency"}],
    )


@pytest.fixture
def basic_resources_dict() -> Dict[str, Dict]:
    """Fixture providing a dictionary of basic resource configurations."""
    return {
        "resource1": {
            "provides": ["capability1", "capability2"],
            "requires": ["dependency1"],
        },
        "resource2": {"provides": ["dependency1"], "requires": []},
        "resource3": {
            "provides": ["capability3"],
            "requires": ["capability1", "capability2"],
        },
    }


@pytest.fixture
def populated_resource_manager(basic_resources_dict):
    """Fixture providing a ResourceManager with predefined resources."""
    manager = ResourceManager()
    for name, config in basic_resources_dict.items():
        manager.add_resource(name, config=config)
    return manager


@pytest.fixture
def simple_dependency_graph():
    """Fixture providing a simple dependency graph for testing resolution."""
    manager = ResourceManager()

    # Database provides a dependency
    manager.add_resource("database", config={"provides": ["database.main"]})

    # App requires database and provides web functionality
    manager.add_resource(
        "application", config={"requires": ["database.main"], "provides": ["app.web"]}
    )

    # Frontend requires web app functionality
    manager.add_resource("frontend", config={"requires": ["app.web"]})

    return manager


@pytest.fixture
def resolver_with_simple_graph(simple_dependency_graph):
    """Fixture providing a DepBuilder with a simple dependency graph."""
    return DepBuilder(resources=simple_dependency_graph, feature_names=["app.web"])
