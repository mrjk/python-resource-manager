# Resource Model

This document explains the resource model in the Resource Manager, focusing on how resources are defined, structured, and managed.

## Resource Class

The `Resource` class is the fundamental building block of the Resource Manager. It represents a configurable component with capabilities and dependencies.

### Core Attributes

Each resource has the following core attributes:

- **name**: A unique identifier for the resource
- **scope**: An optional categorization for the resource
- **provides**: A list of capabilities the resource provides to others
- **requires**: A list of dependencies the resource needs from others
- **vars**: A dictionary of configuration variables

### Attribute System

Resources have a dynamic attribute system that:

1. Allows access to variables from the `vars` dictionary as direct attributes
2. Supports a `default_attrs` class variable for setting default values
3. Makes all attributes accessible using dot notation

```python
# Example Resource class with default attributes
class CustomResource(Resource):
    default_attrs = {
        "environment": "development",
        "enabled": True,
        "priority": 0
    }
```

### Resource Configuration

Resources are typically defined through configuration dictionaries:

```python
config = {
    "desc": "Example resource",
    "provides": ["capability.example"],
    "requires": ["dependency.example"],
    "vars": {
        "port": 8080,
        "host": "localhost"
    }
}
```

## Resource Links

Resources are connected through provider and requirement links:

### Provider Links

Provider links represent capabilities a resource provides to others:

- Each provider link has a **kind** and optional **instance**
- The kind is typically a capability category (e.g., "database")
- The instance is a specific identifier within that category (e.g., "postgres")

Example provider definition:
```
"provides": ["database.postgres", "sql.engine"]
```

### Requirement Links

Requirement links represent dependencies a resource needs from others:

- Each requirement link has a **kind**, optional **instance**, and a **modifier**
- Modifiers control the cardinality (!, ?, +, *)
- Requirements can be remapped to different providers

Example requirement definition:
```
"requires": ["database.main", "cache.redis?", "logging.service*"]
```

## Resource Lifecycle

Resources go through the following lifecycle:

1. **Creation**: Instantiating a Resource object
2. **Configuration**: Setting attributes and links
3. **Resolution**: Resolving dependencies through the resolver
4. **Initialization**: Any custom initialization logic
5. **Usage**: Using the resource in the application
6. **Cleanup**: Resource cleanup when it's no longer needed

## Resource Manager

The `ResourceManager` class manages collections of resources:

1. Provides methods to add, get, and remove resources
2. Maintains a catalog of resources by name and scope
3. Handles resource configuration validation
4. Builds the initial provider and requirement links

```python
# Example ResourceManager usage
manager = ResourceManager()

# Add a resource
manager.add_resource(
    "example_resource",
    scope="application", 
    config={
        "provides": ["example.capability"],
        "requires": ["database.main"],
        "vars": {"timeout": 30}
    }
)

# Get a resource
resource = manager.get_resource("example_resource")

# Get resources by scope
app_resources = manager.get_resources(scope="application")
```

## Resource Extension

The Resource class is designed to be extended for specialized use cases:

```python
class EnvironmentAwareResource(Resource):
    default_attrs = {
        "environment": "development"
    }
    
    def is_valid_for_environment(self, target_env):
        """Check if this resource is valid for the target environment."""
        return self.environment == target_env or self.environment == "all"

class EnvironmentResourceManager(ResourceManager):
    resource_class = EnvironmentAwareResource
```

## Implementation Details

Under the hood, the Resource class:

1. Converts provider and requirement strings into `ResourceLink` objects
2. Manages attribute access through `__getattr__` and `__setattr__`
3. Handles serialization and deserialization of resource configurations
4. Provides helper methods for accessing and manipulating links

## Best Practices

When working with the resource model:

1. **Consistent Naming**: Use a consistent naming convention for resources and capabilities
2. **Clear Dependencies**: Explicitly specify all dependencies with appropriate modifiers
3. **Minimal Scope**: Keep resource capabilities focused on specific responsibilities
4. **Documentation**: Document the purpose of each resource and its requirements
5. **Validation**: Validate resource configurations early

## Related How-To Guides

For practical examples, see:
- [How to Organize Resources in Complex Applications](../resource_manager_howtos/05_organizing_resources.md)
- [How to Handle Optional Dependencies](../resource_manager_howtos/04_optional_dependencies.md) 