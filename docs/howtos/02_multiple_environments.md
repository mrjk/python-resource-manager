# How to Handle Multiple Environments

This guide demonstrates techniques for managing resources across different environments (development, staging, production) using the Resource Manager.

## Problem

When managing applications across multiple environments, you need:

1. Consistent resource structure across environments
2. Environment-specific configurations
3. The ability to test environment-specific setups
4. A way to avoid code duplication while maintaining environment differences

## Solution

Use a combination of resource scopes, inheritance, and custom attributes to manage environment-specific configurations.

## Approach 1: Using Resource Scopes

The simplest approach is to use different scopes for different environments:

```python
from resource_manager.resources import ResourceManager

# Create resource manager
manager = ResourceManager()

# Base resources (common to all environments)
base_resources = {
    "database": {
        "desc": "Database",
        "provides": ["database.main"],
        "vars": {
            "engine": "postgres",
            "version": "13",
            "port": 5432
        }
    },
    "api_service": {
        "desc": "API Service",
        "provides": ["api.rest"],
        "requires": ["database.main"],
        "vars": {
            "port": 8080,
            "workers": 4
        }
    }
}
manager.add_resources(base_resources, scope="base")

# Development environment
dev_resources = {
    "database": {
        "desc": "Dev Database",
        "provides": ["database.main"],
        "vars": {
            "engine": "sqlite",  # Different for dev
            "path": "/tmp/dev.db",
            "port": None
        }
    },
    "api_service": {
        "desc": "Dev API Service",
        "provides": ["api.rest"],
        "requires": ["database.main"],
        "vars": {
            "port": 3000,  # Different for dev
            "workers": 1,  # Fewer workers in dev
            "debug": True  # Debug mode in dev
        }
    }
}
manager.add_resources(dev_resources, scope="development")

# Production environment
prod_resources = {
    "database": {
        "desc": "Production Database",
        "provides": ["database.main"],
        "vars": {
            "engine": "postgres",
            "host": "db.production.example.com",
            "port": 5432,
            "replicas": 3,  # HA setup in production
            "backup_enabled": True
        }
    },
    "api_service": {
        "desc": "Production API Service",
        "provides": ["api.rest"],
        "requires": ["database.main"],
        "vars": {
            "port": 80,
            "workers": 16,  # More workers in production
            "tls_enabled": True
        }
    }
}
manager.add_resources(prod_resources, scope="production")

# Function to create an environment-specific resolver
def create_env_resolver(env_name, feature_names=None):
    """Create a resolver for a specific environment."""
    # Create a new manager for the resolved resources
    env_manager = ResourceManager()
    
    # Add base resources first
    for resource in manager.get_resources(scope="base"):
        env_manager.add_resource(
            resource.name,
            scope="app",
            config=resource
        )
    
    # Override with environment-specific resources
    for resource in manager.get_resources(scope=env_name):
        env_manager.add_resource(
            resource.name,
            scope="app",
            config=resource,
            force=True  # Override base resources
        )
    
    # Create and return resolver
    from resource_manager.resolver import DepBuilder
    resolver = DepBuilder(
        resources=env_manager,
        feature_names=feature_names or ["api.rest"]
    )
    resolver.resolve()
    return resolver

# Use the function to get environment-specific resolvers
dev_resolver = create_env_resolver("development")
prod_resolver = create_env_resolver("production")

# Print dependency orders
print("Development dependencies:", dev_resolver.dep_order)
print("Production dependencies:", prod_resolver.dep_order)

# Access environment-specific configurations
dev_db = dev_resolver.rmanager.get_resource("database")
prod_db = prod_resolver.rmanager.get_resource("database")

print("Dev database engine:", dev_db.engine)  # sqlite
print("Prod database engine:", prod_db.engine)  # postgres
```

## Approach 2: Using Environment Attribute

Add an environment attribute to resources and use a custom resolver:

```python
from resource_manager.resources import Resource, ResourceManager
from resource_manager.resolver import DepBuilder

class EnvironmentAwareResource(Resource):
    """Resource with environment awareness."""
    default_attrs = {
        "environment": None,  # Can be "development", "staging", "production", or None (all)
    }

class EnvironmentResourceManager(ResourceManager):
    """Manager for environment-aware resources."""
    resource_class = EnvironmentAwareResource

class EnvironmentDepBuilder(DepBuilder):
    """Environment-aware dependency resolver."""
    
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
        
        # Filter for environment-specific or environment-agnostic providers
        env_providers = []
        for provider in potential_providers:
            resource = provider.resource
            res_env = resource.environment
            
            # Include if environment matches or if resource applies to all environments
            if res_env is None or res_env == self.environment:
                env_providers.append(provider)
        
        # Match using filtered providers
        if env_providers:
            match_name, provider_links = requirement.match_provider(
                env_providers,
                remap_rules=self.remap_rules,
                default_mode="one",
                remap_requirement=True,
            )
            if provider_links:
                return match_name, provider_links
        
        # Fall back to default matching if no environment-specific providers found
        match_name, provider_links = requirement.match_provider(
            self.provider_links,
            remap_rules=self.remap_rules,
            default_mode="one",
            remap_requirement=True,
        )
        return match_name, provider_links

# Create environment-aware manager
manager = EnvironmentResourceManager()

# Add resources with environment attribute
manager.add_resource(
    "sqlite_db",
    config={
        "desc": "SQLite database for development",
        "provides": ["database.main"],
        "environment": "development",
        "vars": {
            "path": "/tmp/dev.db"
        }
    }
)

manager.add_resource(
    "postgres_db",
    config={
        "desc": "PostgreSQL database for production",
        "provides": ["database.main"],
        "environment": "production",
        "vars": {
            "host": "db.example.com",
            "port": 5432
        }
    }
)

manager.add_resource(
    "api_service",
    config={
        "desc": "API service with different configs per environment",
        "requires": ["database.main"],
        "provides": ["api.rest"],
        "vars": {
            "port": 8080
        }
    }
)

manager.add_resource(
    "dev_logger",
    config={
        "desc": "Development-only logger",
        "provides": ["logging.service"],
        "environment": "development",
        "vars": {
            "level": "DEBUG",
            "output": "console"
        }
    }
)

manager.add_resource(
    "prod_logger",
    config={
        "desc": "Production logger with file output",
        "provides": ["logging.service"],
        "environment": "production",
        "vars": {
            "level": "WARNING",
            "output": "file",
            "file_path": "/var/log/app.log"
        }
    }
)

# Add a service that requires logging
manager.add_resource(
    "web_app",
    config={
        "desc": "Web application",
        "requires": ["api.rest", "logging.service"],
        "provides": ["app.web"]
    }
)

# Resolve for development environment
dev_resolver = EnvironmentDepBuilder(
    environment="development",
    resources=manager,
    feature_names=["app.web"]
)
dev_resolver.resolve()

# Resolve for production environment
prod_resolver = EnvironmentDepBuilder(
    environment="production",
    resources=manager,
    feature_names=["app.web"]
)
prod_resolver.resolve()

# Print resolved dependency orders
print("Development dependencies:", dev_resolver.dep_order)
print("Production dependencies:", prod_resolver.dep_order)
```

## Approach 3: Environment Configuration Files

For larger applications, manage environment configs in separate files:

```python
import yaml
from resource_manager.resources import ResourceManager
from resource_manager.resolver import DepBuilder

# Load environments from YAML files
def load_environment_config(base_path, env_name):
    """Load resource configurations from YAML files."""
    # Load base config
    with open(f"{base_path}/base.yaml", "r") as f:
        base_config = yaml.safe_load(f)
    
    # Load environment-specific config
    with open(f"{base_path}/{env_name}.yaml", "r") as f:
        env_config = yaml.safe_load(f)
    
    # Merge configurations
    merged_config = base_config.copy()
    
    # Override/add environment-specific resources
    for resource_name, resource_config in env_config.items():
        if resource_name in merged_config:
            # Deep merge for existing resources
            for key, value in resource_config.items():
                if key == "vars" and "vars" in merged_config[resource_name]:
                    # Merge variables
                    merged_config[resource_name]["vars"].update(value)
                else:
                    # Override other attributes
                    merged_config[resource_name][key] = value
        else:
            # Add new resources
            merged_config[resource_name] = resource_config
    
    return merged_config

# Example YAML file structures:
# base.yaml:
# ```yaml
# database:
#   desc: Database
#   provides: ["database.main"]
#   vars:
#     engine: postgres
#     port: 5432
# 
# api_service:
#   desc: API Service
#   requires: ["database.main"]
#   provides: ["api.rest"]
#   vars:
#     port: 8080
# ```
#
# development.yaml:
# ```yaml
# database:
#   vars:
#     engine: sqlite
#     path: /tmp/dev.db
#     port: null
# 
# api_service:
#   vars:
#     port: 3000
#     debug: true
# ```
#
# production.yaml:
# ```yaml
# database:
#   vars:
#     host: db.production.example.com
#     replicas: 3
#     backup_enabled: true
# 
# api_service:
#   vars:
#     port: 80
#     workers: 16
#     tls_enabled: true
# ```

