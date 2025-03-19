# Extension Points

This document explains the main extension points in the Resource Manager, detailing how to customize and extend its functionality for specialized use cases.

## Overview of Extension Points

The Resource Manager provides several key extension points:

1. **Custom Resource Classes**: Extend the `Resource` class
2. **Custom Resource Managers**: Extend the `ResourceManager` class
3. **Custom Resolvers**: Extend the `DepBuilder` class
4. **Custom Link Types**: Extend the `ResourceLink` classes

## Custom Resource Classes

The `Resource` class can be extended to add specialized behavior or attributes:

```python
from resource_manager.resources import Resource

class EnvironmentAwareResource(Resource):
    """Resource with environment awareness."""
    
    default_attrs = {
        "environment": "development",  # Default environment
        "min_version": "1.0",         # Minimum version
        "max_version": None,          # Maximum version (None = no limit)
    }
    
    def is_compatible_with_environment(self, target_env, version=None):
        """Check if resource is compatible with the target environment."""
        # Check environment
        if self.environment != "all" and self.environment != target_env:
            return False
        
        # Check version compatibility if specified
        if version and self.min_version:
            if version < self.min_version:
                return False
        
        if version and self.max_version:
            if version > self.max_version:
                return False
        
        return True
```

### Benefits of Custom Resource Classes

1. **Domain-Specific Attributes**: Add attributes relevant to your domain
2. **Behavior Extensions**: Add methods for specialized behavior
3. **Validation Logic**: Add custom validation logic
4. **Resource Lifecycle Hooks**: Add initialization or cleanup hooks

## Custom Resource Managers

The `ResourceManager` class can be extended to customize resource management:

```python
from resource_manager.resources import ResourceManager

class VersionedResourceManager(ResourceManager):
    """Resource manager with versioning support."""
    
    resource_class = EnvironmentAwareResource  # Use custom resource class
    
    def __init__(self, version="1.0", environment="development"):
        super().__init__()
        self.version = version
        self.environment = environment
    
    def get_compatible_resources(self):
        """Get resources compatible with the current environment and version."""
        compatible = []
        
        for name, resource in self.catalog.items():
            if resource.is_compatible_with_environment(self.environment, self.version):
                compatible.append(resource)
        
        return compatible
    
    def add_resource(self, name, config=None, scope=None, force=False):
        """Add a resource with version validation."""
        # Add custom validation
        if config and "min_version" in config.get("vars", {}):
            min_version = config["vars"]["min_version"]
            if min_version > self.version:
                raise ValueError(
                    f"Resource {name} requires minimum version {min_version}, "
                    f"but manager version is {self.version}"
                )
        
        # Call parent method
        return super().add_resource(name, config, scope, force)
```

### Benefits of Custom Resource Managers

1. **Resource Validation**: Add custom validation during resource addition
2. **Resource Filtering**: Add methods to filter resources based on criteria
3. **Resource Creation**: Customize how resources are created and configured
4. **Resource Organization**: Add methods for organizing resources

## Custom Resolvers

The `DepBuilder` class can be extended to customize dependency resolution:

```python
from resource_manager.resolver import DepBuilder

class FeatureToggleResolver(DepBuilder):
    """Resolver with feature toggle support."""
    
    def __init__(self, features_enabled=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.features_enabled = set(features_enabled or [])
    
    def resolve_requirements(self, requirement, lvl=0):
        """Custom resolution logic for feature toggles."""
        # Special handling for feature requirements
        if requirement.kind == "feature":
            feature_name = requirement.instance
            
            # Skip disabled features
            if feature_name not in self.features_enabled:
                # Return empty list for optional features
                if requirement.mod in ["?", "zero_or_one", "*", "zero_or_many"]:
                    return feature_name, []
                
                # Raise error for required features that are disabled
                raise ValueError(
                    f"Required feature {feature_name} is disabled. "
                    f"Enable it by adding to features_enabled."
                )
        
        # Use default resolution for non-feature requirements
        return super().resolve_requirements(requirement, lvl)
    
    def _resolve(self):
        """Custom resolution that filters resources by enabled features."""
        # First, perform standard resolution
        super()._resolve()
        
        # Then, filter the dependency tree to remove disabled features
        # (This is a simplification - a real implementation would be more complex)
        filtered_tree = {}
        for resource_name, edges in self.dep_tree.items():
            filtered_edges = []
            
            for edge in edges:
                # Include edge only if it's not for a disabled feature
                if edge.requirement.kind != "feature" or edge.requirement.instance in self.features_enabled:
                    filtered_edges.append(edge)
            
            if filtered_edges:
                filtered_tree[resource_name] = filtered_edges
            
        self.dep_tree = filtered_tree
```

### Benefits of Custom Resolvers

1. **Resource Selection Logic**: Customize how resources are selected
2. **Dependency Filtering**: Filter dependencies based on custom criteria
3. **Resource Prioritization**: Implement resource priority during resolution
4. **Dependency Validation**: Add custom validation for dependencies
5. **Dependency Graph Manipulation**: Modify the dependency graph after resolution

