# How to Handle Optional Dependencies

This guide demonstrates techniques for working with optional dependencies in the Resource Manager.

## Problem

In many applications, you may have components that:

1. Can function with or without certain dependencies
2. Provide enhanced functionality when optional dependencies are available
3. Need to adapt their behavior based on which dependencies are resolved
4. Have alternative implementations for the same capability

## Solution

The Resource Manager provides several mechanisms for handling optional dependencies.

## Using Cardinality Modifiers

The simplest way to make dependencies optional is to use cardinality modifiers:

```python
from resource_manager.resources import ResourceManager
from resource_manager.resolver import DepBuilder

# Create a resource manager
manager = ResourceManager()

# Add a resource with optional dependencies
manager.add_resource(
    "web_app",
    config={
        "desc": "Web application",
        "provides": ["app.web"],
        "requires": [
            "database.main",        # Required dependency (default: !)
            "cache.redis?",         # Optional (zero or one)
            "logging.service?",     # Optional (zero or one)
            "monitoring.service*"   # Any number, including zero
        ]
    }
)

# Add required dependency
manager.add_resource(
    "database",
    config={
        "desc": "Main database",
        "provides": ["database.main"]
    }
)

# Create resolver
resolver = DepBuilder(resources=manager, feature_names=["app.web"])
resolver.resolve()

# This will succeed even without cache, logging, or monitoring
print("Dependencies:", resolver.dep_order)
```

### Available Cardinality Modifiers

| Modifier | Name | Description |
|----------|------|-------------|
| `!` | `one` | Exactly one provider required (default) |
| `?` | `zero_or_one` | Zero or one provider allowed |
| `+` | `one_or_many` | One or more providers required |
| `*` | `zero_or_many` | Any number of providers allowed, including none |

## Checking for Resolved Dependencies in Code

To adapt behavior based on which optional dependencies were resolved:

```python
# Create a custom resource class
from resource_manager.resources import Resource, ResourceManager

class AdaptableResource(Resource):
    """Resource that adapts to available dependencies."""
    
    def get_resolved_dependencies(self, resolver):
        """Get the resources that resolved for this resource's requirements."""
        dependencies = {}
        
        if self.name not in resolver.dep_tree:
            return dependencies
        
        # Get edge links for this resource
        edge_links = resolver.dep_tree[self.name]
        
        # Group by requirement kind
        for edge in edge_links:
            kind = edge.requirement.kind
            if kind not in dependencies:
                dependencies[kind] = []
            dependencies[kind].append(edge.provider.resource)
        
        return dependencies
    
    def adapt_to_dependencies(self, resolver):
        """Adapt behavior based on which dependencies were resolved."""
        dependencies = self.get_resolved_dependencies(resolver)
        
        # Check for cache
        if "cache" in dependencies and dependencies["cache"]:
            print(f"{self.name}: Using cache for better performance")
        else:
            print(f"{self.name}: No cache available, using slower approach")
        
        # Check for logging
        if "logging" in dependencies and dependencies["logging"]:
            print(f"{self.name}: Logging enabled")
        else:
            print(f"{self.name}: Logging disabled")
        
        # You can also check how many providers were resolved
        if "monitoring" in dependencies:
            count = len(dependencies["monitoring"])
            if count > 0:
                print(f"{self.name}: Using {count} monitoring services")
            else:
                print(f"{self.name}: No monitoring available")
        
        return dependencies

# Use the adaptable resource
class AdaptableResourceManager(ResourceManager):
    resource_class = AdaptableResource

# Create manager and add resources
manager = AdaptableResourceManager()

# Add a resource with optional dependencies
manager.add_resource(
    "web_app",
    config={
        "desc": "Web application",
        "provides": ["app.web"],
        "requires": [
            "database.main",       # Required
            "cache.redis?",        # Optional
            "logging.service?"     # Optional
        ]
    }
)

# Add dependencies
manager.add_resource("database", config={"provides": ["database.main"]})
manager.add_resource("cache", config={"provides": ["cache.redis"]})
# Note: No logging service added

# Resolve dependencies
resolver = DepBuilder(resources=manager, feature_names=["app.web"])
resolver.resolve()

# Adapt to available dependencies
web_app = resolver.rmanager.get_resource("web_app")
web_app.adapt_to_dependencies(resolver)
# Output:
# web_app: Using cache for better performance
# web_app: Logging disabled
```

