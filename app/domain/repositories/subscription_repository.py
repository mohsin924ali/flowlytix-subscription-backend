"""
Subscription Repository Interface

Abstract repository interfaces for subscription management.
Follows Instructions file standards for repository pattern and dependency inversion.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from uuid import UUID

from app.domain.entities.subscription import Subscription, Customer, Device


class ISubscriptionRepository(ABC):
    """
    Subscription repository interface.
    
    Defines the contract for subscription data access.
    Follows Instructions file standards for abstraction and dependency inversion.
    """
    
    @abstractmethod
    async def create(self, subscription: Subscription) -> Subscription:
        """
        Create a new subscription.
        
        Args:
            subscription: Subscription entity to create
            
        Returns:
            Created subscription with updated fields
        """
        pass
    
    @abstractmethod
    async def get_by_id(self, subscription_id: UUID) -> Optional[Subscription]:
        """
        Get subscription by ID.
        
        Args:
            subscription_id: Unique subscription identifier
            
        Returns:
            Subscription entity or None if not found
        """
        pass
    
    @abstractmethod
    async def get_by_license_key(self, license_key: str) -> Optional[Subscription]:
        """
        Get subscription by license key.
        
        Args:
            license_key: Unique license key
            
        Returns:
            Subscription entity or None if not found
        """
        pass
    
    @abstractmethod
    async def get_by_customer_id(self, customer_id: UUID) -> List[Subscription]:
        """
        Get all subscriptions for a customer.
        
        Args:
            customer_id: Customer identifier
            
        Returns:
            List of subscription entities
        """
        pass
    
    @abstractmethod
    async def update(self, subscription: Subscription) -> Subscription:
        """
        Update an existing subscription.
        
        Args:
            subscription: Subscription entity with updated data
            
        Returns:
            Updated subscription entity
        """
        pass
    
    @abstractmethod
    async def delete(self, subscription_id: UUID) -> bool:
        """
        Delete a subscription.
        
        Args:
            subscription_id: Subscription identifier
            
        Returns:
            True if deleted successfully, False if not found
        """
        pass
    
    @abstractmethod
    async def list_all(
        self,
        limit: int = 100,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Subscription]:
        """
        List subscriptions with pagination and filtering.
        
        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            filters: Optional filters (status, tier, etc.)
            
        Returns:
            List of subscription entities
        """
        pass
    
    @abstractmethod
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count subscriptions with optional filtering.
        
        Args:
            filters: Optional filters (status, tier, etc.)
            
        Returns:
            Total count of matching subscriptions
        """
        pass
    
    @abstractmethod
    async def get_expiring_soon(self, days: int = 7) -> List[Subscription]:
        """
        Get subscriptions expiring within specified days.
        
        Args:
            days: Number of days to look ahead
            
        Returns:
            List of expiring subscription entities
        """
        pass


class ICustomerRepository(ABC):
    """
    Customer repository interface.
    
    Defines the contract for customer data access.
    Follows Instructions file standards for abstraction.
    """
    
    @abstractmethod
    async def create(self, customer: Customer) -> Customer:
        """
        Create a new customer.
        
        Args:
            customer: Customer entity to create
            
        Returns:
            Created customer with updated fields
        """
        pass
    
    @abstractmethod
    async def get_by_id(self, customer_id: UUID) -> Optional[Customer]:
        """
        Get customer by ID.
        
        Args:
            customer_id: Unique customer identifier
            
        Returns:
            Customer entity or None if not found
        """
        pass
    
    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[Customer]:
        """
        Get customer by email address.
        
        Args:
            email: Customer email address
            
        Returns:
            Customer entity or None if not found
        """
        pass
    
    @abstractmethod
    async def update(self, customer: Customer) -> Customer:
        """
        Update an existing customer.
        
        Args:
            customer: Customer entity with updated data
            
        Returns:
            Updated customer entity
        """
        pass
    
    @abstractmethod
    async def delete(self, customer_id: UUID) -> bool:
        """
        Delete a customer.
        
        Args:
            customer_id: Customer identifier
            
        Returns:
            True if deleted successfully, False if not found
        """
        pass
    
    @abstractmethod
    async def list_all(
        self,
        limit: int = 100,
        offset: int = 0,
        search: Optional[str] = None
    ) -> List[Customer]:
        """
        List customers with pagination and search.
        
        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            search: Optional search term for name/email
            
        Returns:
            List of customer entities
        """
        pass
    
    @abstractmethod
    async def count(self, search: Optional[str] = None) -> int:
        """
        Count customers with optional search.
        
        Args:
            search: Optional search term for name/email
            
        Returns:
            Total count of matching customers
        """
        pass


class IDeviceRepository(ABC):
    """
    Device repository interface.
    
    Defines the contract for device data access.
    Follows Instructions file standards for abstraction.
    """
    
    @abstractmethod
    async def create(self, device: Device) -> Device:
        """
        Create a new device.
        
        Args:
            device: Device entity to create
            
        Returns:
            Created device with updated fields
        """
        pass
    
    @abstractmethod
    async def get_by_id(self, device_id: UUID) -> Optional[Device]:
        """
        Get device by ID.
        
        Args:
            device_id: Unique device identifier
            
        Returns:
            Device entity or None if not found
        """
        pass
    
    @abstractmethod
    async def get_by_device_id(self, device_id: str, subscription_id: UUID) -> Optional[Device]:
        """
        Get device by device ID and subscription.
        
        Args:
            device_id: Device identifier from client
            subscription_id: Subscription identifier
            
        Returns:
            Device entity or None if not found
        """
        pass
    
    @abstractmethod
    async def get_by_subscription_id(self, subscription_id: UUID) -> List[Device]:
        """
        Get all devices for a subscription.
        
        Args:
            subscription_id: Subscription identifier
            
        Returns:
            List of device entities
        """
        pass
    
    @abstractmethod
    async def update(self, device: Device) -> Device:
        """
        Update an existing device.
        
        Args:
            device: Device entity with updated data
            
        Returns:
            Updated device entity
        """
        pass
    
    @abstractmethod
    async def delete(self, device_id: UUID) -> bool:
        """
        Delete a device.
        
        Args:
            device_id: Device identifier
            
        Returns:
            True if deleted successfully, False if not found
        """
        pass
    
    @abstractmethod
    async def list_all(
        self,
        limit: int = 100,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Device]:
        """
        List devices with pagination and filtering.
        
        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            filters: Optional filters (active, subscription_id, etc.)
            
        Returns:
            List of device entities
        """
        pass
    
    @abstractmethod
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count devices with optional filtering.
        
        Args:
            filters: Optional filters (active, subscription_id, etc.)
            
        Returns:
            Total count of matching devices
        """
        pass
    
    @abstractmethod
    async def get_inactive_devices(self, days: int = 30) -> List[Device]:
        """
        Get devices that haven't been seen for specified days.
        
        Args:
            days: Number of days of inactivity
            
        Returns:
            List of inactive device entities
        """
        pass 