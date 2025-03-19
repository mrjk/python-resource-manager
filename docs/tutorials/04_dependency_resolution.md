# Dependency Resolution

This tutorial explains how the Resource Manager resolves dependencies between resources and determines the correct initialization order.

## Understanding Dependency Resolution

Dependency resolution is the process of:

1. Building a complete dependency graph between resources
2. Matching requirements with compatible providers
3. Determining the correct initialization order
4. Validating that all requirements are satisfied

## The DepBuilder Class

The main class for dependency resolution is `DepBuilder`, which manages the entire resolution process:

```python
from resource_manager.resolver import DepBuilder
from resource_manager.resources import ResourceManager

# Create a resource manager with resources
manager = ResourceManager()
# ... add resources ...

# Create a dependency resolver
resolver = DepBuilder(
    resources=manager,           # ResourceManager with resources
    feature_names=["app.web"],   # Requirements to start resolution from
    remap_rules={"database": "primary"},  # Rules for remapping instance names
    debug=True                   # Enable debug output
)

# Resolve dependencies
resolver.resolve()
```

## Resolution Process

Let's explore the resolution process in detail:

### 1. Building Provider Links

The first step is to collect all provider links from all resources:

```python
provider_links = resolver._build_provider_links()
```

This creates a list of `ResourceProviderLink` objects that represent capabilities provided by resources.

### 2. Building the Dependency Tree

Starting from a build context resource (which requires the specified features), the resolver recursively builds a dependency tree:

```python
dep_tree = resolver._get_dependencies()
```

This creates a dictionary where:
- Keys are resource names
- Values are lists of `EdgeLink` objects representing dependencies

An `EdgeLink` represents a connection between a requirement and a provider.

### 3. Matching Requirements with Providers

For each requirement, the resolver finds compatible providers using the `resolve_requirements` method:

```python
match_name, provider_links = resolver.resolve_requirements(requirement)
```

This method matches requirements with providers based on:
- Matching kinds (requirement kind == provider kind)
- Matching instance names (after any remapping)
- Satisfying cardinality constraints

### 4. Determining Initialization Order

Once the dependency tree is built, the resolver determines the correct initialization order using topological sorting:

```python
dep_topo = resolver._get_simplified_tree(dep_tree)
dep_order = resolver._get_dependencies_order(dep_topo)
```

The result is a list of resource names in the order they should be initialized, with dependencies coming before the resources that depend on them.

## Customizing Resolution

You can customize the resolution process by subclassing `DepBuilder` and overriding the `resolve_requirements` method:

```python
from resource_manager.resolver import DepBuilder

class CustomDepBuilder(DepBuilder):
    def resolve_requirements(self, requirement, lvl=0):
        """Custom implementation for resolving requirements."""
        # Your custom matching logic here
        # Must return (match_name, provider_links)
        
        # Example: Default implementation
        match_name, provider_links = requirement.match_provider(
            self.provider_links,
            remap_rules=self.remap_rules,
            default_mode="one",
            remap_requirement=True,
        )
        
        return match_name, provider_links
```

This allows you to implement different strategies for matching requirements with providers.

## Resolution Example

Let's walk through a complete resolution example:

```python
from resource_manager.resources import ResourceManager
from resource_manager.resolver import DepBuilder

# Create resources
manager = ResourceManager()

# Add resources
resources = {
    "postgres": {
        "desc": "PostgreSQL database",
        "provides": ["database.main"],
    },
    "redis": {
        "desc": "Redis cache",
        "provides": ["cache.main"],
    },
    "backend": {
        "desc": "API service",
        "requires": ["database.main", "cache.main"],
        "provides": ["api.rest"],
    },
    "frontend": {
        "desc": "Web app",
        "requires": ["api.rest"],
        "provides": ["ui.web"],
    }
}
manager.add_resources(resources, scope="app")

# Create resolver starting with 'ui.web' requirement
resolver = DepBuilder(
    resources=manager,
    feature_names=["ui.web"],
    debug=True
)

# Resolve dependencies
resolver.resolve()

# Print resolution results
print("Dependencies tree:")
for resource, edges in resolver.dep_tree.items():
    print(f"{resource} depends on:")
    for edge in edges:
        print(f"  {edge}")

print("\nInitialization order:", resolver.dep_order)
```

Expected output:
```
Dependencies tree:
__build_ctx__ depends on:
  EdgeLink(__build_ctx__:ui.web.DEFAULT -> frontend)
frontend depends on:
  EdgeLink(frontend:api.rest.DEFAULT -> backend)
backend depends on:
  EdgeLink(backend:database.main.DEFAULT -> postgres)
  EdgeLink(backend:cache.main.DEFAULT -> redis)
postgres depends on:
redis depends on:

Initialization order: ['postgres', 'redis', 'backend', 'frontend', '__build_ctx__']
```

## Understanding Resolution Errors

Common resolution errors include:

### 1. Missing Providers

If a requirement can't be satisfied, you'll get a `ResourceLinkError`:

```
ResourceLinkError: Requirement database.main did not match exactly one provider, 
got: 0, please chose one of: <NO OTHER CHOICES>
```

This means no provider was found for the "database.main" requirement.

### 2. Multiple Providers

If multiple providers match a requirement expecting exactly one, you'll get:

```
ResourceLinkError: Requirement database.main did not match exactly one provider, 
got: 2, please chose one of: primary secondary
```

This means two providers were found for "database.main" when only one was expected.

### 3. Cyclic Dependencies

If there are circular dependencies, topological sorting will fail:

```
CycleError: Cyclic dependency found: service_a -> service_b -> service_a
```

This means resources depend on each other in a cycle.

## Using Remapping Rules

Remapping rules allow you to resolve ambiguities when multiple providers of the same kind exist:

```python
# Create a resolver with remapping rules
resolver = DepBuilder(
    resources=manager,
    feature_names=["ui.web"],
    remap_rules={
        "database": "primary",   # Map unspecified database references to "primary" instance
        "cache": "redis",        # Map unspecified cache references to "redis" instance
    }
)
```

In this example:
- A requirement for "database" (without instance) will be mapped to "database.primary"
- A requirement for "cache" (without instance) will be mapped to "cache.redis"

## Next Steps

Now that you understand dependency resolution, let's explore [visualization techniques](05_visualization.md) to help debug and understand complex dependency relationships. 