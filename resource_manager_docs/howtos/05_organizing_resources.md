# How to Organize Resources in Complex Applications

This guide provides best practices for organizing resources in complex applications using the Resource Manager.

## Problem

As applications grow, managing resources becomes more challenging:

1. Large numbers of resources become difficult to track
2. Overlapping dependencies create confusing relationships
3. Resources with similar purposes but different implementations need to be managed
4. Configuration becomes scattered and hard to maintain
5. Teams need to work on different parts of the application

## Solution

Implement structured organization patterns for resources to make the system more maintainable.

## Using Resource Scopes

Scopes provide a way to categorize resources:

```python
from resource_manager.resources import ResourceManager

# Create a resource manager
manager = ResourceManager()

# Group resources by scope
manager.add_resource(
    "user_repository",
    scope="core",  # Core business logic
    config={
        "desc": "User data repository",
        "provides": ["repository.users"]
    }
)

manager.add_resource(
    "user_service",
    scope="core",  # Core business logic
    config={
        "desc": "User business service",
        "provides": ["service.users"],
        "requires": ["repository.users"]
    }
)

manager.add_resource(
    "postgres_db",
    scope="infrastructure",  # Infrastructure resources
    config={
        "desc": "PostgreSQL database",
        "provides": ["database.postgres"]
    }
)

manager.add_resource(
    "database_adapter",
    scope="infrastructure",  # Infrastructure resources
    config={
        "desc": "Database adapter",
        "provides": ["repository.users"],
        "requires": ["database.postgres"]
    }
)

manager.add_resource(
    "api_controller",
    scope="web",  # Web layer
    config={
        "desc": "User API controller",
        "provides": ["controller.users"],
        "requires": ["service.users"]
    }
)

manager.add_resource(
    "web_server",
    scope="web",  # Web layer
    config={
        "desc": "Web server",
        "provides": ["server.http"],
        "requires": ["controller.users"]
    }
)

# Get resources by scope
core_resources = manager.get_resources(scope="core")
infra_resources = manager.get_resources(scope="infrastructure")
web_resources = manager.get_resources(scope="web")

print(f"Core resources: {[r.name for r in core_resources]}")
print(f"Infrastructure resources: {[r.name for r in infra_resources]}")
print(f"Web resources: {[r.name for r in web_resources]}")
```

## Using Resource Groups

Add a group attribute to resources for more flexible organization:

```python
from resource_manager.resources import Resource, ResourceManager

class GroupedResource(Resource):
    """Resource with group support."""
    default_attrs = {
        "group": None,
        "subgroup": None,
    }

class GroupedResourceManager(ResourceManager):
    """Manager with enhanced grouping support."""
    resource_class = GroupedResource
    
    def get_resources_by_group(self, group=None, subgroup=None):
        """Get resources by group and optional subgroup."""
        result = []
        for resource in self.catalog.values():
            if group is not None and resource.group != group:
                continue
            if subgroup is not None and resource.subgroup != subgroup:
                continue
            result.append(resource)
        return result

# Create manager and add resources
manager = GroupedResourceManager()

# Group resources by function
manager.add_resource(
    "mysql_db",
    config={
        "desc": "MySQL database",
        "provides": ["database.mysql"],
        "group": "storage",
        "subgroup": "relational"
    }
)

manager.add_resource(
    "postgres_db",
    config={
        "desc": "PostgreSQL database",
        "provides": ["database.postgres"],
        "group": "storage",
        "subgroup": "relational"
    }
)

manager.add_resource(
    "redis_cache",
    config={
        "desc": "Redis cache",
        "provides": ["cache.redis"],
        "group": "storage",
        "subgroup": "caching"
    }
)

manager.add_resource(
    "user_service",
    config={
        "desc": "User service",
        "provides": ["service.users"],
        "requires": ["database.mysql"],
        "group": "business",
        "subgroup": "users"
    }
)

manager.add_resource(
    "order_service",
    config={
        "desc": "Order service",
        "provides": ["service.orders"],
        "requires": ["database.postgres", "service.users"],
        "group": "business",
        "subgroup": "orders"
    }
)

manager.add_resource(
    "auth_service",
    config={
        "desc": "Auth service",
        "provides": ["service.auth"],
        "requires": ["database.mysql", "cache.redis"],
        "group": "security",
        "subgroup": "authentication"
    }
)

# Get resources by group
storage_resources = manager.get_resources_by_group(group="storage")
business_resources = manager.get_resources_by_group(group="business")
relational_dbs = manager.get_resources_by_group(group="storage", subgroup="relational")

print(f"Storage resources: {[r.name for r in storage_resources]}")
print(f"Business resources: {[r.name for r in business_resources]}")
print(f"Relational databases: {[r.name for r in relational_dbs]}")
```

