# How to Implement Feature Flags

This guide demonstrates how to implement feature flags using the Resource Manager, allowing you to enable or disable features at runtime.

## Problem

When developing applications, you often need to:

1. Enable/disable features without changing code
2. Roll out features gradually to subsets of users
3. A/B test different implementations of the same feature
4. Toggle features per environment (development, staging, production)

## Solution

Use the Resource Manager's dependency resolution system to implement a flexible feature flag mechanism.

## Approach 1: Using Optional Requirements

The simplest approach is to use optional requirements (`?` modifier) for feature dependencies:

```python
from resource_manager.resources import ResourceManager
from resource_manager.resolver import DepBuilder

# Create a resource manager
manager = ResourceManager()

# Add core application resources
manager.add_resource(
    "core_app",
    config={
        "desc": "Core application",
        "provides": ["app.core"],
        "requires": [
            "database.main",          # Required dependency
            "feature.analytics?",     # Optional feature
            "feature.notifications?", # Optional feature
            "feature.export?"         # Optional feature
        ]
    }
)

manager.add_resource(
    "database",
    config={
        "desc": "Main database",
        "provides": ["database.main"]
    }
)

# Define feature implementations
manager.add_resource(
    "analytics_feature",
    config={
        "desc": "Analytics dashboard feature",
        "provides": ["feature.analytics"],
        "requires": ["database.analytics"]
    }
)

manager.add_resource(
    "notifications_feature",
    config={
        "desc": "User notifications feature",
        "provides": ["feature.notifications"],
        "requires": ["messaging.service"]
    }
)

manager.add_resource(
    "export_feature",
    config={
        "desc": "Data export feature",
        "provides": ["feature.export"],
        "requires": ["storage.blob"]
    }
)

# Add feature dependencies
manager.add_resource(
    "analytics_db",
    config={
        "desc": "Analytics database",
        "provides": ["database.analytics"]
    }
)

manager.add_resource(
    "messaging_service",
    config={
        "desc": "Messaging service",
        "provides": ["messaging.service"]
    }
)

manager.add_resource(
    "blob_storage",
    config={
        "desc": "Blob storage",
        "provides": ["storage.blob"]
    }
)

# Enable specific features via feature_names
def get_app_with_features(enabled_features=None):
    """Create a resolver with specific features enabled."""
    feature_names = ["app.core"]  # Base application
    
    # Add enabled features
    if enabled_features:
        for feature in enabled_features:
            if not feature.startswith("feature."):
                feature = f"feature.{feature}"
            feature_names.append(feature)
    
    # Create resolver
    resolver = DepBuilder(
        resources=manager,
        feature_names=feature_names
    )
    resolver.resolve()
    
    return resolver

# Usage examples:
# App with no optional features
basic_app = get_app_with_features()
print("Basic app:", basic_app.dep_order)
# Expected: ["database", "core_app"]

# App with analytics feature
analytics_app = get_app_with_features(["analytics"])
print("App with analytics:", analytics_app.dep_order)
# Expected: ["database", "analytics_db", "analytics_feature", "core_app"]

# App with all features
full_app = get_app_with_features(["analytics", "notifications", "export"])
print("Full app:", full_app.dep_order)
# Expected: All resources included
```

## Approach 2: Custom Feature Resolver

For more control, create a custom resolver that explicitly handles feature flags:

```python
from resource_manager.resolver import DepBuilder

class FeatureFlagResolver(DepBuilder):
    """Resolver with explicit feature flag support."""
    
    def __init__(self, enabled_features=None, *args, **kwargs):
        """Initialize with enabled features."""
        super().__init__(*args, **kwargs)
        self.enabled_features = set(enabled_features or [])
    
    def resolve_requirements(self, requirement, lvl=0):
        """Handle feature-specific requirements differently."""
        # Check if this is a feature requirement
        if requirement.kind.startswith("feature."):
            feature_name = requirement.kind.split(".", 1)[1]
            
            # If feature is explicitly enabled, try to find providers
            if feature_name in self.enabled_features:
                matching_providers = [
                    p for p in self.provider_links 
                    if p.kind == requirement.kind
                ]
                
                if matching_providers:
                    return feature_name, matching_providers
                else:
                    print(f"Warning: Feature {feature_name} was enabled but no provider found")
            
            # Feature not enabled, return empty list (skip it)
            return requirement.instance or feature_name, []
        
        # For non-feature requirements, use standard resolution
        match_name, provider_links = requirement.match_provider(
            self.provider_links,
            remap_rules=self.remap_rules,
            default_mode="one",
            remap_requirement=True,
        )
        return match_name, provider_links

# Usage example
def create_app_with_features(enabled_features=None):
    """Create an application with specific features enabled."""
    resolver = FeatureFlagResolver(
        enabled_features=enabled_features,
        resources=manager,
        feature_names=["app.core"]
    )
    resolver.resolve()
    return resolver

# Enable specific features
app = create_app_with_features(["analytics", "export"])
print("Dependency order:", app.dep_order)
```

## Approach 3: Feature Toggle Resources

Create explicit feature toggle resources:

```python
# Define feature toggle resources
manager.add_resource(
    "analytics_toggle",
    config={
        "desc": "Analytics feature toggle",
        "provides": ["toggle.analytics"],
        "vars": {
            "enabled": True,
            "percentage": 100,  # Percentage of users who get this feature
            "version": "1.0"
        }
    }
)

manager.add_resource(
    "notifications_toggle",
    config={
        "desc": "Notifications feature toggle",
        "provides": ["toggle.notifications"],
        "vars": {
            "enabled": False,
            "percentage": 0,
            "version": "beta"
        }
    }
)

# Make features depend on their toggles
manager.add_resource(
    "analytics_feature",
    config={
        "desc": "Analytics dashboard feature",
        "provides": ["feature.analytics"],
        "requires": [
            "toggle.analytics",  # Require the toggle to be present
            "database.analytics"
        ]
    }
)

manager.add_resource(
    "notifications_feature",
    config={
        "desc": "User notifications feature",
        "provides": ["feature.notifications"],
        "requires": [
            "toggle.notifications",
            "messaging.service"
        ]
    }
)

# Create a custom resolver that checks toggle status
class ToggleResolver(DepBuilder):
    def _resolve(self):
        """Override the resolution process to check toggles."""
        # First pass: identify all toggle resources
        toggle_resources = {}
        for resource_name in self.rmanager.catalog:
            resource = self.rmanager.get_resource(resource_name)
            for provider in resource.provides:
                if provider.kind == "toggle":
                    toggle_name = provider.instance
                    toggle_resources[toggle_name] = resource
        
        # Second pass: filter out disabled features
        filtered_manager = type(self.rmanager)()
        for resource_name in self.rmanager.catalog:
            resource = self.rmanager.get_resource(resource_name)
            
            # Check if this is a feature resource
            is_feature = False
            for provider in resource.provides:
                if provider.kind == "feature":
                    feature_name = provider.instance
                    # Check if toggle exists and is disabled
                    if (feature_name in toggle_resources and 
                        not getattr(toggle_resources[feature_name], "enabled", True)):
                        is_feature = True
                        break
            
            # Add resource to filtered manager if not a disabled feature
            if not is_feature:
                filtered_manager.add_resource(
                    resource_name,
                    config=resource
                )
        
        # Use the filtered manager for resolution
        self.rmanager = filtered_manager
        
        # Continue with normal resolution
        super()._resolve()
```

## Approach 4: Environment-based Feature Flags

Combine feature flags with environment configuration:

```python
# Define features with environment restrictions
manager.add_resource(
    "analytics_feature",
    config={
        "desc": "Analytics dashboard feature",
        "provides": ["feature.analytics"],
        "requires": ["database.analytics"],
        "vars": {
            "environments": ["production", "staging"],  # Only in prod/staging
            "enabled": True
        }
    }
)

manager.add_resource(
    "experimental_feature",
    config={
        "desc": "Experimental feature",
        "provides": ["feature.experimental"],
        "requires": ["database.main"],
        "vars": {
            "environments": ["development"],  # Only in development
            "enabled": True
        }
    }
)

# Create a resolver that respects environment settings
class EnvironmentFeatureResolver(DepBuilder):
    def __init__(self, environment="development", *args, **kwargs):
        """Initialize with current environment."""
        super().__init__(*args, **kwargs)
        self.environment = environment
    
    def _resolve(self):
        """Filter resources based on environment before resolution."""
        # Create a filtered copy of the resource manager
        filtered_manager = type(self.rmanager)()
        
        for resource_name in self.rmanager.catalog:
            resource = self.rmanager.get_resource(resource_name)
            
            # Check if resource has environment restrictions
            environments = getattr(resource, "environments", None)
            enabled = getattr(resource, "enabled", True)
            
            # Include resource if it's enabled and allowed in this environment
            if (enabled and 
                (environments is None or self.environment in environments)):
                filtered_manager.add_resource(
                    resource_name,
                    config=resource
                )
        
        # Use the filtered manager for resolution
        self.rmanager = filtered_manager
        
        # Continue with normal resolution
        super()._resolve()

# Usage
dev_resolver = EnvironmentFeatureResolver(
    environment="development",
    resources=manager,
    feature_names=["app.core"]
)
dev_resolver.resolve()

prod_resolver = EnvironmentFeatureResolver(
    environment="production",
    resources=manager,
    feature_names=["app.core"]
)
prod_resolver.resolve()
```

## Practical Example: Multi-Tenant Application with Features

Here's a complete example of a multi-tenant application with feature flags:

