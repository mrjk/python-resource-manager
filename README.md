# Python Resource Manager

[![PyPI version](https://img.shields.io/pypi/v/resource_manager.svg)](https://pypi.org/project/resource_manager/)
[![Python versions](https://img.shields.io/pypi/pyversions/resource_manager.svg)](https://pypi.org/project/resource_manager/)
[![License](https://img.shields.io/pypi/l/resource_manager.svg)](https://github.com/mrjk/python-resource-manager/blob/main/LICENSE)

A powerful Python library for efficiently managing and resolving resources with dependency management.

## Features

- Resource dependency resolution
- Link management between resources
- Custom exception handling for resource conflicts
- Flexible resource definition and manipulation
- Thread-safe resource management

## Installation

```bash
pip install resource_manager
```

Or using Poetry:

```bash
poetry add resource_manager
```

## Quick Start

```python
from resource_manager import ResourceManager

# Create a resource manager
rm = ResourceManager()

# Define resources
rm.add_resource("database", {
    "host": "localhost",
    "port": 5432,
    "username": "user",
    "password": "password"
})

rm.add_resource("web_app", {
    "port": 8080,
    "depends_on": ["database"]
})

# Resolve resources
resolved = rm.resolve()

# Access resources
database = resolved.get("database")
web_app = resolved.get("web_app")
```

## Documentation

Complete documentation can be found at [https://mrjk.github.io/python-resource-manager/](https://mrjk.github.io/python-resource-manager/)

## Examples

The `examples/` directory contains various usage examples:

- Basic resource management
- Dependency resolution
- Error handling
- Advanced configurations

## Core Concepts

### Resources

Resources are the basic building blocks managed by this library. Each resource has:
- A unique identifier
- Properties and attributes
- Optional dependencies on other resources

### Links

Links define relationships between resources, allowing for complex dependency graphs and resource hierarchies.

### Resolver

The resolver is responsible for analyzing resource dependencies and providing a consistent, resolved view of all resources.

## Development

### Prerequisites

- Python 3.9+
- Poetry

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/mrjk/python-resource-manager.git
cd python-resource-manager

# Install dependencies
poetry install
```

### Running Tests

```bash
poetry run pytest
```

### Code Quality

```bash
# Run linters
poetry run black resource_manager tests
poetry run pylint resource_manager
```

## License

This project is licensed under the GNU General Public License v3 (GPLv3) - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for details on version history and changes.

## Authors

- **mrjk** - [GitHub](https://github.com/mrjk)

## Acknowledgments

- Thanks to all contributors who have helped shape this project
- Inspired by dependency resolution systems in various software ecosystems