## Layered Architecture

Organize resources in layers following clean architecture principles:

```python
from resource_manager.resources import Resource, ResourceManager

class LayeredResource(Resource):
    """Resource with layer information."""
    default_attrs = {
        "layer": None,
    }

class LayeredResourceManager(ResourceManager):
    """Manager for layered architecture."""
    resource_class = LayeredResource
    
    def get_resources_by_layer(self, layer):
        """Get all resources in a specific layer."""
        return [r for r in self.catalog.values() if r.layer == layer]
    
    def get_layers(self):
        """Get all layers used in the application."""
        return sorted(set(r.layer for r in self.catalog.values() if r.layer))

# Define layers
DOMAIN_LAYER = "domain"
APPLICATION_LAYER = "application"
INFRASTRUCTURE_LAYER = "infrastructure"
PRESENTATION_LAYER = "presentation"

# Create manager
manager = LayeredResourceManager()

# Domain layer (business rules)
manager.add_resource(
    "user_entity",
    config={
        "desc": "User entity",
        "provides": ["entity.user"],
        "layer": DOMAIN_LAYER
    }
)

manager.add_resource(
    "order_entity",
    config={
        "desc": "Order entity",
        "provides": ["entity.order"],
        "layer": DOMAIN_LAYER
    }
)

# Application layer (use cases)
manager.add_resource(
    "user_service",
    config={
        "desc": "User service",
        "provides": ["service.users"],
        "requires": ["entity.user", "repository.users"],
        "layer": APPLICATION_LAYER
    }
)

manager.add_resource(
    "order_service",
    config={
        "desc": "Order service",
        "provides": ["service.orders"],
        "requires": ["entity.order", "repository.orders", "service.users"],
        "layer": APPLICATION_LAYER
    }
)

# Infrastructure layer (adapters)
manager.add_resource(
    "user_repository",
    config={
        "desc": "User repository implementation",
        "provides": ["repository.users"],
        "requires": ["database.postgres"],
        "layer": INFRASTRUCTURE_LAYER
    }
)

manager.add_resource(
    "order_repository",
    config={
        "desc": "Order repository implementation",
        "provides": ["repository.orders"],
        "requires": ["database.postgres"],
        "layer": INFRASTRUCTURE_LAYER
    }
)

manager.add_resource(
    "postgres_db",
    config={
        "desc": "PostgreSQL database",
        "provides": ["database.postgres"],
        "layer": INFRASTRUCTURE_LAYER
    }
)

# Presentation layer (UI/API)
manager.add_resource(
    "user_controller",
    config={
        "desc": "User API controller",
        "provides": ["controller.users"],
        "requires": ["service.users"],
        "layer": PRESENTATION_LAYER
    }
)

manager.add_resource(
    "order_controller",
    config={
        "desc": "Order API controller",
        "provides": ["controller.orders"],
        "requires": ["service.orders"],
        "layer": PRESENTATION_LAYER
    }
)

manager.add_resource(
    "web_server",
    config={
        "desc": "Web server",
        "provides": ["server.http"],
        "requires": ["controller.users", "controller.orders"],
        "layer": PRESENTATION_LAYER
    }
)

# Get all layers
layers = manager.get_layers()
print("Application layers:", layers)

# Print resources by layer
for layer in layers:
    resources = manager.get_resources_by_layer(layer)
    print(f"{layer.capitalize()} layer: {[r.name for r in resources]}")
```

