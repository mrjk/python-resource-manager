# 🚀 Resource Manager Tutorials

<div align="center">
  <h3>Step-by-step guides to mastering the Resource Manager library</h3>
</div>

## 📋 Tutorial Series

Follow these tutorials in sequence to build your understanding from fundamentals to advanced concepts:

| # | Tutorial | Focus | Level |
|---|----------|-------|-------|
| 1 | [**Introduction**](01_introduction.md) | Core concepts and benefits | Beginner |
| 2 | [**Basic Usage**](02_basic_usage.md) | Simple examples to get started | Beginner |
| 3 | [**Defining Resources**](03_defining_resources.md) | Creating resource configurations | Intermediate |
| 4 | [**Dependency Resolution**](04_dependency_resolution.md) | How dependencies are resolved | Intermediate |
| 5 | [**Visualization**](05_visualization.md) | Creating dependency graphs | Intermediate |
| 6 | [**Advanced Usage**](06_advanced_usage.md) | Advanced patterns and customization | Advanced |

## 🔍 About Resource Manager

The Resource Manager is a Python library for managing dependencies between configurable components in a system. It provides a flexible framework for defining resources, their capabilities, and their requirements, with automatic dependency resolution and initialization order determination.

### Key Features

- **📦 Declarative Configuration** - Define resources and relationships declaratively
- **🧩 Automatic Resolution** - Let the system determine the correct initialization order
- **✅ Validation** - Ensure all dependencies are satisfied before runtime
- **🔌 Extensibility** - Customize how requirements are matched with providers
- **📊 Visualization** - Generate visual representations of dependency graphs

## 💻 Quick Start

Here's a simple example to get you started:

```python
from resource_manager.resources import ResourceManager
from resource_manager.resolver import DepBuilder

# Create a resource manager
manager = ResourceManager()

# Add resources
manager.add_resource(
    "database",
    config={
        "provides": ["database.main"]
    }
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

## 🤔 Getting Help

If you encounter issues or have questions, please check the [implementation documentation](../implementation/) or refer to the [how-to guides](../howtos/) for specific solutions.

## 🔄 Next Steps

After completing these tutorials, explore the [how-to guides](../howtos/README.md) for practical solutions to common tasks. 