## Providing Fallbacks for Missing Dependencies

You can implement fallbacks for missing dependencies:

```python
from resource_manager.resources import Resource, ResourceManager
from resource_manager.resolver import DepBuilder

class FallbackResource(Resource):
    """Resource that provides fallbacks for missing dependencies."""
    
    default_attrs = {
        "fallbacks": {}  # Map of requirement kinds to fallback implementations
    }
    
    def initialize(self, resolver):
        """Initialize this resource with appropriate fallbacks."""
        dependencies = self.get_resolved_dependencies(resolver)
        
        for requirement_kind, fallback_impl in self.fallbacks.items():
            if requirement_kind not in dependencies or not dependencies[requirement_kind]:
                print(f"{self.name}: Using fallback for {requirement_kind}: {fallback_impl}")
            else:
                print(f"{self.name}: Using real implementation for {requirement_kind}")
    
    def get_resolved_dependencies(self, resolver):
        """Get the resources that resolved for this resource's requirements."""
        # Same implementation as in AdaptableResource
        dependencies = {}
        
        if self.name not in resolver.dep_tree:
            return dependencies
        
        edge_links = resolver.dep_tree[self.name]
        
        for edge in edge_links:
            kind = edge.requirement.kind
            if kind not in dependencies:
                dependencies[kind] = []
            dependencies[kind].append(edge.provider.resource)
        
        return dependencies

# Create manager using fallback resources
class FallbackResourceManager(ResourceManager):
    resource_class = FallbackResource

# Create manager and add resources
manager = FallbackResourceManager()

# Add a resource with optional dependencies and fallbacks
manager.add_resource(
    "web_app",
    config={
        "desc": "Web application",
        "provides": ["app.web"],
        "requires": [
            "database.main",       # Required
            "cache.redis?",        # Optional
            "logging.service?"     # Optional
        ],
        "fallbacks": {
            "cache": "in-memory-cache",
            "logging": "noop-logger"
        }
    }
)

# Add only required dependency
manager.add_resource("database", config={"provides": ["database.main"]})
# Note: No cache or logging services added

# Resolve dependencies
resolver = DepBuilder(resources=manager, feature_names=["app.web"])
resolver.resolve()

# Initialize with fallbacks
web_app = resolver.rmanager.get_resource("web_app")
web_app.initialize(resolver)
# Output:
# web_app: Using fallback for cache: in-memory-cache
# web_app: Using fallback for logging: noop-logger
```

## Alternative Implementation Strategy

Provide alternative implementations that can be chosen at resolution time:

```python
from resource_manager.resources import ResourceManager
from resource_manager.resolver import DepBuilder

# Create a resource manager
manager = ResourceManager()

# Define alternative implementations
manager.add_resource(
    "sqlite_db",
    config={
        "desc": "SQLite database (lightweight)",
        "provides": ["database.sqlite"],
        "vars": {
            "connection": "sqlite:///app.db",
            "is_lightweight": True
        }
    }
)

manager.add_resource(
    "postgres_db",
    config={
        "desc": "PostgreSQL database (full-featured)",
        "provides": ["database.postgres"],
        "vars": {
            "connection": "postgresql://user:pass@localhost/app",
            "is_lightweight": False
        }
    }
)

# Define application that can use either database
manager.add_resource(
    "web_app",
    config={
        "desc": "Web application with database flexibility",
        "provides": ["app.web"],
        "requires": [
            "database.sqlite?",  # Can use SQLite
            "database.postgres?" # Or PostgreSQL
        ]
    }
)

# Create a custom resolver to handle alternative implementations
class AlternativeImplementationResolver(DepBuilder):
    def _resolve(self):
        """Add pseudo-requirement to ensure exactly one database is selected."""
        # First, ensure the application exists
        if "web_app" not in self.rmanager.catalog:
            raise ValueError("web_app resource not found")
        
        # Get the web app resource
        web_app = self.rmanager.get_resource("web_app")
        
        # Create a requirement verification resource
        self.rmanager.add_resource(
            "__db_verifier__",
            scope="INTERNAL",
            config={
                "desc": "Verifies exactly one database is selected",
                "requires": ["database.+"]  # Require at least one database
            },
            force=True
        )
        
        # Proceed with normal resolution
        super()._resolve()
        
        # Check if we have exactly one database
        if self.dep_tree and "__db_verifier__" in self.dep_tree:
            db_edges = self.dep_tree["__db_verifier__"]
            if len(db_edges) > 1:
                print("Warning: Multiple database implementations selected")

# Resolve with preference for SQLite
sqlite_resolver = AlternativeImplementationResolver(
    resources=manager,
    feature_names=["app.web", "database.sqlite"]
)
sqlite_resolver.resolve()
print("SQLite dependencies:", sqlite_resolver.dep_order)

# Resolve with preference for PostgreSQL
postgres_resolver = AlternativeImplementationResolver(
    resources=manager,
    feature_names=["app.web", "database.postgres"]
)
postgres_resolver.resolve()
print("PostgreSQL dependencies:", postgres_resolver.dep_order)

# If no preference is specified, resolver will pick one (first encountered)
default_resolver = AlternativeImplementationResolver(
    resources=manager,
    feature_names=["app.web"]
)
default_resolver.resolve()
print("Default dependencies:", default_resolver.dep_order)
```

## Using Remapping Rules

Remapping rules can be used to choose implementations without changing resource definitions:

```python
from resource_manager.resources import ResourceManager
from resource_manager.resolver import DepBuilder

# Create resources
manager = ResourceManager()

# Add alternative implementations of a capability
manager.add_resource(
    "simple_logger",
    config={
        "desc": "Simple console logger",
        "provides": ["logging.simple"]
    }
)

manager.add_resource(
    "advanced_logger",
    config={
        "desc": "Advanced logger with file output",
        "provides": ["logging.advanced"]
    }
)

# Application that requires generic logging
manager.add_resource(
    "web_app",
    config={
        "desc": "Web application",
        "provides": ["app.web"],
        "requires": ["logging"]  # Generic requirement without instance
    }
)

# Use remapping rules to choose implementation
def create_app_with_logger(logger_type="simple"):
    """Create an application with a specific logger type."""
    remap_rules = {
        "logging": logger_type  # Maps "logging" to "simple" or "advanced"
    }
    
    resolver = DepBuilder(
        resources=manager,
        feature_names=["app.web"],
        remap_rules=remap_rules
    )
    resolver.resolve()
    return resolver

# Resolve with simple logger
simple_app = create_app_with_logger("simple")
print("Simple logger app:", simple_app.dep_order)

# Resolve with advanced logger
advanced_app = create_app_with_logger("advanced")
print("Advanced logger app:", advanced_app.dep_order)
```

## Handling Optional Services in a Microservices Architecture

For microservices with optional dependencies on other services:

```python
from resource_manager.resources import ResourceManager
from resource_manager.resolver import DepBuilder

# Create resource manager
manager = ResourceManager()

# Define core services
manager.add_resource(
    "api_gateway",
    config={
        "desc": "API Gateway",
        "provides": ["service.gateway"],
        "requires": [
            "service.users",         # Required service
            "service.orders?",       # Optional service
            "service.recommendations?" # Optional service
        ]
    }
)

manager.add_resource(
    "user_service",
    config={
        "desc": "User Service",
        "provides": ["service.users"],
        "requires": ["database.users"]
    }
)

manager.add_resource(
    "order_service",
    config={
        "desc": "Order Service",
        "provides": ["service.orders"],
        "requires": ["database.orders"]
    }
)

manager.add_resource(
    "recommendation_service",
    config={
        "desc": "Recommendation Service",
        "provides": ["service.recommendations"],
        "requires": ["database.recommendations", "ml.model"]
    }
)

# Define databases
manager.add_resource(
    "user_db",
    config={
        "desc": "User Database",
        "provides": ["database.users"]
    }
)

manager.add_resource(
    "order_db",
    config={
        "desc": "Order Database",
        "provides": ["database.orders"]
    }
)

manager.add_resource(
    "recommendation_db",
    config={
        "desc": "Recommendation Database",
        "provides": ["database.recommendations"]
    }
)

manager.add_resource(
    "ml_model",
    config={
        "desc": "Machine Learning Model",
        "provides": ["ml.model"]
    }
)

# Function to deploy different service compositions
def deploy_services(services_to_include=None):
    """Deploy a specific set of services."""
    if services_to_include is None:
        services_to_include = ["gateway", "users"]  # Minimal set
    
    feature_names = []
    for service in services_to_include:
        feature_names.append(f"service.{service}")
    
    resolver = DepBuilder(
        resources=manager,
        feature_names=feature_names
    )
    resolver.resolve()
    
    return resolver

# Basic deployment: gateway and users only
basic = deploy_services(["gateway", "users"])
print("Basic deployment:", basic.dep_order)
# Expected: user_db, user_service, api_gateway

# Full deployment: all services
full = deploy_services(["gateway", "users", "orders", "recommendations"])
print("Full deployment:", full.dep_order)
# Expected: all resources included

# Custom deployment: gateway, users, and orders (no recommendations)
custom = deploy_services(["gateway", "users", "orders"])
print("Custom deployment:", custom.dep_order)
# Expected: user_db, order_db, user_service, order_service, api_gateway
```

## Best Practices

1. **Use clear modifiers**: Always explicitly specify cardinality modifiers for optional dependencies
2. **Provide fallbacks**: Implement graceful fallbacks for missing optional dependencies
3. **Test both paths**: Test your application both with and without optional dependencies
4. **Explicit is better than implicit**: Clearly document which dependencies are optional
5. **Use remapping rules**: For selecting between alternative implementations
6. **Avoid deep optional chains**: Be cautious with resources that have optional dependencies that themselves have optional dependencies

## Common Issues and Solutions

### Issue: Unclear Dependency Status

If you need to check whether optional dependencies were resolved:

```python
def check_dependency_status(resolver, resource_name, dependency_kind):
    """Check if a specific dependency kind was resolved for a resource."""
    if resource_name not in resolver.dep_tree:
        return False
    
    for edge in resolver.dep_tree[resource_name]:
        if edge.requirement.kind == dependency_kind:
            return True
    
    return False

# Usage
has_cache = check_dependency_status(resolver, "web_app", "cache")
print(f"Web app has cache: {has_cache}")
```

### Issue: Accessing Resolved Dependencies

To access the specific resources that resolved for requirements:

```python
def get_resolved_dependencies(resolver, resource_name, dependency_kind=None):
    """Get resources that resolved for a resource's requirements."""
    dependencies = {}
    
    if resource_name not in resolver.dep_tree:
        return dependencies
    
    for edge in resolver.dep_tree[resource_name]:
        kind = edge.requirement.kind
        if dependency_kind and kind != dependency_kind:
            continue
            
        if kind not in dependencies:
            dependencies[kind] = []
        dependencies[kind].append(edge.provider.resource)
    
    return dependencies

# Usage
deps = get_resolved_dependencies(resolver, "web_app")
for kind, resources in deps.items():
    print(f"Dependency kind: {kind}")
    for resource in resources:
        print(f"  - {resource.name}")
```

## Summary

The Resource Manager provides several approaches for handling optional dependencies:

1. **Cardinality Modifiers**: Use `?`, `*`, or `+` to control requirement cardinality
2. **Custom Resources**: Create resources that adapt to available dependencies
3. **Fallback Implementations**: Provide alternative implementations when dependencies are missing
4. **Alternative Implementations**: Define multiple resources providing the same capability
5. **Remapping Rules**: Use remapping to choose specific implementations

These techniques allow you to build flexible applications that can adapt to different deployment scenarios and available dependencies. 