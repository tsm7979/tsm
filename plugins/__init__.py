"""
Plugin Architecture
===================

Extensible plugin system for custom functionality.
"""

from typing import Dict, Any, Optional, List, Type, Callable
from dataclasses import dataclass, field
from datetime import datetime
from abc import ABC, abstractmethod
from enum import Enum
import importlib
import inspect
import logging

logger = logging.getLogger(__name__)


class PluginType(str, Enum):
    """Plugin types."""
    PREPROCESSOR = "preprocessor"  # Pre-process input
    POSTPROCESSOR = "postprocessor"  # Post-process output
    MODEL_PROVIDER = "model_provider"  # Custom model provider
    TOOL = "tool"  # Custom tool
    ROUTER = "router"  # Custom routing logic
    VERIFIER = "verifier"  # Custom verification rule
    CACHE = "cache"  # Custom cache backend
    MONITOR = "monitor"  # Custom monitoring


class PluginStatus(str, Enum):
    """Plugin status."""
    LOADED = "loaded"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


@dataclass
class PluginMetadata:
    """Plugin metadata."""
    name: str
    version: str
    author: str
    description: str
    plugin_type: PluginType
    dependencies: List[str] = field(default_factory=list)
    config_schema: Optional[Dict[str, Any]] = None


class Plugin(ABC):
    """
    Base plugin class.

    All plugins must inherit from this class and implement required methods.
    """

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        pass

    @abstractmethod
    async def initialize(self, config: Dict[str, Any]):
        """
        Initialize plugin with configuration.

        Args:
            config: Plugin configuration
        """
        pass

    @abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        """
        Execute plugin functionality.

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Plugin execution result
        """
        pass

    async def shutdown(self):
        """Shutdown plugin (cleanup resources)."""
        pass

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate plugin configuration.

        Args:
            config: Configuration to validate

        Returns:
            True if valid
        """
        return True


class PreprocessorPlugin(Plugin):
    """Base class for preprocessor plugins."""

    @abstractmethod
    async def preprocess(self, input_text: str, context: Dict[str, Any]) -> str:
        """
        Preprocess input text.

        Args:
            input_text: Input text
            context: Request context

        Returns:
            Preprocessed text
        """
        pass

    async def execute(self, *args, **kwargs) -> Any:
        """Execute preprocessor."""
        return await self.preprocess(*args, **kwargs)


class PostprocessorPlugin(Plugin):
    """Base class for postprocessor plugins."""

    @abstractmethod
    async def postprocess(
        self,
        output_text: str,
        input_text: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Postprocess output text.

        Args:
            output_text: Model output
            input_text: Original input
            context: Request context

        Returns:
            Postprocessed text
        """
        pass

    async def execute(self, *args, **kwargs) -> Any:
        """Execute postprocessor."""
        return await self.postprocess(*args, **kwargs)


class ToolPlugin(Plugin):
    """Base class for tool plugins."""

    @property
    @abstractmethod
    def tool_name(self) -> str:
        """Tool name."""
        pass

    @property
    @abstractmethod
    def tool_description(self) -> str:
        """Tool description."""
        pass

    @property
    @abstractmethod
    def parameters_schema(self) -> Dict[str, Any]:
        """Parameters schema (JSON schema)."""
        pass

    @abstractmethod
    async def run(self, **parameters) -> Any:
        """
        Run tool with parameters.

        Args:
            **parameters: Tool parameters

        Returns:
            Tool result
        """
        pass

    async def execute(self, *args, **kwargs) -> Any:
        """Execute tool."""
        return await self.run(**kwargs)


@dataclass
class LoadedPlugin:
    """Loaded plugin instance."""
    plugin_id: str
    instance: Plugin
    metadata: PluginMetadata
    status: PluginStatus
    config: Dict[str, Any]
    loaded_at: datetime = field(default_factory=datetime.utcnow)
    error: Optional[str] = None