```python
from resource_manager.resources import Resource, ResourceManager
from resource_manager.resolver import DepBuilder

# Create custom resource class for feature flags
class FeatureResource(Resource):
    default_attrs = {
        "enabled": True,         # Whether feature is enabled by default
        "percentage": 100,       # Percentage of tenants that get this feature
        "min_tier": "free",      # Minimum subscription tier needed
        "environments": None,    # List of allowed environments or None for all
        "description": "",       # Human-readable description
    }

class TenantAwareResource(Resource):
    default_attrs = {
        "tenant_id": None,       # Specific tenant or None for all
        "environment": None,     # Specific environment or None for all
        "tier": "free",          # Subscription tier (free, standard, premium)
    }

class FeatureManager(ResourceManager):
    resource_class = TenantAwareResource

# Custom resolver for multi-tenant feature flags
class MultiTenantFeatureResolver(DepBuilder):
    def __init__(self, tenant_id=None, environment="production", tier="free", *args, **kwargs):
        """Initialize with tenant context."""
        super().__init__(*args, **kwargs)
        self.tenant_id = tenant_id
        self.environment = environment
        self.tier = tier
        self.enabled_features = kwargs.pop("enabled_features", set())
    
    def resolve_requirements(self, requirement, lvl=0):
        """Handle feature flags based on tenant context."""
        # Special handling for feature requirements
        if requirement.kind.startswith("feature."):
            feature_name = requirement.kind.split(".", 1)[1]
            
            # Get all feature providers
            matching_providers = [
                p for p in self.provider_links 
                if p.kind == requirement.kind
            ]
            
            # No matching providers at all
            if not matching_providers:
                if requirement.mod in ["?", "zero_or_one", "*", "zero_or_many"]:
                    return feature_name, []
                raise ValueError(f"Required feature {feature_name} has no provider")
            
            # Filter providers based on tenant context
            valid_providers = []
            for provider in matching_providers:
                feature = provider.resource
                
                # Check if feature is enabled
                if not getattr(feature, "enabled", True):
                    continue
                
                # Check environment restrictions
                environments = getattr(feature, "environments", None)
                if environments and self.environment not in environments:
                    continue
                
                # Check tier requirements
                min_tier = getattr(feature, "min_tier", "free")
                tier_levels = {"free": 0, "standard": 1, "premium": 2}
                if tier_levels.get(self.tier, 0) < tier_levels.get(min_tier, 0):
                    continue
                
                # Check if feature is explicitly enabled
                if feature_name in self.enabled_features:
                    valid_providers.append(provider)
                    continue
                
                # Check percentage rollout
                percentage = getattr(feature, "percentage", 100)
                if percentage >= 100:
                    valid_providers.append(provider)
                elif percentage <= 0:
                    continue
                else:
                    # In a real system, use a deterministic hash of tenant_id
                    # to ensure consistent feature assignment
                    import hashlib
                    if self.tenant_id:
                        tenant_hash = int(hashlib.md5(
                            f"{self.tenant_id}:{feature_name}".encode()
                        ).hexdigest(), 16)
                        # Determine if tenant is in the percentage
                        if tenant_hash % 100 < percentage:
                            valid_providers.append(provider)
            
            # Return valid providers or empty list for optional features
            if valid_providers:
                return feature_name, valid_providers
            elif requirement.mod in ["?", "zero_or_one", "*", "zero_or_many"]:
                return feature_name, []
            else:
                raise ValueError(
                    f"Required feature {feature_name} not available for "
                    f"tenant {self.tenant_id} in {self.environment} (tier: {self.tier})"
                )
        
        # Default handling for non-feature requirements
        match_name, provider_links = requirement.match_provider(
            self.provider_links,
            remap_rules=self.remap_rules,
            default_mode="one",
            remap_requirement=True,
        )
        return match_name, provider_links

# Create the manager and add resources
manager = FeatureManager()

# Core resources
manager.add_resource(
    "app_core",
    config={
        "desc": "Core application",
        "provides": ["app.core"],
        "requires": [
            "database.main",
            "feature.dashboard?",
            "feature.reports?",
            "feature.ai_assistant?",
            "feature.export?"
        ]
    }
)

manager.add_resource(
    "main_db",
    config={
        "desc": "Main database",
        "provides": ["database.main"]
    }
)

# Feature definitions
manager.add_resource(
    "dashboard_feature",
    config={
        "desc": "Interactive dashboard",
        "provides": ["feature.dashboard"],
        "enabled": True,
        "percentage": 100,
        "min_tier": "free",
        "environments": ["production", "staging", "development"]
    }
)

manager.add_resource(
    "reports_feature",
    config={
        "desc": "Advanced reporting",
        "provides": ["feature.reports"],
        "requires": ["database.analytics"],
        "enabled": True,
        "percentage": 100,
        "min_tier": "standard",
        "environments": ["production", "staging", "development"]
    }
)

manager.add_resource(
    "ai_assistant_feature",
    config={
        "desc": "AI-powered assistant",
        "provides": ["feature.ai_assistant"],
        "requires": ["service.ai"],
        "enabled": True,
        "percentage": 20,  # Gradual rollout to 20% of tenants
        "min_tier": "premium",
        "environments": ["production"]
    }
)

manager.add_resource(
    "export_feature",
    config={
        "desc": "Data export capabilities",
        "provides": ["feature.export"],
        "requires": ["storage.blob"],
        "enabled": False,  # Disabled for now
        "percentage": 0,
        "min_tier": "standard",
        "environments": ["production", "staging"]
    }
)

# Feature dependencies
manager.add_resource(
    "analytics_db",
    config={
        "desc": "Analytics database",
        "provides": ["database.analytics"]
    }
)

manager.add_resource(
    "ai_service",
    config={
        "desc": "AI service",
        "provides": ["service.ai"]
    }
)

manager.add_resource(
    "blob_storage",
    config={
        "desc": "Blob storage",
        "provides": ["storage.blob"]
    }
)

# Example usage for different tenants
def resolve_for_tenant(tenant_id, environment, tier, enabled_features=None):
    """Resolve resources for a specific tenant."""
    resolver = MultiTenantFeatureResolver(
        tenant_id=tenant_id,
        environment=environment,
        tier=tier,
        resources=manager,
        feature_names=["app.core"],
        enabled_features=enabled_features or set()
    )
    resolver.resolve()
    return resolver

# Free tier tenant
free_tenant = resolve_for_tenant("tenant1", "production", "free")
print("Free tenant features:", [
    r for r in free_tenant.dep_order 
    if "feature" in r
])

# Standard tier tenant
standard_tenant = resolve_for_tenant("tenant2", "production", "standard")
print("Standard tier features:", [
    r for r in standard_tenant.dep_order 
    if "feature" in r
])

# Premium tier tenant
premium_tenant = resolve_for_tenant("tenant3", "production", "premium")
print("Premium tier features:", [
    r for r in premium_tenant.dep_order 
    if "feature" in r
])

# Tenant with export explicitly enabled
tenant_with_export = resolve_for_tenant(
    "tenant4", "production", "standard", 
    enabled_features={"export"}
)
print("Tenant with export enabled:", [
    r for r in tenant_with_export.dep_order 
    if "feature" in r
])
```

