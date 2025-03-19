# Advanced Usage Patterns

This tutorial explores advanced usage patterns and customization options for the Resource Manager.

## Custom Resource Classes

One of the most powerful ways to extend the Resource Manager is to create custom resource classes with specialized behavior:

```python
from resource_manager.resources import Resource, ResourceManager

class ConfigurableResource(Resource):
    """A resource with advanced configuration capabilities."""
    
    default_attrs = {
        "config_file": None,
        "auto_restart": True,
        "version": "latest",
        "port": 8000
    }
    
    def load_config(self):
        """Load configuration from file if specified."""
        if self.config_file:
            print(f"Loading config from {self.config_file}")
            # Actual implementation would load from file
            return {"loaded": True}
        return {"loaded": False}
    
    def generate_command(self):
        """Generate startup command based on configuration."""
        cmd = f"start_{self.name}"
        if self.version != "latest":
            cmd += f" --version={self.version}"
        if self.port:
            cmd += f" --port={self.port}"
        return cmd

# Create a custom resource manager that uses our resource class
class CustomManager(ResourceManager):
    resource_class = ConfigurableResource

# Use the custom manager
manager = CustomManager()

# Add resources with custom attributes
manager.add_resource(
    "api_server",
    scope="app",
    config={
        "desc": "API Server",
        "provides": ["api.rest"],
        "port": 8080,
        "version": "2.1.0",
        "config_file": "/etc/api/config.yaml"
    }
)

# Use custom methods
resource = manager.get_resource("api_server")
config = resource.load_config()
command = resource.generate_command()
print(f"Command: {command}")  # Output: Command: start_api_server --version=2.1.0 --port=8080
```

## Dependency Resolution Strategies

You can implement custom dependency resolution strategies by extending the `DepBuilder` class:

```python
from resource_manager.resolver import DepBuilder

class FeatureDepBuilder(DepBuilder):
    """A dependency resolver focused on feature-based resolution."""
    
    def resolve_requirements(self, requirement, lvl=0):
        """Custom resolution strategy that prioritizes feature-specific providers."""
        # Get all possible providers for this requirement
        potential_providers = [
            p for p in self.provider_links 
            if p.kind == requirement.kind
        ]
        
        # Try different matching strategies in order:
        
        # 1. First try to match the exact instance name
        if requirement.instance:
            exact_matches = [
                p for p in potential_providers 
                if p.instance == requirement.instance
            ]
            if exact_matches:
                return requirement.instance, exact_matches
        
        # 2. Use remapping rules if available
        match_name = None
        if self.remap_rules and requirement.kind in self.remap_rules:
            match_name = self.remap_rules[requirement.kind]
            remapped_matches = [
                p for p in potential_providers 
                if p.instance == match_name
            ]
            if remapped_matches:
                return match_name, remapped_matches
        
        # 3. Look for "feature" providers if the requirement kind is a feature
        if requirement.kind.startswith("feature."):
            feature_matches = [
                p for p in potential_providers 
                if p.resource.name.startswith("feature_")
            ]
            if feature_matches:
                return "feature", feature_matches
        
        # 4. Fall back to default matching
        match_name, provider_links = requirement.match_provider(
            self.provider_links,
            remap_rules=self.remap_rules,
            default_mode="one",
            remap_requirement=True,
        )
        
        return match_name, provider_links
```

## Working with Complex Dependency Scenarios

### 1. Optional Features

To implement optional features, use the `?` (zero_or_one) modifier:

```python
manager.add_resource(
    "application",
    scope="app",
    config={
        "desc": "Application with optional features",
        "requires": [
            "database.main",      # Required database
            "cache.redis?",       # Optional cache
            "logging.service?"    # Optional logging
        ],
        "provides": ["app.web"]
    }
)
```

### 2. Multiple Implementation Options

To allow different implementations of a capability, use the resource instance name:

```python
# Add alternative database options
manager.add_resource(
    "postgres",
    scope="app",
    config={
        "desc": "PostgreSQL database",
        "provides": ["database.postgres"]
    }
)

manager.add_resource(
    "mysql",
    scope="app",
    config={
        "desc": "MySQL database",
        "provides": ["database.mysql"]
    }
)

# Choose a specific implementation
manager.add_resource(
    "app_postgres",
    scope="app",
    config={
        "desc": "App using PostgreSQL",
        "requires": ["database.postgres"]
    }
)

# Or use remapping to choose at resolution time
resolver = DepBuilder(
    resources=manager,
    feature_names=["app.main"],
    remap_rules={"database": "mysql"}  # Choose MySQL implementation
)
```

### 3. Multiple Instances of the Same Kind

For services that can have multiple instances, use the `+` (one_or_many) modifier:

```python
# Define worker resources
manager.add_resource(
    "worker_fast",
    scope="app",
    config={
        "desc": "Fast worker for urgent tasks",
        "provides": ["worker.fast"],
        "vars": {"queue": "urgent", "threads": 10}
    }
)

manager.add_resource(
    "worker_slow",
    scope="app",
    config={
        "desc": "Slow worker for background tasks",
        "provides": ["worker.slow"],
        "vars": {"queue": "background", "threads": 2}
    }
)

# Require at least one worker
manager.add_resource(
    "job_scheduler",
    scope="app",
    config={
        "desc": "Job scheduler",
        "requires": ["worker.+"],  # Require one or more workers of any instance
        "provides": ["scheduler.jobs"]
    }
)
```

### 4. Feature Flags

You can implement feature flags by creating resources that represent features:

```python
# Define feature flags
features = {
    "feature_analytics": {
        "desc": "Analytics feature",
        "provides": ["feature.analytics"],
        "requires": ["database.main"]
    },
    "feature_notifications": {
        "desc": "Notifications feature",
        "provides": ["feature.notifications"],
        "requires": ["messaging.service"]
    },
    "feature_export": {
        "desc": "Data export feature",
        "provides": ["feature.export"],
        "requires": ["storage.blob"]
    }
}
manager.add_resources(features, scope="features")

# Create application that can use features
manager.add_resource(
    "application",
    scope="app",
    config={
        "desc": "Application with optional features",
        "requires": [
            "database.main",
            "feature.analytics?",
            "feature.notifications?",
            "feature.export?"
        ]
    }
)

# Enable specific features at resolution time
resolver = DepBuilder(
    resources=manager,
    feature_names=["application", "feature.analytics", "feature.export"]
)
```

## Advanced Integration Patterns

### 1. Resource Composition

You can build complex resources by composing simpler ones:

```python
# Define basic infrastructure resources
infra = {
    "network": {
        "desc": "Network infrastructure",
        "provides": ["network.vpc", "network.subnets"]
    },
    "storage": {
        "desc": "Storage services",
        "provides": ["storage.blob", "storage.file"]
    },
    "compute": {
        "desc": "Compute services",
        "requires": ["network.vpc"],
        "provides": ["compute.vm", "compute.container"]
    }
}
manager.add_resources(infra, scope="infrastructure")

# Define platform layer that builds on infrastructure
platform = {
    "database_service": {
        "desc": "Managed database service",
        "requires": ["compute.container", "storage.blob"],
        "provides": ["database.service"]
    },
    "message_queue": {
        "desc": "Message queue service",
        "requires": ["compute.container", "network.vpc"],
        "provides": ["messaging.queue"]
    },
    "auth_service": {
        "desc": "Authentication service",
        "requires": ["database.service"],
        "provides": ["auth.service"]
    }
}
manager.add_resources(platform, scope="platform")

# Define application layer that builds on platform
applications = {
    "web_portal": {
        "desc": "Web portal application",
        "requires": ["database.service", "auth.service"],
        "provides": ["app.portal"]
    },
    "mobile_backend": {
        "desc": "Mobile app backend",
        "requires": ["database.service", "auth.service", "messaging.queue"],
        "provides": ["app.mobile_api"]
    }
}
manager.add_resources(applications, scope="applications")
```

