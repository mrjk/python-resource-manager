# Resource Manager - Basic Usage

This tutorial will walk you through a simple example of using the Resource Manager to define resources, set up dependencies, and resolve them.

## Installation

The Resource Manager can be installed via pip:

```
pip install resource_manager
```

## Import Required Classes

First, import the necessary classes from the resource manager:

```python
from resource_manager.resources import Resource, ResourceManager
from resource_manager.resolver import DepBuilder
from resource_manager.links import ResourceProviderLink, ResourceRequireLink
```

## Creating Resources

Let's start by creating a few simple resources:

```python
# Create a resource manager to hold our resources
manager = ResourceManager()

# Add a database resource
manager.add_resource(
    "database",
    scope="app",
    config={
        "desc": "PostgreSQL database",
        "provides": ["database.main"],  # This resource provides a database capability
    }
)

# Add an application resource that depends on the database
manager.add_resource(
    "application",
    scope="app",
    config={
        "desc": "Web application",
        "requires": ["database.main"],  # This resource requires a database
        "provides": ["app.web"],        # This resource provides a web app capability
    }
)

# Add a proxy resource that depends on the application
manager.add_resource(
    "proxy",
    scope="app",
    config={
        "desc": "Nginx proxy",
        "requires": ["app.web"],       # This resource requires a web app
    }
)
```

In this example:
- The database provides a "database.main" capability
- The application requires "database.main" and provides "app.web"
- The proxy requires "app.web"

## Resolving Dependencies

Now, let's resolve the dependencies:

```python
# Create a dependency resolver
resolver = DepBuilder(
    resources=manager,                 # Pass our resource manager
    feature_names=["proxy"],           # Start with the proxy resource
    debug=True                         # Enable debug output
)

# Resolve dependencies
resolver.resolve()

# Print the resolved dependency order
print("Dependency order:", resolver.dep_order)
```

The resolver will:
1. Start with the requested resource (proxy)
2. Find all required dependencies recursively
3. Determine the correct initialization order using topological sorting

The `dep_order` list will contain resources in the order they should be initialized, which in this case would be:
```
['database', 'application', 'proxy']
```

## Visualizing Dependencies

You can generate a visual representation of the dependency graph:

```python
# Generate a dependency graph
resolver.gen_graph("dependencies.png")
```

This will create a PNG image showing resources as nodes and dependencies as directed edges.

## Complete Example

Here's the complete example code:

```python
from resource_manager.resources import Resource, ResourceManager
from resource_manager.resolver import DepBuilder

# Create a resource manager
manager = ResourceManager()

# Add resources
manager.add_resource(
    "database",
    scope="app",
    config={
        "desc": "PostgreSQL database",
        "provides": ["database.main"],
    }
)

manager.add_resource(
    "application",
    scope="app",
    config={
        "desc": "Web application",
        "requires": ["database.main"],
        "provides": ["app.web"],
    }
)

manager.add_resource(
    "proxy",
    scope="app",
    config={
        "desc": "Nginx proxy",
        "requires": ["app.web"],
    }
)

# Resolve dependencies
resolver = DepBuilder(
    resources=manager,
    feature_names=["proxy"],
    debug=True
)
resolver.resolve()

# Print results
print("Dependency order:", resolver.dep_order)

# Generate visualization
resolver.gen_graph("dependencies.png")
```

## Next Steps

Now that you understand the basics, let's move on to [defining resources in more detail](03_defining_resources.md) to learn about the various ways to configure resources and their relationships. 