## Custom Link Types

The `ResourceLink` classes can be extended to add specialized link behavior:

```python
from resource_manager.links import ResourceRequireLink

class VersionedRequireLink(ResourceRequireLink):
    """Requirement link with version constraints."""
    
    def __init__(self, kind, instance=None, resource=None, mod=None, min_version=None, max_version=None):
        super().__init__(kind, instance, resource, mod)
        self.min_version = min_version
        self.max_version = max_version
    
    def match_provider(self, provider_links, remap_rules=None, default_mode="one", remap_requirement=False):
        """Match providers with version constraints."""
        # First, use the standard matching logic
        match_name, matching_providers = super().match_provider(
            provider_links, remap_rules, default_mode, remap_requirement
        )
        
        # Then, filter by version constraints
        if matching_providers and (self.min_version or self.max_version):
            filtered_providers = []
            
            for provider in matching_providers:
                provider_resource = provider.resource
                provider_version = getattr(provider_resource, "version", None)
                
                # Skip providers without version information
                if provider_version is None:
                    continue
                
                # Check minimum version
                if self.min_version and provider_version < self.min_version:
                    continue
                
                # Check maximum version
                if self.max_version and provider_version > self.max_version:
                    continue
                
                # Provider meets version constraints
                filtered_providers.append(provider)
            
            # Update matching providers
            matching_providers = filtered_providers
            
            # Validate cardinality again
            if default_mode in ["!", "one"] and not matching_providers:
                raise ValueError(
                    f"No version-compatible provider found for required dependency {self}"
                )
        
        return match_name, matching_providers
```

### Benefits of Custom Link Types

1. **Enhanced Matching Logic**: Add custom criteria for matching providers
2. **Link Metadata**: Add metadata to links for specialized resolution
3. **Link Validation**: Add validation for links

## Complete Extension Example

Here's a complete example showing how to extend multiple components:

```python
from resource_manager.resources import Resource, ResourceManager
from resource_manager.resolver import DepBuilder

# 1. Custom Resource class
class EnterpriseResource(Resource):
    default_attrs = {
        "environment": "development",
        "tenant_id": None,
        "priority": 0,
        "version": "1.0"
    }
    
    def is_compatible(self, environment, tenant_id=None):
        """Check if resource is compatible with the given environment and tenant."""
        # Environment compatibility
        if self.environment != "all" and self.environment != environment:
            return False
        
        # Tenant compatibility
        if tenant_id and self.tenant_id and self.tenant_id != tenant_id:
            return False
        
        return True

# 2. Custom ResourceManager
class EnterpriseResourceManager(ResourceManager):
    resource_class = EnterpriseResource
    
    def get_resources_by_environment(self, environment):
        """Get resources for a specific environment."""
        return [r for r in self.catalog.values() if r.is_compatible(environment)]

# 3. Custom Resolver
class EnterpriseDepBuilder(DepBuilder):
    def __init__(self, environment="development", tenant_id=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.environment = environment
        self.tenant_id = tenant_id
    
    def resolve_requirements(self, requirement, lvl=0):
        """Environment and tenant-aware resolution."""
        # Find all potential providers
        match_name, provider_links = super().resolve_requirements(requirement, lvl)
        
        # Filter providers by environment and tenant compatibility
        if provider_links:
            compatible_providers = []
            
            for provider in provider_links:
                resource = provider.resource
                if resource.is_compatible(self.environment, self.tenant_id):
                    compatible_providers.append(provider)
            
            # Use compatible providers
            if compatible_providers:
                provider_links = compatible_providers
            elif requirement.mod in ["!", "one", "+", "one_or_many"]:
                # Required dependency with no compatible providers
                raise ValueError(
                    f"No compatible provider found for required dependency {requirement} "
                    f"in environment {self.environment} for tenant {self.tenant_id}"
                )
        
        return match_name, provider_links
```

## Implementation Guidelines

When extending the Resource Manager:

1. **Respect interfaces**: Maintain the expected method signatures
2. **Call parent methods**: Use `super()` to call parent methods when appropriate
3. **Follow conventions**: Follow the naming and structure conventions
4. **Test extensions**: Thoroughly test your extensions
5. **Document behavior**: Document any custom behavior

## Best Practices

1. **Minimal Extensions**: Only extend what you need
2. **Composability**: Design extensions to be composable
3. **Separation of Concerns**: Keep each extension focused on a specific concern
4. **Backwards Compatibility**: Maintain compatibility with the base API
5. **Clear Documentation**: Document your extensions clearly

## Related How-To Guides

For practical examples, see:
- [How to Extend the Resource Manager](../resource_manager_howtos/08_extending.md)
- [How to Customize Resource Resolution](../resource_manager_howtos/01_custom_resolution.md)