class PluginManager:
    """
    Plugin manager for loading and managing plugins.

    Features:
    - Dynamic plugin loading
    - Dependency resolution
    - Lifecycle management
    - Error handling
    """

    def __init__(self):
        """Initialize plugin manager."""
        self.plugins: Dict[str, LoadedPlugin] = {}
        self.plugin_types: Dict[PluginType, List[str]] = {
            ptype: [] for ptype in PluginType
        }

        logger.info("PluginManager initialized")

    def register_plugin(
        self,
        plugin_class: Type[Plugin],
        config: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Register a plugin class.

        Args:
            plugin_class: Plugin class (must inherit from Plugin)
            config: Optional plugin configuration

        Returns:
            Plugin ID

        Raises:
            ValueError: If plugin invalid
        """
        # Validate plugin class
        if not issubclass(plugin_class, Plugin):
            raise ValueError("Plugin must inherit from Plugin base class")

        # Create instance
        instance = plugin_class()

        # Get metadata
        metadata = instance.metadata

        # Validate config
        config = config or {}
        if not instance.validate_config(config):
            raise ValueError("Invalid plugin configuration")

        # Generate plugin ID
        plugin_id = f"{metadata.name}:{metadata.version}"

        # Check if already loaded
        if plugin_id in self.plugins:
            raise ValueError(f"Plugin already loaded: {plugin_id}")

        # Create loaded plugin
        loaded = LoadedPlugin(
            plugin_id=plugin_id,
            instance=instance,
            metadata=metadata,
            status=PluginStatus.LOADED,
            config=config
        )

        # Store plugin
        self.plugins[plugin_id] = loaded
        self.plugin_types[metadata.plugin_type].append(plugin_id)

        logger.info(
            f"Registered plugin: {plugin_id} "
            f"(type={metadata.plugin_type.value})"
        )

        return plugin_id

    async def initialize_plugin(self, plugin_id: str):
        """
        Initialize a plugin.

        Args:
            plugin_id: Plugin ID
        """
        if plugin_id not in self.plugins:
            raise ValueError(f"Plugin not found: {plugin_id}")

        loaded = self.plugins[plugin_id]

        try:
            # Initialize plugin
            await loaded.instance.initialize(loaded.config)

            # Mark as active
            loaded.status = PluginStatus.ACTIVE

            logger.info(f"Initialized plugin: {plugin_id}")

        except Exception as e:
            loaded.status = PluginStatus.ERROR
            loaded.error = str(e)

            logger.error(
                f"Failed to initialize plugin {plugin_id}: {e}",
                exc_info=True
            )
            raise

    async def initialize_all(self):
        """Initialize all loaded plugins."""
        for plugin_id in self.plugins:
            try:
                await self.initialize_plugin(plugin_id)
            except Exception as e:
                logger.error(f"Failed to initialize {plugin_id}: {e}")

    def unload_plugin(self, plugin_id: str):
        """
        Unload a plugin.

        Args:
            plugin_id: Plugin ID
        """
        if plugin_id not in self.plugins:
            return

        loaded = self.plugins[plugin_id]

        # Remove from type index
        self.plugin_types[loaded.metadata.plugin_type].remove(plugin_id)

        # Remove plugin
        del self.plugins[plugin_id]

        logger.info(f"Unloaded plugin: {plugin_id}")

    async def shutdown_plugin(self, plugin_id: str):
        """
        Shutdown a plugin.

        Args:
            plugin_id: Plugin ID
        """
        if plugin_id not in self.plugins:
            return

        loaded = self.plugins[plugin_id]

        try:
            await loaded.instance.shutdown()
            loaded.status = PluginStatus.INACTIVE

            logger.info(f"Shutdown plugin: {plugin_id}")

        except Exception as e:
            logger.error(f"Error shutting down plugin {plugin_id}: {e}")

    async def shutdown_all(self):
        """Shutdown all plugins."""
        for plugin_id in list(self.plugins.keys()):
            await self.shutdown_plugin(plugin_id)

    def get_plugin(self, plugin_id: str) -> Optional[LoadedPlugin]:
        """Get plugin by ID."""
        return self.plugins.get(plugin_id)

    def get_plugins_by_type(self, plugin_type: PluginType) -> List[LoadedPlugin]:
        """Get all plugins of a specific type."""
        plugin_ids = self.plugin_types[plugin_type]
        return [self.plugins[pid] for pid in plugin_ids]

    async def execute_plugin(
        self,
        plugin_id: str,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute a plugin.

        Args:
            plugin_id: Plugin ID
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Plugin execution result
        """
        if plugin_id not in self.plugins:
            raise ValueError(f"Plugin not found: {plugin_id}")

        loaded = self.plugins[plugin_id]

        if loaded.status != PluginStatus.ACTIVE:
            raise RuntimeError(f"Plugin not active: {plugin_id}")

        try:
            result = await loaded.instance.execute(*args, **kwargs)
            return result

        except Exception as e:
            logger.error(
                f"Plugin execution error ({plugin_id}): {e}",
                exc_info=True
            )
            raise

    async def execute_preprocessors(
        self,
        input_text: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Execute all preprocessor plugins in sequence.

        Args:
            input_text: Input text
            context: Request context

        Returns:
            Preprocessed text
        """
        text = input_text

        for plugin_id in self.plugin_types[PluginType.PREPROCESSOR]:
            loaded = self.plugins[plugin_id]

            if loaded.status != PluginStatus.ACTIVE:
                continue

            try:
                text = await loaded.instance.preprocess(text, context)
            except Exception as e:
                logger.error(
                    f"Preprocessor error ({plugin_id}): {e}",
                    exc_info=True
                )

        return text

    async def execute_postprocessors(
        self,
        output_text: str,
        input_text: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Execute all postprocessor plugins in sequence.

        Args:
            output_text: Model output
            input_text: Original input
            context: Request context

        Returns:
            Postprocessed text
        """
        text = output_text

        for plugin_id in self.plugin_types[PluginType.POSTPROCESSOR]:
            loaded = self.plugins[plugin_id]

            if loaded.status != PluginStatus.ACTIVE:
                continue

            try:
                text = await loaded.instance.postprocess(text, input_text, context)
            except Exception as e:
                logger.error(
                    f"Postprocessor error ({plugin_id}): {e}",
                    exc_info=True
                )

        return text

    def get_stats(self) -> Dict[str, Any]:
        """Get plugin statistics."""
        stats = {
            "total": len(self.plugins),
            "by_status": {
                status.value: sum(
                    1 for p in self.plugins.values()
                    if p.status == status
                )
                for status in PluginStatus
            },
            "by_type": {
                ptype.value: len(plugin_ids)
                for ptype, plugin_ids in self.plugin_types.items()
            }
        }

        return stats


class PluginHook:
    """
    Plugin hook for attaching custom logic to specific points.

    Similar to WordPress hooks/filters.
    """

    def __init__(self):
        """Initialize hook system."""
        self.hooks: Dict[str, List[Callable]] = {}

    def register(self, hook_name: str, callback: Callable, priority: int = 10):
        """
        Register a hook callback.

        Args:
            hook_name: Hook name
            callback: Callback function
            priority: Priority (lower = earlier)
        """
        if hook_name not in self.hooks:
            self.hooks[hook_name] = []

        self.hooks[hook_name].append((priority, callback))

        # Sort by priority
        self.hooks[hook_name].sort(key=lambda x: x[0])

        logger.debug(f"Registered hook: {hook_name} (priority={priority})")

    async def apply(self, hook_name: str, value: Any, *args, **kwargs) -> Any:
        """
        Apply hooks to a value.

        Args:
            hook_name: Hook name
            value: Value to filter
            *args: Additional arguments
            **kwargs: Additional keyword arguments

        Returns:
            Filtered value
        """
        if hook_name not in self.hooks:
            return value

        result = value

        for priority, callback in self.hooks[hook_name]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    result = await callback(result, *args, **kwargs)
                else:
                    result = callback(result, *args, **kwargs)
            except Exception as e:
                logger.error(
                    f"Hook error ({hook_name}): {e}",
                    exc_info=True
                )

        return result


# Fix missing import
import asyncio

# Global plugin manager
plugin_manager = PluginManager()

# Global hook system
hooks = PluginHook()