## Module-Based Organization

For large applications, organize resources in modules:

```python
from resource_manager.resources import Resource, ResourceManager

class ModularResource(Resource):
    """Resource with module information."""
    default_attrs = {
        "module": None,
    }

class ModularResourceManager(ResourceManager):
    """Manager for modular application."""
    resource_class = ModularResource
    
    def get_resources_by_module(self, module):
        """Get all resources in a specific module."""
        return [r for r in self.catalog.values() if r.module == module]
    
    def get_modules(self):
        """Get all modules in the application."""
        return sorted(set(r.module for r in self.catalog.values() if r.module))

# Create manager
manager = ModularResourceManager()

# Users module
manager.add_resource(
    "user_entity",
    config={
        "desc": "User entity",
        "provides": ["entity.user"],
        "module": "users"
    }
)

manager.add_resource(
    "user_repository",
    config={
        "desc": "User repository",
        "provides": ["repository.users"],
        "requires": ["database.main"],
        "module": "users"
    }
)

manager.add_resource(
    "user_service",
    config={
        "desc": "User service",
        "provides": ["service.users"],
        "requires": ["entity.user", "repository.users"],
        "module": "users"
    }
)

manager.add_resource(
    "user_controller",
    config={
        "desc": "User controller",
        "provides": ["controller.users"],
        "requires": ["service.users"],
        "module": "users"
    }
)

# Orders module
manager.add_resource(
    "order_entity",
    config={
        "desc": "Order entity",
        "provides": ["entity.order"],
        "module": "orders"
    }
)

manager.add_resource(
    "order_repository",
    config={
        "desc": "Order repository",
        "provides": ["repository.orders"],
        "requires": ["database.main"],
        "module": "orders"
    }
)

manager.add_resource(
    "order_service",
    config={
        "desc": "Order service",
        "provides": ["service.orders"],
        "requires": ["entity.order", "repository.orders", "service.users"],
        "module": "orders"
    }
)

manager.add_resource(
    "order_controller",
    config={
        "desc": "Order controller",
        "provides": ["controller.orders"],
        "requires": ["service.orders"],
        "module": "orders"
    }
)

# Shared infrastructure module
manager.add_resource(
    "database",
    config={
        "desc": "Main database",
        "provides": ["database.main"],
        "module": "infrastructure"
    }
)

manager.add_resource(
    "cache",
    config={
        "desc": "Cache service",
        "provides": ["cache.main"],
        "module": "infrastructure"
    }
)

manager.add_resource(
    "web_server",
    config={
        "desc": "Web server",
        "provides": ["server.http"],
        "requires": ["controller.users", "controller.orders"],
        "module": "infrastructure"
    }
)

# Get all modules
modules = manager.get_modules()
print("Application modules:", modules)

# Print resources by module
for module in modules:
    resources = manager.get_resources_by_module(module)
    print(f"{module.capitalize()} module: {[r.name for r in resources]}")
```

## Feature-Based Organization

Organize resources by features for better maintainability:

```python
from resource_manager.resources import Resource, ResourceManager

class FeatureResource(Resource):
    """Resource with feature information."""
    default_attrs = {
        "feature": None,
        "layer": None,
    }

class FeatureResourceManager(ResourceManager):
    """Manager for feature-based organization."""
    resource_class = FeatureResource
    
    def get_resources_by_feature(self, feature):
        """Get all resources in a specific feature."""
        return [r for r in self.catalog.values() if r.feature == feature]
    
    def get_features(self):
        """Get all features in the application."""
        return sorted(set(r.feature for r in self.catalog.values() if r.feature))

# Create manager
manager = FeatureResourceManager()

# User management feature
manager.add_resource(
    "user_entity",
    config={
        "desc": "User entity",
        "provides": ["entity.user"],
        "feature": "user_management",
        "layer": "domain"
    }
)

manager.add_resource(
    "user_repository",
    config={
        "desc": "User repository",
        "provides": ["repository.users"],
        "requires": ["database.main"],
        "feature": "user_management",
        "layer": "infrastructure"
    }
)

manager.add_resource(
    "user_service",
    config={
        "desc": "User service",
        "provides": ["service.users"],
        "requires": ["entity.user", "repository.users"],
        "feature": "user_management",
        "layer": "application"
    }
)

manager.add_resource(
    "user_controller",
    config={
        "desc": "User controller",
        "provides": ["controller.users"],
        "requires": ["service.users"],
        "feature": "user_management",
        "layer": "presentation"
    }
)

# Order processing feature
manager.add_resource(
    "order_entity",
    config={
        "desc": "Order entity",
        "provides": ["entity.order"],
        "feature": "order_processing",
        "layer": "domain"
    }
)

manager.add_resource(
    "order_repository",
    config={
        "desc": "Order repository",
        "provides": ["repository.orders"],
        "requires": ["database.main"],
        "feature": "order_processing",
        "layer": "infrastructure"
    }
)

manager.add_resource(
    "order_service",
    config={
        "desc": "Order service",
        "provides": ["service.orders"],
        "requires": ["entity.order", "repository.orders", "service.users"],
        "feature": "order_processing",
        "layer": "application"
    }
)

manager.add_resource(
    "order_controller",
    config={
        "desc": "Order controller",
        "provides": ["controller.orders"],
        "requires": ["service.orders"],
        "feature": "order_processing",
        "layer": "presentation"
    }
)

# Shared resources
manager.add_resource(
    "database",
    config={
        "desc": "Main database",
        "provides": ["database.main"],
        "feature": "shared",
        "layer": "infrastructure"
    }
)

manager.add_resource(
    "web_server",
    config={
        "desc": "Web server",
        "provides": ["server.http"],
        "requires": ["controller.users", "controller.orders"],
        "feature": "shared",
        "layer": "infrastructure"
    }
)

# Get all features
features = manager.get_features()
print("Application features:", features)

# Print resources by feature
for feature in features:
    resources = manager.get_resources_by_feature(feature)
    print(f"{feature.replace('_', ' ').title()} feature: {[r.name for r in resources]}")
```

## Configuration Management

Keep resource configurations in external files:

```python
import yaml
from resource_manager.resources import ResourceManager
from resource_manager.resolver import DepBuilder

# Example YAML config structure:
"""
# infrastructure.yaml
database:
  desc: Main database
  provides:
    - database.main
  vars:
    host: localhost
    port: 5432

cache:
  desc: Redis cache
  provides:
    - cache.redis
  vars:
    host: localhost
    port: 6379

# users.yaml
user_repository:
  desc: User repository
  provides:
    - repository.users
  requires:
    - database.main
  vars:
    table_name: users

user_service:
  desc: User service
  provides:
    - service.users
  requires:
    - repository.users
    - cache.redis?
"""

def load_resources_from_yaml(file_path):
    """Load resources from a YAML file."""
    with open(file_path, 'r') as f:
        config = yaml.safe_load(f)
    
    if not config:
        return {}
    
    return config

def load_application_resources(config_dir):
    """Load resources from multiple configuration files."""
    manager = ResourceManager()
    
    # Load infrastructure resources
    infra_config = load_resources_from_yaml(f"{config_dir}/infrastructure.yaml")
    manager.add_resources(infra_config, scope="infrastructure")
    
    # Load business resources
    users_config = load_resources_from_yaml(f"{config_dir}/users.yaml")
    manager.add_resources(users_config, scope="business")
    
    # Load presentation resources
    api_config = load_resources_from_yaml(f"{config_dir}/api.yaml")
    manager.add_resources(api_config, scope="presentation")
    
    return manager

# Usage example (assuming the YAML files exist)
# manager = load_application_resources("./config")
# resolver = DepBuilder(resources=manager, feature_names=["server.http"])
# resolver.resolve()
```