# Usage:
def create_environment(base_path, env_name, feature_names=None):
    """Create a resolver for a specific environment using YAML configs."""
    # Load merged configuration
    config = load_environment_config(base_path, env_name)
    
    # Create resource manager and add resources
    manager = ResourceManager()
    manager.add_resources(config)
    
    # Create resolver
    resolver = DepBuilder(
        resources=manager,
        feature_names=feature_names or ["api.rest"]
    )
    resolver.resolve()
    
    return resolver

# Example usage:
# dev_resolver = create_environment("./configs", "development")
# prod_resolver = create_environment("./configs", "production")
```

## Best Practices

1. **Use standardized naming**: Keep resource names consistent across environments
2. **Document differences**: Clearly document which attributes change between environments
3. **Validate configurations**: Add validation to ensure required attributes are present
4. **Limit environment differences**: Minimize differences between environments to reduce complexity
5. **Use inheritance**: Start with base configurations and override only what changes
6. **Test all environments**: Test your application in each environment configuration
7. **Version control**: Store environment configurations in version control
8. **Use environment variables**: For sensitive values, use environment variables instead of hardcoding

## Common Issues and Solutions

### Issue: Resource Found in One Environment But Not Another

If a resource is found in one environment but not another:

```python
# Problem: Resource exists in development but not production
# Solution: Use optional requirements or check environment

# Using optional requirements
manager.add_resource(
    "web_app",
    config={
        "desc": "Web application",
        "requires": [
            "api.rest", 
            "logging.service?",  # Optional requirement
            "dev.tool?"          # Optional dev-only requirement
        ]
    }
)

# Or check environment in resolver
class SafeEnvironmentResolver(EnvironmentDepBuilder):
    def _get_dependencies(self, debug=False):
        try:
            return super()._get_dependencies(debug)
        except Exception as e:
            print(f"Warning: Resolution error in {self.environment}: {e}")
            # Handle gracefully, perhaps with default dependencies
            return {}
```

### Issue: Different Dependency Structures Per Environment

If dependency structure changes significantly between environments:

```python
# Create environment-specific resolvers with different logic
class DevResolver(DepBuilder):
    def resolve_requirements(self, requirement, lvl=0):
        # Development-specific resolution logic
        # ...

class ProdResolver(DepBuilder):
    def resolve_requirements(self, requirement, lvl=0):
        # Production-specific resolution logic
        # ...

# Use the appropriate resolver based on environment
resolver_class = DevResolver if env == "development" else ProdResolver
resolver = resolver_class(resources=manager, feature_names=["app.main"])
```

### Issue: Testing Environment Configurations

To test environment configurations:

```python
def validate_environment_config(resolver, required_resources):
    """Validate that all required resources are present in resolved dependencies."""
    resolved_resources = set(resolver.dep_order)
    missing = set(required_resources) - resolved_resources
    
    if missing:
        raise ValueError(f"Missing required resources: {missing}")
    
    return True

# Test development environment
dev_resolver = create_env_resolver("development")
validate_environment_config(
    dev_resolver, 
    ["database", "api_service", "web_app"]
)

# Test production environment
prod_resolver = create_env_resolver("production")
validate_environment_config(
    prod_resolver, 
    ["database", "api_service", "web_app", "logging_service"]
)
```

## Summary

Managing multiple environments with the Resource Manager involves:

1. **Resource Scopes**: Organize resources by environment scope
2. **Environment Attributes**: Add environment flags to resources
3. **Custom Resolvers**: Create environment-aware dependency resolution
4. **Configuration Files**: Manage environment differences in structured files
5. **Inheritance**: Start with base configurations and override as needed

These approaches allow you to maintain consistent resource structure while accommodating environment-specific differences in your applications. 