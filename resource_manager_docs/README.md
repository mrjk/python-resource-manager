# Resource Manager Documentation

<div align="center">
  <h3>A powerful framework for managing resource dependencies in complex systems</h3>
</div>

## 📚 Documentation Overview

This documentation is organized to help you effectively learn and use the Resource Manager library:

### 🚀 [Getting Started](tutorials/01_introduction.md)
Begin your journey with the Resource Manager through our step-by-step tutorials:

1. [Introduction](tutorials/01_introduction.md) - Core concepts and benefits
2. [Basic Usage](tutorials/02_basic_usage.md) - Simple examples to get started
3. [Defining Resources](tutorials/03_defining_resources.md) - Detailed guide to resources
4. [Dependency Resolution](tutorials/04_dependency_resolution.md) - Understanding resolution
5. [Visualization](tutorials/05_visualization.md) - Creating dependency graphs
6. [Advanced Usage](tutorials/06_advanced_usage.md) - Advanced techniques

### 💡 [How-To Guides](howtos/README.md)
Practical solutions for common tasks:

1. [Custom Resolution](howtos/01_custom_resolution.md) - Customize resolution logic
2. [Multiple Environments](howtos/02_multiple_environments.md) - Dev, staging, production
3. [Feature Flags](howtos/03_feature_flags.md) - Implementing feature flags
4. [Optional Dependencies](howtos/04_optional_dependencies.md) - Handle optional resources
5. [Organizing Resources](howtos/05_organizing_resources.md) - Structure complex applications

### 🔍 [Implementation Details](implementation/README.md)
Understand how it works internally:

1. [Resource Model](implementation/resource_model.md) - Core resource concepts
2. [Resource Linking](implementation/resource_linking.md) - Link mechanics
3. [Dependency Resolution](implementation/dependency_resolution.md) - Resolution algorithm
4. [Extension Points](implementation/extension_points.md) - Extending the library

## 🌟 Quick Example

```python
from resource_manager.resources import ResourceManager
from resource_manager.resolver import DepBuilder

# Create a resource manager
manager = ResourceManager()

# Add resources with dependencies
manager.add_resource(
    "database",
    config={"provides": ["database.main"]}
)

manager.add_resource(
    "application",
    config={
        "requires": ["database.main"],
        "provides": ["app.web"]
    }
)

# Resolve dependencies
resolver = DepBuilder(resources=manager, feature_names=["app.web"])
resolver.resolve()

# Print the resolved dependency order
print("Dependency order:", resolver.dep_order)
```

## 🔗 Navigation

| Section | Description |
|---------|-------------|
| [Tutorials](tutorials/README.md) | Step-by-step learning path |
| [How-To Guides](howtos/README.md) | Task-oriented guides |
| [Implementation](implementation/README.md) | Technical details | 