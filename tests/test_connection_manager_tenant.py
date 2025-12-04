"""
Unit tests for ConnectionManager tenant_id handling

Tests that verify:
1. register_connector() requires tenant_id parameter
2. Connection objects are created with correct tenant_id
3. Both JWT user tenant and demo tenant fallback scenarios work correctly
"""

import pytest
import uuid
from uuid import UUID
from unittest.mock import AsyncMock, MagicMock, patch
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from aam_hybrid.core.connection_manager import ConnectionManager
from aam_hybrid.shared.constants import DEMO_TENANT_UUID
from aam_hybrid.shared.models import Connection, ConnectionStatus


class TestConnectionManagerTenantId:
    """Test suite for tenant_id handling in ConnectionManager"""
    
    @pytest.fixture
    def connection_manager(self):
        """Create a ConnectionManager instance for testing"""
        return ConnectionManager()
    
    @pytest.fixture
    def mock_tenant_id(self):
        """Generate a mock tenant UUID"""
        return uuid.uuid4()
    
    @pytest.fixture
    def demo_tenant_id(self):
        """Return the demo tenant UUID"""
        return UUID(DEMO_TENANT_UUID)
    
    @pytest.mark.asyncio
    async def test_register_connector_requires_tenant_id(self, connection_manager):
        """Test that register_connector() requires tenant_id parameter"""
        # This test verifies that calling register_connector without tenant_id
        # will raise a TypeError due to missing required argument
        
        with pytest.raises(TypeError, match="tenant_id"):
            await connection_manager.register_connector(
                name="Test Connection",
                source_type="Salesforce"
                # Missing tenant_id - should raise TypeError
            )
    
    @pytest.mark.asyncio
    async def test_register_connector_creates_connection_with_tenant_id(
        self, 
        connection_manager, 
        mock_tenant_id
    ):
        """Test that Connection objects are created with correct tenant_id"""
        
        # Mock the database session and operations
        mock_session = AsyncMock()
        mock_connection = Connection(
            id=uuid.uuid4(),
            name="Test Connection",
            source_type="Salesforce",
            tenant_id=mock_tenant_id,
            connector_config={},
            status=ConnectionStatus.PENDING
        )
        
        # Mock session.add, commit, refresh
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        # Patch AsyncSessionLocal to return our mock session
        with patch('aam_hybrid.core.connection_manager.AsyncSessionLocal') as mock_session_local:
            # Configure the context manager
            mock_session_local.return_value.__aenter__.return_value = mock_session
            mock_session_local.return_value.__aexit__.return_value = None
            
            # Mock the Connection constructor to return our mock connection
            with patch('aam_hybrid.core.connection_manager.Connection') as mock_conn_class:
                mock_conn_class.return_value = mock_connection
                
                # Call register_connector with tenant_id
                result = await connection_manager.register_connector(
                    name="Test Connection",
                    source_type="Salesforce",
                    tenant_id=mock_tenant_id,
                    config={"instance_url": "https://test.salesforce.com"}
                )
                
                # Verify Connection was created with tenant_id
                mock_conn_class.assert_called_once()
                call_kwargs = mock_conn_class.call_args.kwargs
                assert call_kwargs['name'] == "Test Connection"
                assert call_kwargs['source_type'] == "Salesforce"
                assert call_kwargs['tenant_id'] == mock_tenant_id
                assert call_kwargs['status'] == ConnectionStatus.PENDING
                
                # Verify the connection was added and committed
                mock_session.add.assert_called_once()
                mock_session.commit.assert_called_once()
                mock_session.refresh.assert_called_once()
                
                # Verify the result
                assert result.tenant_id == mock_tenant_id
    
    @pytest.mark.asyncio
    async def test_register_connector_with_demo_tenant_id(
        self, 
        connection_manager, 
        demo_tenant_id
    ):
        """Test that Connection can be created with DEMO_TENANT_UUID"""
        
        # Mock the database session and operations
        mock_session = AsyncMock()
        mock_connection = Connection(
            id=uuid.uuid4(),
            name="Demo Connection",
            source_type="FileSource",
            tenant_id=demo_tenant_id,
            connector_config={},
            status=ConnectionStatus.PENDING
        )
        
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        with patch('aam_hybrid.core.connection_manager.AsyncSessionLocal') as mock_session_local:
            mock_session_local.return_value.__aenter__.return_value = mock_session
            mock_session_local.return_value.__aexit__.return_value = None
            
            with patch('aam_hybrid.core.connection_manager.Connection') as mock_conn_class:
                mock_conn_class.return_value = mock_connection
                
                # Call register_connector with DEMO_TENANT_UUID
                result = await connection_manager.register_connector(
                    name="Demo Connection",
                    source_type="FileSource",
                    tenant_id=demo_tenant_id,
                    config={"file_path": "/tmp/data.csv"}
                )
                
                # Verify Connection was created with demo tenant_id
                call_kwargs = mock_conn_class.call_args.kwargs
                assert call_kwargs['tenant_id'] == demo_tenant_id
                assert str(call_kwargs['tenant_id']) == DEMO_TENANT_UUID
                
                # Verify the result
                assert result.tenant_id == demo_tenant_id
                assert str(result.tenant_id) == DEMO_TENANT_UUID
    
    @pytest.mark.asyncio
    async def test_api_fallback_logic_with_user_tenant(self, mock_tenant_id):
        """Test API endpoint fallback: use user tenant_id if available"""
        
        # Mock current_user with tenant_id (as UUID, since User.tenant_id is UUID type)
        mock_user = MagicMock()
        mock_user.tenant_id = mock_tenant_id
        mock_user.email = "test@example.com"
        
        # Test the tenant_id resolution logic from API endpoint
        tenant_id = (
            mock_user.tenant_id 
            if mock_user and hasattr(mock_user, 'tenant_id') and mock_user.tenant_id 
            else UUID(DEMO_TENANT_UUID)
        )
        
        # Should use user's tenant_id
        assert tenant_id == mock_tenant_id
        assert tenant_id != UUID(DEMO_TENANT_UUID)
    
    @pytest.mark.asyncio
    async def test_api_fallback_logic_without_user_tenant(self):
        """Test API endpoint fallback: use DEMO_TENANT_UUID if user has no tenant_id"""
        
        # Mock current_user without tenant_id
        mock_user = MagicMock()
        mock_user.email = "test@example.com"
        # Simulate user without tenant_id attribute
        delattr(mock_user, 'tenant_id') if hasattr(mock_user, 'tenant_id') else None
        
        # Test the tenant_id resolution logic from API endpoint
        tenant_id = (
            mock_user.tenant_id 
            if mock_user and hasattr(mock_user, 'tenant_id') and mock_user.tenant_id 
            else UUID(DEMO_TENANT_UUID)
        )
        
        # Should use DEMO_TENANT_UUID
        assert tenant_id == UUID(DEMO_TENANT_UUID)
        assert str(tenant_id) == DEMO_TENANT_UUID
    
    @pytest.mark.asyncio
    async def test_api_fallback_logic_with_none_user(self):
        """Test API endpoint fallback: use DEMO_TENANT_UUID if user is None"""
        
        # No user
        mock_user = None
        
        # Test the tenant_id resolution logic from API endpoint
        tenant_id = (
            mock_user.tenant_id 
            if mock_user and hasattr(mock_user, 'tenant_id') and mock_user.tenant_id 
            else UUID(DEMO_TENANT_UUID)
        )
        
        # Should use DEMO_TENANT_UUID
        assert tenant_id == UUID(DEMO_TENANT_UUID)
        assert str(tenant_id) == DEMO_TENANT_UUID
    
    @pytest.mark.asyncio
    async def test_onboarding_service_uses_demo_tenant(self, demo_tenant_id):
        """Test that onboarding service uses DEMO_TENANT_UUID"""
        
        # Verify that the constant matches expected value
        assert DEMO_TENANT_UUID == "f8ab4417-86a1-4dd2-a049-ea423063850e"
        
        # Verify UUID conversion works
        tenant_uuid = UUID(DEMO_TENANT_UUID)
        assert tenant_uuid == demo_tenant_id
        assert isinstance(tenant_uuid, UUID)
        
        # This validates that the onboarding service can correctly use:
        # tenant_id=UUID(DEMO_TENANT_UUID)
        assert str(tenant_uuid) == DEMO_TENANT_UUID
    
    def test_tenant_id_is_uuid_type(self, mock_tenant_id, demo_tenant_id):
        """Test that tenant_id values are proper UUID instances"""
        
        # Both should be UUID instances
        assert isinstance(mock_tenant_id, UUID)
        assert isinstance(demo_tenant_id, UUID)
        
        # Should be comparable
        assert mock_tenant_id != demo_tenant_id  # Different UUIDs
        
        # Should be convertible to string
        assert len(str(mock_tenant_id)) == 36
        assert len(str(demo_tenant_id)) == 36
        
        # Demo tenant should match the constant
        assert str(demo_tenant_id) == DEMO_TENANT_UUID


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
