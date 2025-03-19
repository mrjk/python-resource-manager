# Visualizing Dependency Graphs

This tutorial explores how to visualize resource dependency graphs to better understand and debug complex configurations.

## Why Visualize Dependencies?

Visualizing dependency relationships helps to:

1. Understand the flow of dependencies in your system
2. Debug issues with resource dependencies and initialization order
3. Document and communicate system architecture
4. Identify potential bottlenecks or unnecessary dependencies

## Basic Visualization

The `DepBuilder` class includes a `gen_graph` method that generates a visual representation of the dependency graph:

```python
from resource_manager.resources import ResourceManager
from resource_manager.resolver import DepBuilder

# Create resources
manager = ResourceManager()
# ... add resources ...

# Resolve dependencies
resolver = DepBuilder(resources=manager, feature_names=["app.main"])
resolver.resolve()

# Generate a visualization
resolver.gen_graph("dependencies.png")
```

This will create a PNG image with:
- Nodes representing resources
- Directed edges representing dependencies
- Edge labels showing the rule that created each dependency

## Customizing the Graph

While the basic `gen_graph` method works well for simple graphs, you might want to customize the visualization for more complex systems. You can extend the method or create your own:

```python
import pydot
from resource_manager.resolver import DepBuilder

class CustomDepBuilder(DepBuilder):
    def gen_custom_graph(self, output_file="custom_graph.png"):
        """Generate a custom dependency graph visualization."""
        # Create a directed graph
        graph = pydot.Dot(
            "dependency_graph",
            graph_type="digraph",
            rankdir="LR",  # Left to right layout
            bgcolor="white"
        )
        
        # Add nodes for each resource
        for resource_name in self.dep_order:
            # Get the resource object
            resource = self.rmanager.get_resource(resource_name)
            
            # Customize node appearance based on resource properties
            shape = "box"
            color = "black"
            style = "filled"
            fillcolor = "white"
            
            # Different colors for different resource types/groups
            if hasattr(resource, "group"):
                if resource.group == "database":
                    fillcolor = "lightblue"
                elif resource.group == "application":
                    fillcolor = "lightgreen"
                elif resource.group == "network":
                    fillcolor = "lightyellow"
            
            # Create node with label showing resource attributes
            label = f"{resource_name}"
            if hasattr(resource, "desc") and resource.desc:
                label += f"\\n{resource.desc}"
                
            node = pydot.Node(
                resource_name,
                shape=shape,
                color=color,
                style=style,
                fillcolor=fillcolor,
                label=label
            )
            graph.add_node(node)
        
        # Add edges for dependencies
        for resource_name in self.dep_order:
            if resource_name in self.dep_tree:
                edges = self.dep_tree[resource_name]
                for edge in edges:
                    dependency_name = edge.provider.resource.name
                    label = edge.rule
                    
                    # Create edge with custom styling
                    edge_obj = pydot.Edge(
                        dependency_name,
                        resource_name,
                        label=label,
                        fontsize=10,
                        color="blue"
                    )
                    graph.add_edge(edge_obj)
        
        # Save the graph
        graph.write(output_file, format="png")
```

## Creating Hierarchical Graphs

For complex systems, you might want to group resources into clusters:

```python
def gen_clustered_graph(self, output_file="clustered_graph.png"):
    """Generate a graph with resources grouped into clusters by scope or group."""
    # Create main graph
    graph = pydot.Dot(
        "clustered_graph",
        graph_type="digraph",
        rankdir="TB",  # Top to bottom layout
        newrank=True
    )
    
    # Group resources by scope or group
    groups = {}
    for resource_name in self.dep_order:
        resource = self.rmanager.get_resource(resource_name)
        
        # Use group attribute if available, otherwise use scope
        group_key = getattr(resource, "group", resource.scope or "default")
        if group_key not in groups:
            groups[group_key] = []
        groups[group_key].append(resource)
    
    # Create clusters for each group
    for group_name, resources in groups.items():
        # Skip empty groups
        if not resources:
            continue
            
        # Create a cluster subgraph
        cluster = pydot.Cluster(
            f"cluster_{group_name}",
            label=group_name,
            style="filled",
            fillcolor="lightgray"
        )
        
        # Add nodes to the cluster
        for resource in resources:
            node = pydot.Node(
                resource.name,
                shape="box",
                style="filled",
                fillcolor="white",
                label=f"{resource.name}\n{getattr(resource, 'desc', '')}"
            )
            cluster.add_node(node)
        
        # Add the cluster to the main graph
        graph.add_subgraph(cluster)
    
    # Add edges for dependencies
    for resource_name in self.dep_order:
        if resource_name in self.dep_tree:
            edges = self.dep_tree[resource_name]
            for edge in edges:
                dependency_name = edge.provider.resource.name
                label = edge.rule
                
                # Create edge
                edge_obj = pydot.Edge(
                    dependency_name,
                    resource_name,
                    label=label
                )
                graph.add_edge(edge_obj)
    
    # Save the graph
    graph.write(output_file, format="png")
```

