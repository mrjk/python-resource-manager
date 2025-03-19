import pytest
from resource_manager.resources import Resource, ResourceManager
from resource_manager.exceptions import ResourceDuplicateError, ResourceTypeError


class TestResource:
    """Unit tests for the Resource class."""

    def test_resource_initialization(self):
        """Test that a resource can be properly initialized."""
        resource = Resource(
            "test", 
            scope="test_scope",
            provides=[{"kind": "test.provider"}],
            requires=[{"kind": "test.requirement"}],
            custom_attr="custom_value"
        )
        
        assert resource.name == "test"
        assert resource.scope == "test_scope"
        assert len(resource.provides) == 1
        assert len(resource.requires) == 1
        assert resource.custom_attr == "custom_value"
        
    def test_resource_copy(self):
        """Test that a resource can be copied properly."""
        original = Resource(
            "original", 
            scope="test",
            provides=[{"kind": "test.provider"}],
            requires=[{"kind": "test.requirement"}],
            custom_attr="custom_value"
        )
        
        copy = original.copy()
        
        # Verify copied resource has the same attributes
        assert copy.name == original.name
        assert copy.scope == original.scope
        assert len(copy.provides) == len(original.provides)
        assert len(copy.requires) == len(original.requires)
        assert copy.custom_attr == original.custom_attr
        
        # Verify it's a different object
        assert copy is not original
        
    def test_resource_representation(self):
        """Test the string representation of a resource."""
        resource = Resource("test", scope="test_scope")
        assert str(resource) == "Resource(test, test_scope)"
        

class TestResourceManager:
    """Unit tests for the ResourceManager class."""
    
    def test_add_resource(self, empty_resource_manager):
        """Test adding a resource to a manager."""
        manager = empty_resource_manager
        
        # Add a resource
        manager.add_resource(
            "test", 
            scope="test_scope",
            config={
                "provides": ["test.capability"],
                "requires": ["test.dependency"]
            }
        )
        
        # Verify resource was added
        assert "test" in manager.catalog
        resource = manager.get_resource("test")
        assert resource.name == "test"
        assert resource.scope == "test_scope"
        
    def test_add_resource_from_instance(self, empty_resource_manager, basic_resource):
        """Test adding a resource instance to a manager."""
        manager = empty_resource_manager
        
        # Add a resource instance
        manager.add_resource("new_resource", config=basic_resource)
        
        # Verify resource was added with new name
        assert "new_resource" in manager.catalog
        resource = manager.get_resource("new_resource")
        assert resource.name == "new_resource"
        assert resource.scope == "test"  # From basic_resource
        
    def test_add_resource_duplicate_error(self, empty_resource_manager):
        """Test that adding a duplicate resource raises an error."""
        manager = empty_resource_manager
        
        # Add resource first time
        manager.add_resource("test", config={})
        
        # Try to add it again
        with pytest.raises(ResourceDuplicateError):
            manager.add_resource("test", config={})
            
        # It should work with force=True
        manager.add_resource("test", config={}, force=True)
        
    def test_add_resources(self, empty_resource_manager, basic_resources_dict):
        """Test adding multiple resources at once."""
        manager = empty_resource_manager
        
        # Add multiple resources
        manager.add_resources(basic_resources_dict, scope="test_scope")
        
        # Verify all resources were added
        for name in basic_resources_dict:
            assert name in manager.catalog
            assert manager.get_resource(name).scope == "test_scope"
            
    def test_get_resource(self, populated_resource_manager):
        """Test retrieving a resource by name."""
        manager = populated_resource_manager
        
        # Get existing resource
        resource = manager.get_resource("resource1")
        assert resource.name == "resource1"
        
        # Get non-existent resource
        with pytest.raises(KeyError):
            manager.get_resource("non_existent")
            
    def test_get_resources(self, populated_resource_manager):
        """Test retrieving all resources or filtered by scope."""
        manager = populated_resource_manager
        
        # Add a resource with different scope
        manager.add_resource("scoped_resource", scope="different_scope", config={})
        
        # Get all resources
        all_resources = manager.get_resources()
        assert isinstance(all_resources, dict)
        assert len(all_resources) == 4  # 3 from fixture + 1 we added
        
        # Get resources by scope
        scoped_resources = manager.get_resources(scope="different_scope")
        assert isinstance(scoped_resources, list)
        assert len(scoped_resources) == 1
        
    def test_dump_catalog(self, populated_resource_manager):
        """Test dumping the entire catalog."""
        manager = populated_resource_manager
        catalog = manager.dump_catalog()
        
        # Verify it's a copy, not a reference
        assert catalog is not manager.catalog
        assert len(catalog) == len(manager.catalog)
        
    def test_iteration(self, populated_resource_manager):
        """Test that the manager is iterable."""
        manager = populated_resource_manager
        resources = list(manager)
        
        assert len(resources) == len(manager.catalog)
        
    def test_copy(self, populated_resource_manager):
        """Test copying the resource manager."""
        original = populated_resource_manager
        copy = original.copy()
        
        # Verify it's a new object with the same resources
        assert copy is not original
        assert len(copy.catalog) == len(original.catalog)
        
        # Modifications to the copy shouldn't affect the original
        copy.add_resource("new_resource", config={})
        assert "new_resource" in copy.catalog
        assert "new_resource" not in original.catalog 