# Defining Resources

This tutorial explores how to define resources and their relationships in more detail.

## Resource Structure

A resource in the Resource Manager system has the following key attributes:

- `name`: A unique identifier for the resource
- `scope`: An optional namespace or category
- `provides`: A list of capabilities this resource provides to others
- `requires`: A list of capabilities this resource needs from others
- Additional custom attributes (like `desc`, `vars`, etc.)

## Creating Resources

There are multiple ways to create resources:

### 1. Direct Instantiation

```python
from resource_manager.resources import Resource

# Create a resource directly
db_resource = Resource(
    name="database",
    scope="app",
    provides=[{"kind": "database", "instance": "main"}],
    requires=[{"kind": "storage", "instance": "fast"}],
    desc="PostgreSQL database"
)
```

### 2. Through ResourceManager

```python
from resource_manager.resources import ResourceManager

# Create a resource manager
manager = ResourceManager()

# Add a resource using dictionary config
manager.add_resource(
    "database",
    scope="app",
    config={
        "provides": [{"kind": "database", "instance": "main"}],
        "requires": [{"kind": "storage", "instance": "fast"}],
        "desc": "PostgreSQL database",
        "vars": {
            "port": 5432,
            "version": "13"
        }
    }
)
```

### 3. Adding Multiple Resources

```python
# Add multiple resources at once
resources_config = {
    "database": {
        "provides": ["database.main"],
        "requires": ["storage.fast"],
        "desc": "PostgreSQL database"
    },
    "application": {
        "provides": ["app.web"],
        "requires": ["database.main"],
        "desc": "Web application"
    }
}

manager.add_resources(resources_config, scope="app")
```

## Provider and Requirement Links

Provider and requirement links define the relationships between resources.

### Link Syntax

Links can be defined in several formats:

#### 1. String Format

The simplest way is to use strings with the format `kind.instance.modifier`:

```python
# Provide a database capability
"database.main"

# Require exactly one database
"database.main!"

# Require zero or one storage
"storage.fast?"

# Require one or more cache instances
"cache.memory+"

# Accept any number of logging services
"logging.service*"
```

#### 2. Dictionary Format

For more control, use dictionaries:

```python
# Provide a database capability
{"kind": "database", "instance": "main"}

# Require exactly one database
{"kind": "database", "instance": "main", "mod": "!"}

# Using long-form modifiers
{"kind": "storage", "instance": "fast", "mod": "zero_or_one"}
```

### Cardinality Modifiers

Modifiers control how many providers are required:

- `!` or `one`: Exactly one match required
- `?` or `zero_or_one`: Zero or one match required
- `+` or `one_or_many`: One or more matches required
- `*` or `zero_or_many`: Any number of matches allowed

If no modifier is specified, `!` (exactly one) is used by default.

## Specialized Resource Classes

You can extend the `Resource` class to add custom functionality:

```python
from resource_manager.resources import Resource

class DatabaseResource(Resource):
    default_attrs = {
        "port": 5432,
        "version": "13",
        "storage_type": "ssd"
    }
    
    def validate_connection(self):
        # Custom logic for database resources
        print(f"Validating connection to {self.name} on port {self.port}")

# Create custom resource
db = DatabaseResource(
    name="postgres",
    scope="app",
    provides=["database.main"],
    port=5433  # Override default attributes
)

# Access custom attributes
print(db.port)        # 5433
print(db.version)     # "13"
print(db.storage_type)  # "ssd"

# Call custom methods
db.validate_connection()
```

## Custom Resource Managers

Similarly, you can extend `ResourceManager` to customize behavior:

```python
from resource_manager.resources import ResourceManager, Resource

class CustomResource(Resource):
    default_attrs = {
        "priority": "medium"
    }

class CustomResourceManager(ResourceManager):
    resource_class = CustomResource  # Use our custom resource class
    
    def get_high_priority_resources(self):
        return [r for r in self.catalog.values() if r.priority == "high"]

# Create custom manager
custom_manager = CustomResourceManager()

# Add resources (will be CustomResource instances)
custom_manager.add_resource(
    "important_service",
    config={"priority": "high", "provides": ["service.important"]}
)

# Use custom methods
high_priority = custom_manager.get_high_priority_resources()
```

## Practical Example

Let's define a more complex application with multiple components:

```python
from resource_manager.resources import ResourceManager

# Create a resource manager
manager = ResourceManager()

# Define resources for a web application stack
resources = {
    "postgres": {
        "desc": "PostgreSQL database",
        "provides": ["database.main", "database.metrics"],
        "group": "storage"
    },
    "redis": {
        "desc": "Redis cache",
        "provides": ["cache.main", "pubsub.events"],
        "group": "storage"
    },
    "backend": {
        "desc": "API backend service",
        "requires": ["database.main", "cache.main"],
        "provides": ["api.rest", "api.graphql"],
        "group": "application"
    },
    "frontend": {
        "desc": "React frontend",
        "requires": ["api.rest"],
        "provides": ["ui.web"],
        "group": "application"
    },
    "nginx": {
        "desc": "Nginx web server",
        "requires": ["ui.web", "api.graphql"],
        "provides": ["ingress.http"],
        "group": "network"
    },
    "certbot": {
        "desc": "Let's Encrypt certificate manager",
        "requires": ["ingress.http"],
        "provides": ["ssl.certificates"],
        "group": "security"
    }
}

# Add all resources
manager.add_resources(resources, scope="production")

# Verify resources
for resource in manager:
    print(f"Resource: {resource.name} ({resource.group})")
    print(f"  Provides: {[p.rule for p in resource.provides]}")
    print(f"  Requires: {[r.rule for r in resource.requires]}")
```

## Next Steps

Now that you know how to define resources, let's move on to [dependency resolution](04_dependency_resolution.md) to learn how dependencies are resolved and the correct initialization order is determined. 