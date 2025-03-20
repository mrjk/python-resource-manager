import pytest

from resource_manager.exceptions import (
    ResourceConfigError,
    ResourceDuplicateError,
    ResourceImplementationError,
    ResourceLinkError,
    ResourceManagerError,
    ResourceResolutionError,
    ResourceTypeError,
)
from resource_manager.links import (
    ResourceLink,
    ResourceProviderLink,
    ResourceRequireLink,
)
from resource_manager.resolver import DepBuilder
from resource_manager.resources import Resource, ResourceManager


class TestResourceExceptions:
    """Tests for exceptions raised by the Resource class."""
    
    def test_resource_type_error(self):
        """Test that ResourceTypeError is raised for invalid types."""
        # Invalid name type
        with pytest.raises(AssertionError):
            Resource(123)  # Name should be a string
            
        # Invalid provides type
        with pytest.raises(AssertionError):
            Resource("test", provides="not_a_list")  # Provides should be a list
            
        # Invalid requires type
        with pytest.raises(AssertionError):
            Resource("test", requires="not_a_list")  # Requires should be a list


class TestResourceManagerExceptions:
    """Tests for exceptions raised by the ResourceManager class."""
    
    def test_add_resource_duplicate_error(self):
        """Test that adding a duplicate resource raises ResourceDuplicateError."""
        manager = ResourceManager()
        
        # Add a resource
        manager.add_resource("test", config={})
        
        # Try to add it again
        with pytest.raises(ResourceDuplicateError):
            manager.add_resource("test", config={})
    
    def test_add_resource_type_error(self):
        """Test that adding a resource with invalid types raises ResourceTypeError."""
        manager = ResourceManager()
        
        # Invalid resource name
        with pytest.raises(ResourceTypeError):
            manager.add_resource(123)
            
        # Invalid config type
        with pytest.raises(ResourceTypeError):
            manager.add_resource("test", config="not_a_dict_or_resource")
    
    def test_add_resources_type_error(self):
        """Test that adding resources with invalid types raises ResourceTypeError."""
        manager = ResourceManager()
        
        # Invalid resources type
        with pytest.raises(ResourceTypeError):
            manager.add_resources("not_a_dict")
            
        # Invalid resource name in dict
        with pytest.raises(ResourceTypeError):
            manager.add_resources({123: {}})
            
        # Invalid resource config in dict
        with pytest.raises(ResourceTypeError):
            manager.add_resources({"test": "not_a_dict_or_resource"})
    
    def test_get_resource_key_error(self):
        """Test that getting a non-existent resource raises KeyError."""
        manager = ResourceManager()
        
        with pytest.raises(KeyError):
            manager.get_resource("non_existent")


class TestLinkExceptions:
    """Tests for exceptions raised by the ResourceLink classes."""
    
    def test_resource_link_config_error(self):
        """Test that invalid link configurations raise ResourceConfigError."""
        # Missing kind
        with pytest.raises(ResourceConfigError):
            ResourceLink({"instance": "instance1"})
            
        # Invalid string format
        with pytest.raises(ResourceConfigError):
            ResourceLink("invalid.format.with.too.many.parts")
    
    def test_resource_link_type_error(self):
        """Test that invalid link types raise ResourceTypeError."""
        # Invalid config type
        with pytest.raises(ResourceTypeError):
            ResourceLink(123)  # Config should be dict or string
    
    def test_require_link_validation_error(self):
        """Test that requirement validation errors raise ResourceLinkError."""
        # Create a requirement with "!" modifier (exactly one required)
        requirement = ResourceRequireLink("test.kind!")
        
        # Empty provider list
        with pytest.raises(ResourceLinkError):
            requirement.match_provider([])
            
        # Create a requirement with "+" modifier (at least one required)
        requirement = ResourceRequireLink("test.kind+")
        
        # Empty provider list
        with pytest.raises(ResourceLinkError):
            requirement.match_provider([])


class TestResolverExceptions:
    """Tests for exceptions raised by the DepBuilder class."""
    
    def test_resolver_already_resolved_error(self):
        """Test that resolving twice raises ResourceResolutionError."""
        resolver = DepBuilder()
        resolver.resolve()
        
        with pytest.raises(ResourceResolutionError):
            resolver.resolve()
    
    def test_resolver_unresolvable_requirements_error(self):
        """Test that unresolvable requirements raise an appropriate error."""
        # Create a resource manager with unresolvable dependencies
        manager = ResourceManager()
        
        # App requires database, but database is not provided
        manager.add_resource(
            "app",
            config={
                "requires": ["database.main"]
            }
        )
        
        # Create resolver requesting the app
        resolver = DepBuilder(
            resources=manager,
            feature_names=["app"]
        )
        
        # Resolution should fail
        with pytest.raises(ResourceLinkError) as excinfo:
            resolver.resolve()
        
        # Verify the error is related to unresolved dependency
        error_str = str(excinfo.value)
        assert "exactly one provider" in error_str
    
    def test_resolver_missing_feature_error(self):
        """Test that requesting a non-existent feature raises an appropriate error."""
        # Create a resource manager
        manager = ResourceManager()
        
        # Add a resource
        manager.add_resource(
            "app",
            config={
                "provides": ["app.feature"]
            }
        )
        
        # Create resolver requesting a non-existent feature
        resolver = DepBuilder(
            resources=manager, 
            feature_names=["missing.feature"]
        )
        
        # Resolution should fail
        with pytest.raises(ResourceLinkError) as excinfo:
            resolver.resolve()
        
        # Verify the error is related to missing feature
        error_str = str(excinfo.value)
        assert "exactly one provider" in error_str


class TestExceptionHierarchy:
    """Tests for the exception hierarchy."""
    
    def test_exception_inheritance(self):
        """Test that all exceptions inherit from ResourceManagerError."""
        assert issubclass(ResourceConfigError, ResourceManagerError)
        assert issubclass(ResourceTypeError, ResourceConfigError)
        assert issubclass(ResourceLinkError, ResourceManagerError)
        assert issubclass(ResourceDuplicateError, ResourceManagerError)
        assert issubclass(ResourceResolutionError, ResourceManagerError)
        assert issubclass(ResourceImplementationError, ResourceManagerError) 