## Namespace Conventions

Use consistent naming conventions to organize resources:

```python
from resource_manager.resources import ResourceManager

# Create a resource manager
manager = ResourceManager()

# Use a consistent naming convention for resources
# Format: [domain].[type].[name]

# Infrastructure domain
manager.add_resource(
    "postgres_db",
    config={
        "desc": "PostgreSQL database",
        "provides": ["infra.db.postgres"]
    }
)

manager.add_resource(
    "redis_cache",
    config={
        "desc": "Redis cache",
        "provides": ["infra.cache.redis"]
    }
)

# Core domain
manager.add_resource(
    "user_repository",
    config={
        "desc": "User repository",
        "provides": ["core.repo.users"],
        "requires": ["infra.db.postgres"]
    }
)

manager.add_resource(
    "user_service",
    config={
        "desc": "User service",
        "provides": ["core.service.users"],
        "requires": ["core.repo.users", "infra.cache.redis?"]
    }
)

# API domain
manager.add_resource(
    "user_controller",
    config={
        "desc": "User API controller",
        "provides": ["api.controller.users"],
        "requires": ["core.service.users"]
    }
)

manager.add_resource(
    "web_server",
    config={
        "desc": "Web server",
        "provides": ["api.server.http"],
        "requires": ["api.controller.users"]
    }
)
```

## Dependency Management

Use dependency abstractions to create more maintainable systems:

```python
from resource_manager.resources import ResourceManager

# Create a resource manager
manager = ResourceManager()

# 1. Use dependency inversion - depend on abstractions, not implementations

# Infrastructure implementations
manager.add_resource(
    "postgres_impl",
    config={
        "desc": "PostgreSQL implementation",
        "provides": ["persistence.sql.postgres", "persistence.repository"]
    }
)

manager.add_resource(
    "mongodb_impl",
    config={
        "desc": "MongoDB implementation",
        "provides": ["persistence.nosql.mongodb", "persistence.repository"]
    }
)

# Business layer depends on the abstraction
manager.add_resource(
    "user_service",
    config={
        "desc": "User service",
        "provides": ["service.users"],
        "requires": ["persistence.repository"]  # Abstract dependency
    }
)

# 2. Use adapter pattern for external dependencies

manager.add_resource(
    "payment_gateway_adapter",
    config={
        "desc": "Payment gateway adapter",
        "provides": ["payment.processor"],  # Abstract interface
        "requires": ["payment.stripe"]      # Concrete implementation
    }
)

manager.add_resource(
    "stripe_service",
    config={
        "desc": "Stripe payment service",
        "provides": ["payment.stripe"]
    }
)

# Business layer depends on the abstraction
manager.add_resource(
    "order_service",
    config={
        "desc": "Order service",
        "provides": ["service.orders"],
        "requires": ["payment.processor"]  # Abstract dependency
    }
)
```

## Bounded Contexts

Implement domain-driven design bounded contexts:

```python
from resource_manager.resources import Resource, ResourceManager

class BoundedContextResource(Resource):
    """Resource with bounded context support."""
    default_attrs = {
        "bounded_context": None,
    }

class BoundedContextManager(ResourceManager):
    """Resource manager for domain-driven design with bounded contexts."""
    resource_class = BoundedContextResource
    
    def get_resources_by_context(self, context):
        """Get all resources in a specific bounded context."""
        return [r for r in self.catalog.values() if r.bounded_context == context]
    
    def get_contexts(self):
        """Get all bounded contexts."""
        return sorted(set(r.bounded_context for r in self.catalog.values() 
                        if r.bounded_context))

# Create manager
manager = BoundedContextManager()

# User context
manager.add_resource(
    "user_entity",
    config={
        "desc": "User entity",
        "provides": ["user.entity"],
        "bounded_context": "user_management"
    }
)

manager.add_resource(
    "user_repository",
    config={
        "desc": "User repository",
        "provides": ["user.repository"],
        "requires": ["database.main"],
        "bounded_context": "user_management"
    }
)

manager.add_resource(
    "user_service",
    config={
        "desc": "User service",
        "provides": ["user.service"],
        "requires": ["user.entity", "user.repository"],
        "bounded_context": "user_management"
    }
)

# Order context
manager.add_resource(
    "order_entity",
    config={
        "desc": "Order entity",
        "provides": ["order.entity"],
        "bounded_context": "order_processing"
    }
)

manager.add_resource(
    "order_repository",
    config={
        "desc": "Order repository",
        "provides": ["order.repository"],
        "requires": ["database.main"],
        "bounded_context": "order_processing"
    }
)

manager.add_resource(
    "order_service",
    config={
        "desc": "Order service",
        "provides": ["order.service"],
        "requires": ["order.entity", "order.repository", "customer.service"],
        "bounded_context": "order_processing"
    }
)

# Define context mappings for integration
manager.add_resource(
    "customer_mapping",
    config={
        "desc": "Maps user concept to customer concept",
        "provides": ["customer.service"],
        "requires": ["user.service"],
        "bounded_context": "context_mapping"
    }
)

# Shared infrastructure
manager.add_resource(
    "database",
    config={
        "desc": "Main database",
        "provides": ["database.main"],
        "bounded_context": "shared_infrastructure"
    }
)

# Get all contexts
contexts = manager.get_contexts()
print("Bounded contexts:", contexts)

# Print resources by context
for context in contexts:
    resources = manager.get_resources_by_context(context)
    print(f"{context.replace('_', ' ').title()} context: {[r.name for r in resources]}")
```

## Practical Example: E-Commerce System

Here's a complete example for an e-commerce application:

```python
from resource_manager.resources import Resource, ResourceManager
from resource_manager.resolver import DepBuilder

class AppResource(Resource):
    """Enhanced resource with organizational attributes."""
    default_attrs = {
        "module": None,
        "layer": None,
        "bounded_context": None,
    }

class AppResourceManager(ResourceManager):
    """Enhanced resource manager with organizational capabilities."""
    resource_class = AppResource

# Create manager
manager = AppResourceManager()

# Catalog bounded context
catalog_resources = {
    "product_entity": {
        "desc": "Product entity",
        "provides": ["entity.product"],
        "module": "catalog",
        "layer": "domain",
        "bounded_context": "product_catalog"
    },
    "category_entity": {
        "desc": "Category entity",
        "provides": ["entity.category"],
        "module": "catalog",
        "layer": "domain",
        "bounded_context": "product_catalog"
    },
    "product_repository": {
        "desc": "Product repository",
        "provides": ["repository.products"],
        "requires": ["database.products"],
        "module": "catalog",
        "layer": "infrastructure",
        "bounded_context": "product_catalog"
    },
    "category_repository": {
        "desc": "Category repository",
        "provides": ["repository.categories"],
        "requires": ["database.categories"],
        "module": "catalog",
        "layer": "infrastructure",
        "bounded_context": "product_catalog"
    },
    "product_service": {
        "desc": "Product service",
        "provides": ["service.products"],
        "requires": ["entity.product", "repository.products"],
        "module": "catalog",
        "layer": "application",
        "bounded_context": "product_catalog"
    },
    "catalog_api": {
        "desc": "Catalog API",
        "provides": ["api.catalog"],
        "requires": ["service.products"],
        "module": "catalog",
        "layer": "presentation",
        "bounded_context": "product_catalog"
    }
}

# Order bounded context
order_resources = {
    "order_entity": {
        "desc": "Order entity",
        "provides": ["entity.order"],
        "module": "orders",
        "layer": "domain",
        "bounded_context": "order_processing"
    },
    "order_item_entity": {
        "desc": "Order item entity",
        "provides": ["entity.order_item"],
        "module": "orders",
        "layer": "domain",
        "bounded_context": "order_processing"
    },
    "order_repository": {
        "desc": "Order repository",
        "provides": ["repository.orders"],
        "requires": ["database.orders"],
        "module": "orders",
        "layer": "infrastructure",
        "bounded_context": "order_processing"
    },
    "order_service": {
        "desc": "Order service",
        "provides": ["service.orders"],
        "requires": [
            "entity.order",
            "repository.orders",
            "service.users",
            "service.products",
            "service.payment"
        ],
        "module": "orders",
        "layer": "application",
        "bounded_context": "order_processing"
    },
    "order_api": {
        "desc": "Order API",
        "provides": ["api.orders"],
        "requires": ["service.orders"],
        "module": "orders",
        "layer": "presentation",
        "bounded_context": "order_processing"
    }
}

# User bounded context
user_resources = {
    "user_entity": {
        "desc": "User entity",
        "provides": ["entity.user"],
        "module": "users",
        "layer": "domain",
        "bounded_context": "user_management"
    },
    "user_repository": {
        "desc": "User repository",
        "provides": ["repository.users"],
        "requires": ["database.users"],
        "module": "users",
        "layer": "infrastructure",
        "bounded_context": "user_management"
    },
    "auth_service": {
        "desc": "Authentication service",
        "provides": ["service.auth"],
        "requires": ["repository.users", "cache.main?"],
        "module": "users",
        "layer": "application",
        "bounded_context": "user_management"
    },
    "user_service": {
        "desc": "User service",
        "provides": ["service.users"],
        "requires": ["entity.user", "repository.users", "service.auth"],
        "module": "users",
        "layer": "application",
        "bounded_context": "user_management"
    },
    "user_api": {
        "desc": "User API",
        "provides": ["api.users"],
        "requires": ["service.users"],
        "module": "users",
        "layer": "presentation",
        "bounded_context": "user_management"
    }
}

# Payment bounded context
payment_resources = {
    "payment_entity": {
        "desc": "Payment entity",
        "provides": ["entity.payment"],
        "module": "payments",
        "layer": "domain",
        "bounded_context": "payment_processing"
    },
    "payment_repository": {
        "desc": "Payment repository",
        "provides": ["repository.payments"],
        "requires": ["database.payments"],
        "module": "payments",
        "layer": "infrastructure",
        "bounded_context": "payment_processing"
    },
    "payment_gateway": {
        "desc": "Payment gateway adapter",
        "provides": ["gateway.payment"],
        "requires": ["payment.stripe"],
        "module": "payments",
        "layer": "infrastructure",
        "bounded_context": "payment_processing"
    },
    "stripe_service": {
        "desc": "Stripe payment service",
        "provides": ["payment.stripe"],
        "module": "payments",
        "layer": "infrastructure",
        "bounded_context": "payment_processing"
    },
    "payment_service": {
        "desc": "Payment service",
        "provides": ["service.payment"],
        "requires": ["entity.payment", "repository.payments", "gateway.payment"],
        "module": "payments",
        "layer": "application",
        "bounded_context": "payment_processing"
    },
    "payment_api": {
        "desc": "Payment API",
        "provides": ["api.payments"],
        "requires": ["service.payment"],
        "module": "payments",
        "layer": "presentation",
        "bounded_context": "payment_processing"
    }
}

# Shared infrastructure
infra_resources = {
    "product_db": {
        "desc": "Product database",
        "provides": ["database.products", "database.categories"],
        "module": "infrastructure",
        "layer": "infrastructure",
        "bounded_context": "shared_infrastructure"
    },
    "user_db": {
        "desc": "User database",
        "provides": ["database.users"],
        "module": "infrastructure",
        "layer": "infrastructure",
        "bounded_context": "shared_infrastructure"
    },
    "order_db": {
        "desc": "Order database",
        "provides": ["database.orders"],
        "module": "infrastructure",
        "layer": "infrastructure",
        "bounded_context": "shared_infrastructure"
    },
    "payment_db": {
        "desc": "Payment database",
        "provides": ["database.payments"],
        "module": "infrastructure",
        "layer": "infrastructure",
        "bounded_context": "shared_infrastructure"
    },
    "redis_cache": {
        "desc": "Redis cache",
        "provides": ["cache.main"],
        "module": "infrastructure",
        "layer": "infrastructure",
        "bounded_context": "shared_infrastructure"
    },
    "web_server": {
        "desc": "Web server",
        "provides": ["server.http"],
        "requires": ["api.catalog", "api.orders", "api.users", "api.payments"],
        "module": "infrastructure",
        "layer": "infrastructure",
        "bounded_context": "shared_infrastructure"
    }
}

# Add all resources
manager.add_resources(catalog_resources)
manager.add_resources(order_resources)
manager.add_resources(user_resources)
manager.add_resources(payment_resources)
manager.add_resources(infra_resources)

# Resolve entire application
resolver = DepBuilder(
    resources=manager,
    feature_names=["server.http"]
)
resolver.resolve()

# Get resources by different organizational dimensions
def print_resources_by_dimension(manager, attribute):
    """Print resources organized by a specific dimension."""
    dimension_values = sorted(set(
        getattr(resource, attribute) 
        for resource in manager.catalog.values() 
        if getattr(resource, attribute)
    ))
    
    print(f"\nResources by {attribute}:")
    for value in dimension_values:
        resources = [
            resource.name 
            for resource in manager.catalog.values() 
            if getattr(resource, attribute) == value
        ]
        print(f"  {value}: {resources}")

# Print different views of the application
print_resources_by_dimension(manager, "module")
print_resources_by_dimension(manager, "layer")
print_resources_by_dimension(manager, "bounded_context")

# Print initialization order
print("\nInitialization order:")
print(resolver.dep_order)
```