### 2. Environment-specific Configuration

You can manage environment-specific configurations using resource scopes:

```python
# Define base resources common to all environments
base_resources = {
    "database": {
        "desc": "Database service",
        "provides": ["database.main"],
        "vars": {"engine": "postgres"}
    },
    "api": {
        "desc": "API service",
        "requires": ["database.main"],
        "provides": ["api.rest"],
        "vars": {"port": 8080}
    }
}
manager.add_resources(base_resources, scope="base")

# Development environment overrides
dev_resources = {
    "database": {
        "desc": "Development database",
        "provides": ["database.main"],
        "vars": {"engine": "sqlite", "path": "/tmp/dev.db"}
    }
}
manager.add_resources(dev_resources, scope="development")

# Production environment overrides
prod_resources = {
    "database": {
        "desc": "Production database",
        "provides": ["database.main"],
        "vars": {
            "engine": "postgres", 
            "host": "db.prod.example.com",
            "replicas": 3
        }
    },
    "api": {
        "desc": "Production API service",
        "requires": ["database.main"],
        "provides": ["api.rest"],
        "vars": {
            "port": 80,
            "tls": True,
            "min_instances": 5
        }
    }
}
manager.add_resources(prod_resources, scope="production")

# Resolve for specific environment
env = "production"  # or "development"

# Create a new manager with only the resources for the specified environment
env_manager = ResourceManager()

# Add base resources first
for resource in manager.get_resources(scope="base"):
    env_manager.add_resource(
        resource.name,
        scope="app",
        config=resource
    )

# Override with environment-specific resources
for resource in manager.get_resources(scope=env):
    env_manager.add_resource(
        resource.name,
        scope="app",
        config=resource,
        force=True  # Force overwrite of base resources
    )

# Resolve dependencies for the environment
resolver = DepBuilder(
    resources=env_manager,
    feature_names=["api.rest"]
)
resolver.resolve()
```

## Integration with External Systems

You can extend the Resource Manager to integrate with external systems like Kubernetes, Docker, or cloud providers:

```python
import subprocess
import json

class KubernetesResource(Resource):
    """Resource that can be deployed to Kubernetes."""
    
    default_attrs = {
        "namespace": "default",
        "replicas": 1,
        "image": None,
        "ports": [],
        "env_vars": {}
    }
    
    def generate_manifest(self):
        """Generate Kubernetes manifest for this resource."""
        manifest = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": self.name,
                "namespace": self.namespace
            },
            "spec": {
                "replicas": self.replicas,
                "selector": {
                    "matchLabels": {
                        "app": self.name
                    }
                },
                "template": {
                    "metadata": {
                        "labels": {
                            "app": self.name
                        }
                    },
                    "spec": {
                        "containers": [{
                            "name": self.name,
                            "image": self.image,
                            "ports": [{"containerPort": p} for p in self.ports],
                            "env": [{"name": k, "value": v} for k, v in self.env_vars.items()]
                        }]
                    }
                }
            }
        }
        return manifest
    
    def deploy(self):
        """Deploy this resource to Kubernetes."""
        manifest = self.generate_manifest()
        manifest_json = json.dumps(manifest)
        
        # Use kubectl to apply the manifest
        cmd = ["kubectl", "apply", "-f", "-"]
        process = subprocess.Popen(
            cmd, 
            stdin=subprocess.PIPE, 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate(input=manifest_json.encode())
        
        if process.returncode != 0:
            raise Exception(f"Failed to deploy {self.name}: {stderr.decode()}")
        
        return stdout.decode()
```

## Next Steps

You now have a solid understanding of the Resource Manager library and its advanced usage patterns. For further exploration:

1. Implement a custom resolver for your specific needs
2. Integrate the Resource Manager with your existing systems
3. Explore the source code to understand the implementation details

Check out the complete code examples and reference documentation for more details.

For specific use cases not covered in this tutorial, consider creating a custom resolver or resource class that addresses your requirements. 