# How to Customize Resource Resolution

This guide shows you how to implement custom resolution strategies for specific dependency scenarios.

## Problem

The default dependency resolution strategy may not be sufficient for complex applications with specialized requirements, such as:

- Features that need to be enabled based on runtime conditions
- Resources that should be matched differently depending on context
- Complex matching rules beyond simple kind/instance matching

## Solution

Create a custom resolver by subclassing the `DepBuilder` class and overriding the `resolve_requirements` method.

## Basic Custom Resolver

Here's how to create a basic custom resolver:

```python
from resource_manager.resolver import DepBuilder

class CustomDepBuilder(DepBuilder):
    def resolve_requirements(self, requirement, lvl=0):
        """Custom implementation for resolving requirements."""
        
        # Call the default matching logic
        match_name, provider_links = requirement.match_provider(
            self.provider_links,
            remap_rules=self.remap_rules,
            default_mode="one", 
            remap_requirement=True,
        )
        
        # Add custom logic here
        # For example, logging the matches
        print(f"Requirement {requirement.rule} matched with {len(provider_links)} providers")
        
        return match_name, provider_links
```

## Feature-Based Resolution

This example demonstrates a resolver that handles features differently from regular requirements:

```python
class FeatureDepBuilder(DepBuilder):
    def resolve_requirements(self, requirement, lvl=0):
        """Specialized resolver for feature-based requirements."""
        
        # Special handling for feature requirements
        if requirement.kind.startswith("feature."):
            # Get all providers with matching kind
            matching_providers = [
                p for p in self.provider_links 
                if p.kind == requirement.kind
            ]
            
            # Check if this feature was explicitly requested
            feature_name = requirement.kind.split(".", 1)[1]  # Extract feature name
            
            if feature_name in self.feature_names:
                # Feature was requested, so include it
                if matching_providers:
                    return feature_name, matching_providers
                else:
                    # Print warning if feature was requested but not available
                    print(f"Warning: Feature {feature_name} was requested but no provider found")
            
            # Feature wasn't requested, use normal matching logic for optional features
            match_name, provider_links = requirement.match_provider(
                self.provider_links,
                remap_rules=self.remap_rules,
                default_mode="zero_or_one",  # Make features optional by default
                remap_requirement=True,
            )
            return match_name, provider_links
        
        # Default handling for non-feature requirements
        match_name, provider_links = requirement.match_provider(
            self.provider_links,
            remap_rules=self.remap_rules,
            default_mode="one",
            remap_requirement=True,
        )
        return match_name, provider_links
```

## Priority-Based Resolution

This example shows a resolver that considers resource priorities:

```python
class PriorityDepBuilder(DepBuilder):
    def resolve_requirements(self, requirement, lvl=0):
        """Resolver that selects providers based on priority."""
        
        # Get all potential providers for this requirement
        potential_providers = [
            p for p in self.provider_links 
            if p.kind == requirement.kind
        ]
        
        # If instance is specified, filter by it
        if requirement.instance:
            potential_providers = [
                p for p in potential_providers 
                if p.instance == requirement.instance
            ]
        
        # If we found providers, select based on priority
        if potential_providers:
            # Check if resources have a priority attribute
            prioritized_providers = []
            for provider in potential_providers:
                # Get priority from resource (default to 0)
                priority = getattr(provider.resource, "priority", 0)
                prioritized_providers.append((priority, provider))
            
            # Sort by priority (highest first)
            prioritized_providers.sort(reverse=True)
            
            # Return highest priority provider
            if prioritized_providers:
                highest_priority = prioritized_providers[0][0]
                # Get all providers with the highest priority
                selected_providers = [
                    p for prio, p in prioritized_providers 
                    if prio == highest_priority
                ]
                return requirement.instance or "default", selected_providers
        
        # Fall back to default matching if no prioritized providers found
        match_name, provider_links = requirement.match_provider(
            self.provider_links,
            remap_rules=self.remap_rules,
            default_mode="one",
            remap_requirement=True,
        )
        return match_name, provider_links
```

## Environment-Aware Resolution

This resolver selects providers based on the current environment:

```python
class EnvironmentDepBuilder(DepBuilder):
    def __init__(self, environment="development", *args, **kwargs):
        """Initialize with environment setting."""
        super().__init__(*args, **kwargs)
        self.environment = environment
    
    def resolve_requirements(self, requirement, lvl=0):
        """Environment-aware resolution strategy."""
        
        # Get all potential providers
        potential_providers = [
            p for p in self.provider_links 
            if p.kind == requirement.kind
        ]
        
        # Try to find environment-specific providers first
        env_specific_providers = []
        for provider in potential_providers:
            resource = provider.resource
            # Check if resource has environment attribute
            res_env = getattr(resource, "environment", None)
            
            # If environment matches or resource is environment-agnostic
            if res_env is None or res_env == self.environment:
                env_specific_providers.append(provider)
        
        # If we found environment-specific providers, match among them
        if env_specific_providers:
            # Create a temporary requirement for matching
            temp_req = requirement
            match_name, _ = temp_req.match_provider(
                env_specific_providers,
                remap_rules=self.remap_rules,
                default_mode="one",
                remap_requirement=True,
            )
            # If we found a match, return it
            if match_name and env_specific_providers:
                return match_name, env_specific_providers
        
        # Fall back to default matching
        match_name, provider_links = requirement.match_provider(
            self.provider_links,
            remap_rules=self.remap_rules,
            default_mode="one",
            remap_requirement=True,
        )
        return match_name, provider_links
```

## Using Custom Resolvers

Here's how to use your custom resolver:

```python
from resource_manager.resources import ResourceManager

# Create resources
manager = ResourceManager()
# ... add resources ...

# Use your custom resolver
resolver = CustomDepBuilder(
    resources=manager,
    feature_names=["app.main"],
    debug=True
)

# Resolve dependencies
resolver.resolve()

# Access resolution results
print("Dependency order:", resolver.dep_order)
```

## Practical Example

Let's use a feature-based resolver to implement a microservices application with optional components:

```python
from resource_manager.resources import ResourceManager
from resource_manager.resolver import DepBuilder

# Create a custom feature resolver
class MicroserviceResolver(DepBuilder):
    def resolve_requirements(self, requirement, lvl=0):
        # Handle optional microservices
        if requirement.kind == "service" and requirement.mod == "?":
            service_name = requirement.instance
            # Check if this service was explicitly enabled
            if service_name in self.feature_names:
                # Service is enabled, try to find providers
                matching_providers = [
                    p for p in self.provider_links 
                    if p.kind == requirement.kind and p.instance == service_name
                ]
                if matching_providers:
                    return service_name, matching_providers
            
            # Service wasn't enabled or not found, return empty list
            return service_name, []
        
        # Default handling for other requirements
        match_name, provider_links = requirement.match_provider(
            self.provider_links,
            remap_rules=self.remap_rules,
            default_mode="one",
            remap_requirement=True,
        )
        return match_name, provider_links

# Create resources for our microservices
manager = ResourceManager()

# Core services
manager.add_resource(
    "api_gateway",
    config={
        "desc": "API Gateway service",
        "provides": ["service.gateway"],
        "requires": [
            "service.auth?",    # Optional auth service
            "service.users",    # Required user service
            "service.orders?"   # Optional order service
        ]
    }
)

manager.add_resource(
    "user_service",
    config={
        "desc": "User management service",
        "provides": ["service.users"],
        "requires": ["database.users"]
    }
)

# Optional services
manager.add_resource(
    "auth_service",
    config={
        "desc": "Authentication service",
        "provides": ["service.auth"],
        "requires": ["database.auth"]
    }
)

manager.add_resource(
    "order_service",
    config={
        "desc": "Order management service",
        "provides": ["service.orders"],
        "requires": ["database.orders"]
    }
)

# Databases
manager.add_resource(
    "user_db",
    config={
        "desc": "User database",
        "provides": ["database.users"]
    }
)

manager.add_resource(
    "auth_db",
    config={
        "desc": "Auth database",
        "provides": ["database.auth"]
    }
)

manager.add_resource(
    "order_db",
    config={
        "desc": "Order database",
        "provides": ["database.orders"]
    }
)

# Resolve with only the auth service enabled
resolver = MicroserviceResolver(
    resources=manager,
    feature_names=["service.gateway", "auth"],  # Enable auth but not orders
    debug=True
)

resolver.resolve()

# Print the resolved dependency order
print("Dependency order:", resolver.dep_order)
# Expected: user_db, auth_db, user_service, auth_service, api_gateway
# Note: order_service and order_db not included
```

## Best Practices

1. **Keep it simple**: Only override what you need to
2. **Maintain compatibility**: Fall back to default resolution for common cases
3. **Add clear documentation**: Explain what your custom resolver does
4. **Add logging**: Log resolution decisions for debugging
5. **Use feature flags**: Resolution is a great place to implement feature flags
6. **Test thoroughly**: Test your resolver with various resource configurations 