## Real-world Example

Let's create a visualization for a more complex application:

```python
from resource_manager.resources import ResourceManager
from resource_manager.resolver import DepBuilder

# Create a resource manager
manager = ResourceManager()

# Define resources for a web application stack
resources = {
    "postgres": {
        "desc": "PostgreSQL database",
        "provides": ["database.main", "database.metrics"],
        "group": "storage"
    },
    "redis": {
        "desc": "Redis cache",
        "provides": ["cache.main", "pubsub.events"],
        "group": "storage"
    },
    "backend": {
        "desc": "API backend service",
        "requires": ["database.main", "cache.main"],
        "provides": ["api.rest", "api.graphql"],
        "group": "application"
    },
    "frontend": {
        "desc": "React frontend",
        "requires": ["api.rest"],
        "provides": ["ui.web"],
        "group": "application"
    },
    "nginx": {
        "desc": "Nginx web server",
        "requires": ["ui.web", "api.graphql"],
        "provides": ["ingress.http"],
        "group": "network"
    },
    "certbot": {
        "desc": "Let's Encrypt certificate manager",
        "requires": ["ingress.http"],
        "provides": ["ssl.certificates"],
        "group": "security"
    }
}
manager.add_resources(resources, scope="production")

# Create and resolve dependencies
resolver = DepBuilder(
    resources=manager,
    feature_names=["ssl.certificates"],  # Start with the certificates
    debug=True
)
resolver.resolve()

# Generate a visualization
resolver.gen_graph("web_app_dependencies.png")

# Create a customized visualization (assuming we have the methods above)
if hasattr(resolver, "gen_custom_graph"):
    resolver.gen_custom_graph("web_app_custom.png")
if hasattr(resolver, "gen_clustered_graph"):
    resolver.gen_clustered_graph("web_app_clustered.png")
```

## Advanced Visualization with External Tools

For more advanced visualization, you can export the dependency data to other formats:

### Exporting to DOT Format

```python
def export_to_dot(self, output_file="dependencies.dot"):
    """Export dependency graph to DOT format for use with Graphviz."""
    graph = pydot.Dot(
        "dependency_graph",
        graph_type="digraph",
        rankdir="LR"
    )
    
    # Add nodes and edges (similar to previous examples)
    # ...
    
    # Write to DOT file
    with open(output_file, "w") as f:
        f.write(graph.to_string())
    
    print(f"Exported dependency graph to {output_file}")
    print("You can visualize this file with Graphviz tools like:")
    print(f"  dot -Tpng {output_file} -o output.png")
    print(f"  dot -Tsvg {output_file} -o output.svg")
```

### Exporting to JSON

```python
import json

def export_to_json(self, output_file="dependencies.json"):
    """Export dependency graph to JSON format."""
    data = {
        "resources": {},
        "dependencies": []
    }
    
    # Add resource data
    for resource_name in self.dep_order:
        resource = self.rmanager.get_resource(resource_name)
        data["resources"][resource_name] = {
            "name": resource.name,
            "scope": resource.scope,
            "desc": getattr(resource, "desc", None),
            "group": getattr(resource, "group", None),
            "provides": [p.rule for p in resource.provides],
            "requires": [r.rule for r in resource.requires]
        }
    
    # Add dependency data
    for resource_name, edges in self.dep_tree.items():
        for edge in edges:
            data["dependencies"].append({
                "source": edge.provider.resource.name,
                "target": resource_name,
                "rule": edge.rule
            })
    
    # Write to JSON file
    with open(output_file, "w") as f:
        json.dump(data, f, indent=2)
    
    print(f"Exported dependency data to {output_file}")
```

This JSON format can be used with visualization libraries like D3.js to create interactive visualizations.

## Tips for Effective Visualizations

1. **Group related resources**: Use clusters or color coding to group related resources
2. **Use clear labels**: Make sure node and edge labels are informative but not too verbose
3. **Adjust layout**: Experiment with different layout directions (LR, RL, TB, BT)
4. **Highlight critical paths**: Use color or thicker edges for critical dependency paths
5. **Filter complexity**: For large systems, consider generating multiple views that focus on specific subsystems

## Next Steps

Now that you can visualize and understand dependency relationships, let's move on to [advanced usage patterns](06_advanced_usage.md) to explore more complex scenarios and customization options. 