## Best Practices

1. **Clear naming convention**: Use a consistent prefix (like `feature.`) for feature capabilities
2. **Centralized configuration**: Keep feature flag definitions in a central place
3. **Fine-grained features**: Break functionality into small, independently toggleable features
4. **Default to off**: New features should be disabled by default
5. **Document features**: Clearly document what each feature does and its dependencies
6. **Avoid deep feature dependencies**: Features should not depend on other optional features
7. **Clean up**: Remove feature flags after they're fully launched and stable

## Common Issues and Solutions

### Issue: Features Interfering with Each Other

If features have overlapping requirements, they might interfere with each other:

```python
# Problem: Features with overlapping dependencies
manager.add_resource(
    "feature_a",
    config={
        "desc": "Feature A",
        "provides": ["feature.a"],
        "requires": ["database.special"]
    }
)

manager.add_resource(
    "feature_b",
    config={
        "desc": "Feature B",
        "provides": ["feature.b"],
        "requires": ["database.special"]
    }
)

# Solution: Use specific instance names for dependencies
manager.add_resource(
    "feature_a",
    config={
        "desc": "Feature A",
        "provides": ["feature.a"],
        "requires": ["database.special.feature_a"]  # Use specific instance
    }
)

manager.add_resource(
    "feature_b",
    config={
        "desc": "Feature B",
        "provides": ["feature.b"],
        "requires": ["database.special.feature_b"]  # Use specific instance
    }
)
```

### Issue: Feature Persistence

Features that affect data storage need special handling:

```python
# Problem: Feature creates data that persists even when disabled
# Solution: Add version tracking and migration strategy

manager.add_resource(
    "data_format_feature",
    config={
        "desc": "New data format",
        "provides": ["feature.new_format"],
        "vars": {
            "enabled": True,
            "version": "2.0",
            "schema_version": 3,
            "requires_migration": True,
            "migration_strategy": "read_both_write_new"  # Read old and new, write only new
        }
    }
)

# In your application code, you would check the feature's migration strategy
# and handle data accordingly, even when the feature is disabled
```

## Summary

The Resource Manager provides several powerful ways to implement feature flags:

1. **Optional Dependencies**: Use `?` modifier for simple on/off toggles
2. **Custom Resolvers**: Create resolvers that understand feature flags
3. **Feature Toggle Resources**: Define explicit resources for feature toggles
4. **Environment-based Features**: Combine with environment configuration
5. **Multi-tenant Features**: Implement sophisticated rollout strategies

These approaches give you fine-grained control over features across environments, tenants, and deployment stages. 