## Best Practices

1. **Consistent naming**: Use a consistent naming convention for resources and capabilities
2. **Layered dependencies**: Organize resources in layers with clean dependency directions
3. **Bounded contexts**: Group related resources into bounded contexts with explicit boundaries
4. **Dependency inversion**: Depend on abstractions, not implementations
5. **Single responsibility**: Each resource should have a single responsibility
6. **Modular structure**: Organize resources in logical modules
7. **External configuration**: Store resource configurations in external files
8. **Abstraction layers**: Use abstraction layers to isolate external dependencies
9. **Minimal dependencies**: Minimize dependencies between resources
10. **Cross-cutting concerns**: Handle cross-cutting concerns as separate resources

## Common Issues and Solutions

### Issue: Circular Dependencies

```python
# Problem: Circular dependency
manager.add_resource(
    "service_a",
    config={
        "requires": ["service_b"]
    }
)

manager.add_resource(
    "service_b",
    config={
        "requires": ["service_a"]
    }
)

# Solution: Introduce an abstraction
manager.add_resource(
    "service_a",
    config={
        "provides": ["service.a", "interface.a"],
        "requires": ["interface.b"]
    }
)

manager.add_resource(
    "service_b",
    config={
        "provides": ["service.b", "interface.b"],
        "requires": ["interface.a"]
    }
)
```

### Issue: Tight Coupling

```python
# Problem: Direct dependency on implementation
manager.add_resource(
    "user_service",
    config={
        "requires": ["repository.postgres.users"]  # Direct dependency on postgres
    }
)

# Solution: Depend on abstraction
manager.add_resource(
    "user_service",
    config={
        "requires": ["repository.users"]  # Abstract dependency
    }
)

manager.add_resource(
    "postgres_repository",
    config={
        "provides": ["repository.users", "repository.postgres.users"]
    }
)
```

## Summary

Organizing resources effectively in complex applications requires:

1. **Consistent Structure**: Use scopes, groups, or attributes to categorize resources
2. **Clear Boundaries**: Define clear boundaries between different parts of the application
3. **Layered Architecture**: Organize resources in layers with clean dependency directions
4. **Modular Design**: Use modules to organize related resources
5. **Abstract Dependencies**: Depend on abstractions, not implementations
6. **External Configuration**: Store resource configurations in external files
7. **Clean Naming**: Use a consistent naming convention

These practices help manage complexity and make your application more maintainable as it grows.