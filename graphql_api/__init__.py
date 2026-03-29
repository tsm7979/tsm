"""
TSM GraphQL API
===============

Modern GraphQL API for flexible querying and mutations.

Features:
- Type-safe schema
- Query batching
- Field-level permissions
- DataLoader for N+1 prevention
- Subscription support
- Query complexity analysis
"""

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio
import logging

logger = logging.getLogger(__name__)


class GraphQLType(str, Enum):
    """GraphQL type system."""

    SCALAR = "scalar"
    OBJECT = "object"
    INTERFACE = "interface"
    UNION = "union"
    ENUM = "enum"
    INPUT_OBJECT = "input_object"
    LIST = "list"
    NON_NULL = "non_null"


class ScalarType(str, Enum):
    """Built-in scalar types."""

    INT = "Int"
    FLOAT = "Float"
    STRING = "String"
    BOOLEAN = "Boolean"
    ID = "ID"
    DATETIME = "DateTime"
    JSON = "JSON"


@dataclass
class Field:
    """GraphQL field definition."""

    name: str
    type: str
    description: str = ""
    args: Dict[str, "Argument"] = field(default_factory=dict)
    resolver: Optional[Callable] = None
    required: bool = False
    list: bool = False

    def get_type_string(self) -> str:
        """Get GraphQL type string."""
        type_str = self.type

        if self.list:
            type_str = f"[{type_str}]"

        if self.required:
            type_str = f"{type_str}!"

        return type_str


@dataclass
class Argument:
    """GraphQL argument definition."""

    name: str
    type: str
    description: str = ""
    default_value: Any = None
    required: bool = False


@dataclass
class ObjectType:
    """GraphQL object type definition."""

    name: str
    description: str = ""
    fields: Dict[str, Field] = field(default_factory=dict)
    interfaces: List[str] = field(default_factory=list)

    def add_field(self, field: Field):
        """Add a field to this object type."""
        self.fields[field.name] = field

    def to_sdl(self) -> str:
        """Convert to GraphQL SDL (Schema Definition Language)."""
        lines = []

        if self.description:
            lines.append(f'"""{self.description}"""')

        implements = f" implements {', '.join(self.interfaces)}" if self.interfaces else ""
        lines.append(f"type {self.name}{implements} {{")

        for field in self.fields.values():
            field_desc = f'  """{field.description}"""\n  ' if field.description else "  "

            args_str = ""
            if field.args:
                args_parts = []
                for arg in field.args.values():
                    arg_type = f"{arg.type}!" if arg.required else arg.type
                    args_parts.append(f"{arg.name}: {arg_type}")
                args_str = f"({', '.join(args_parts)})"

            lines.append(f"{field_desc}{field.name}{args_str}: {field.get_type_string()}")

        lines.append("}")
        return "\n".join(lines)


@dataclass
class InputType:
    """GraphQL input type definition."""

    name: str
    description: str = ""
    fields: Dict[str, Field] = field(default_factory=dict)

    def to_sdl(self) -> str:
        """Convert to GraphQL SDL."""
        lines = []

        if self.description:
            lines.append(f'"""{self.description}"""')

        lines.append(f"input {self.name} {{")

        for field in self.fields.values():
            field_desc = f'  """{field.description}"""\n  ' if field.description else "  "
            lines.append(f"{field_desc}{field.name}: {field.get_type_string()}")

        lines.append("}")
        return "\n".join(lines)


@dataclass
class EnumType:
    """GraphQL enum type definition."""

    name: str
    description: str = ""
    values: List[str] = field(default_factory=list)

    def to_sdl(self) -> str:
        """Convert to GraphQL SDL."""
        lines = []

        if self.description:
            lines.append(f'"""{self.description}"""')

        lines.append(f"enum {self.name} {{")

        for value in self.values:
            lines.append(f"  {value}")

        lines.append("}")
        return "\n".join(lines)


class Schema:
    """
    GraphQL schema definition.

    Defines all types, queries, mutations, and subscriptions.
    """

    def __init__(self):
        self.types: Dict[str, ObjectType] = {}
        self.input_types: Dict[str, InputType] = {}
        self.enum_types: Dict[str, EnumType] = {}
        self.query_type: Optional[ObjectType] = None
        self.mutation_type: Optional[ObjectType] = None
        self.subscription_type: Optional[ObjectType] = None

    def add_type(self, obj_type: ObjectType):
        """Add an object type to the schema."""
        self.types[obj_type.name] = obj_type

    def add_input_type(self, input_type: InputType):
        """Add an input type to the schema."""
        self.input_types[input_type.name] = input_type

    def add_enum_type(self, enum_type: EnumType):
        """Add an enum type to the schema."""
        self.enum_types[enum_type.name] = enum_type

    def set_query_type(self, query_type: ObjectType):
        """Set the root query type."""
        self.query_type = query_type

    def set_mutation_type(self, mutation_type: ObjectType):
        """Set the root mutation type."""
        self.mutation_type = mutation_type

    def set_subscription_type(self, subscription_type: ObjectType):
        """Set the root subscription type."""
        self.subscription_type = subscription_type

    def to_sdl(self) -> str:
        """Generate GraphQL SDL for the entire schema."""
        lines = []

        # Scalar types
        lines.append("scalar DateTime")
        lines.append("scalar JSON")
        lines.append("")

        # Enum types
        for enum_type in self.enum_types.values():
            lines.append(enum_type.to_sdl())
            lines.append("")

        # Input types
        for input_type in self.input_types.values():
            lines.append(input_type.to_sdl())
            lines.append("")

        # Object types
        for obj_type in self.types.values():
            lines.append(obj_type.to_sdl())
            lines.append("")

        # Query type
        if self.query_type:
            lines.append(self.query_type.to_sdl())
            lines.append("")

        # Mutation type
        if self.mutation_type:
            lines.append(self.mutation_type.to_sdl())
            lines.append("")

        # Subscription type
        if self.subscription_type:
            lines.append(self.subscription_type.to_sdl())
            lines.append("")

        # Schema definition
        schema_parts = []
        if self.query_type:
            schema_parts.append(f"  query: {self.query_type.name}")
        if self.mutation_type:
            schema_parts.append(f"  mutation: {self.mutation_type.name}")
        if self.subscription_type:
            schema_parts.append(f"  subscription: {self.subscription_type.name}")

        if schema_parts:
            lines.append("schema {")
            lines.extend(schema_parts)
            lines.append("}")

        return "\n".join(lines)


class DataLoader:
    """
    DataLoader for batching and caching.

    Prevents N+1 query problems by batching requests.
    """

    def __init__(self, batch_load_fn: Callable):
        self.batch_load_fn = batch_load_fn
        self._batch: List[Any] = []
        self._batch_futures: Dict[Any, asyncio.Future] = {}
        self._cache: Dict[Any, Any] = {}
        self._batch_scheduled = False

    async def load(self, key: Any) -> Any:
        """Load a value by key, batching if possible."""
        # Check cache first
        if key in self._cache:
            return self._cache[key]

        # Add to batch
        if key not in self._batch_futures:
            self._batch.append(key)
            self._batch_futures[key] = asyncio.Future()

            # Schedule batch execution
            if not self._batch_scheduled:
                self._batch_scheduled = True
                asyncio.create_task(self._execute_batch())

        # Wait for batch to complete
        return await self._batch_futures[key]

    async def load_many(self, keys: List[Any]) -> List[Any]:
        """Load multiple values."""
        return await asyncio.gather(*[self.load(key) for key in keys])

    async def _execute_batch(self):
        """Execute the current batch."""
        # Wait for next event loop tick to collect more requests
        await asyncio.sleep(0)

        batch = self._batch
        futures = self._batch_futures

        # Reset batch
        self._batch = []
        self._batch_futures = {}
        self._batch_scheduled = False

        try:
            # Execute batch load
            results = await self.batch_load_fn(batch)

            # Resolve futures and cache results
            for key, result in zip(batch, results):
                self._cache[key] = result
                futures[key].set_result(result)

        except Exception as e:
            # Reject all futures
            for future in futures.values():
                future.set_exception(e)

    def clear(self, key: Optional[Any] = None):
        """Clear cache."""
        if key is None:
            self._cache.clear()
        else:
            self._cache.pop(key, None)


@dataclass
class ResolverContext:
    """Context passed to resolvers."""

    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    request_id: str = ""
    data_loaders: Dict[str, DataLoader] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class Resolver:
    """Base resolver class."""

    async def resolve(self, parent: Any, args: Dict[str, Any], context: ResolverContext, info: Any) -> Any:
        """Resolve field value."""
        raise NotImplementedError


@dataclass
class QueryComplexity:
    """Query complexity analysis."""

    total_complexity: int = 0
    max_depth: int = 0
    field_count: int = 0

    def exceeds_limit(self, max_complexity: int = 1000, max_depth: int = 10) -> bool:
        """Check if complexity exceeds limits."""
        return self.total_complexity > max_complexity or self.max_depth > max_depth


class TSMSchema:
    """
    TSM GraphQL Schema Builder.

    Creates the complete GraphQL schema for TSM.
    """

    def __init__(self):
        self.schema = Schema()
        self._build_schema()

    def _build_schema(self):
        """Build the TSM GraphQL schema."""
        # Enum types
        self._add_enums()

        # Input types
        self._add_input_types()

        # Object types
        self._add_object_types()

        # Root types
        self._add_query_type()
        self._add_mutation_type()
        self._add_subscription_type()

    def _add_enums(self):
        """Add enum types."""
        # Model provider enum
        self.schema.add_enum_type(EnumType(
            name="ModelProvider",
            description="Available model providers",
            values=["OPENAI", "ANTHROPIC", "GOOGLE", "LOCAL", "AZURE", "TOGETHER", "GROQ", "DEEPSEEK"]
        ))

        # Task type enum
        self.schema.add_enum_type(EnumType(
            name="TaskType",
            description="Types of tasks",
            values=["REASONING", "CODE_ANALYSIS", "CODE_GENERATION", "SEARCH", "SUMMARIZATION", "CLASSIFICATION"]
        ))

        # Status enum
        self.schema.add_enum_type(EnumType(
            name="RequestStatus",
            description="Request status",
            values=["PENDING", "PROCESSING", "COMPLETED", "FAILED", "TIMEOUT"]
        ))

        # Tenant tier enum
        self.schema.add_enum_type(EnumType(
            name="TenantTier",
            description="Tenant subscription tier",
            values=["FREE", "STARTER", "PRO", "ENTERPRISE"]
        ))

    def _add_input_types(self):
        """Add input types."""
        # Model execution input
        exec_input = InputType(name="ExecuteModelInput", description="Input for model execution")
        exec_input.fields["prompt"] = Field(name="prompt", type="String", required=True)
        exec_input.fields["model"] = Field(name="model", type="String")
        exec_input.fields["provider"] = Field(name="provider", type="ModelProvider")
        exec_input.fields["temperature"] = Field(name="temperature", type="Float")
        exec_input.fields["maxTokens"] = Field(name="maxTokens", type="Int")
        self.schema.add_input_type(exec_input)

        # Document input
        doc_input = InputType(name="DocumentInput", description="Input for document operations")
        doc_input.fields["content"] = Field(name="content", type="String", required=True)
        doc_input.fields["metadata"] = Field(name="metadata", type="JSON")
        self.schema.add_input_type(doc_input)

    def _add_object_types(self):
        """Add object types."""
        # Model type
        model_type = ObjectType(name="Model", description="AI model information")
        model_type.add_field(Field(name="id", type="ID", required=True))
        model_type.add_field(Field(name="name", type="String", required=True))
        model_type.add_field(Field(name="provider", type="ModelProvider", required=True))
        model_type.add_field(Field(name="contextWindow", type="Int", required=True))
        model_type.add_field(Field(name="costPerToken", type="Float", required=True))
        self.schema.add_type(model_type)

        # Request type
        request_type = ObjectType(name="Request", description="AI request information")
        request_type.add_field(Field(name="id", type="ID", required=True))
        request_type.add_field(Field(name="input", type="String", required=True))
        request_type.add_field(Field(name="output", type="String"))
        request_type.add_field(Field(name="model", type="String", required=True))
        request_type.add_field(Field(name="provider", type="ModelProvider", required=True))
        request_type.add_field(Field(name="status", type="RequestStatus", required=True))
        request_type.add_field(Field(name="tokens", type="Int", required=True))
        request_type.add_field(Field(name="cost", type="Float", required=True))
        request_type.add_field(Field(name="latencyMs", type="Float", required=True))
        request_type.add_field(Field(name="createdAt", type="DateTime", required=True))
        self.schema.add_type(request_type)

        # Document type
        document_type = ObjectType(name="Document", description="Document in memory store")
        document_type.add_field(Field(name="id", type="ID", required=True))
        document_type.add_field(Field(name="content", type="String", required=True))
        document_type.add_field(Field(name="metadata", type="JSON"))
        document_type.add_field(Field(name="createdAt", type="DateTime", required=True))
        self.schema.add_type(document_type)

        # Tenant type
        tenant_type = ObjectType(name="Tenant", description="Tenant information")
        tenant_type.add_field(Field(name="id", type="ID", required=True))
        tenant_type.add_field(Field(name="name", type="String", required=True))
        tenant_type.add_field(Field(name="tier", type="TenantTier", required=True))
        tenant_type.add_field(Field(name="email", type="String", required=True))
        tenant_type.add_field(Field(name="createdAt", type="DateTime", required=True))
        self.schema.add_type(tenant_type)

        # Analytics type
        analytics_type = ObjectType(name="Analytics", description="Usage analytics")
        analytics_type.add_field(Field(name="totalRequests", type="Int", required=True))
        analytics_type.add_field(Field(name="totalTokens", type="Int", required=True))
        analytics_type.add_field(Field(name="totalCost", type="Float", required=True))
        analytics_type.add_field(Field(name="avgLatencyMs", type="Float", required=True))
        analytics_type.add_field(Field(name="successRate", type="Float", required=True))
        self.schema.add_type(analytics_type)

    def _add_query_type(self):
        """Add root query type."""
        query = ObjectType(name="Query", description="Root query type")

        # Model queries
        query.add_field(Field(
            name="models",
            type="Model",
            description="List available models",
            list=True,
            required=True
        ))

        query.add_field(Field(
            name="model",
            type="Model",
            description="Get model by ID",
            args={"id": Argument(name="id", type="ID", required=True)}
        ))

        # Request queries
        query.add_field(Field(
            name="requests",
            type="Request",
            description="List recent requests",
            list=True,
            required=True,
            args={
                "limit": Argument(name="limit", type="Int", default_value=10),
                "offset": Argument(name="offset", type="Int", default_value=0)
            }
        ))

        query.add_field(Field(
            name="request",
            type="Request",
            description="Get request by ID",
            args={"id": Argument(name="id", type="ID", required=True)}
        ))

        # Document queries
        query.add_field(Field(
            name="documents",
            type="Document",
            description="List documents",
            list=True,
            required=True,
            args={
                "limit": Argument(name="limit", type="Int", default_value=10),
                "offset": Argument(name="offset", type="Int", default_value=0)
            }
        ))

        query.add_field(Field(
            name="searchDocuments",
            type="Document",
            description="Search documents",
            list=True,
            required=True,
            args={"query": Argument(name="query", type="String", required=True)}
        ))

        # Analytics queries
        query.add_field(Field(
            name="analytics",
            type="Analytics",
            description="Get usage analytics",
            required=True,
            args={
                "startDate": Argument(name="startDate", type="DateTime"),
                "endDate": Argument(name="endDate", type="DateTime")
            }
        ))

        # Tenant queries
        query.add_field(Field(
            name="tenant",
            type="Tenant",
            description="Get current tenant",
            required=True
        ))

        self.schema.set_query_type(query)

    def _add_mutation_type(self):
        """Add root mutation type."""
        mutation = ObjectType(name="Mutation", description="Root mutation type")

        # Model execution
        mutation.add_field(Field(
            name="executeModel",
            type="Request",
            description="Execute AI model",
            required=True,
            args={"input": Argument(name="input", type="ExecuteModelInput", required=True)}
        ))

        # Document mutations
        mutation.add_field(Field(
            name="addDocument",
            type="Document",
            description="Add a document to memory",
            required=True,
            args={"input": Argument(name="input", type="DocumentInput", required=True)}
        ))

        mutation.add_field(Field(
            name="deleteDocument",
            type="Boolean",
            description="Delete a document",
            required=True,
            args={"id": Argument(name="id", type="ID", required=True)}
        ))

        # Cache mutations
        mutation.add_field(Field(
            name="clearCache",
            type="Boolean",
            description="Clear cache",
            required=True
        ))

        self.schema.set_mutation_type(mutation)

    def _add_subscription_type(self):
        """Add root subscription type."""
        subscription = ObjectType(name="Subscription", description="Root subscription type")

        # Request status subscription
        subscription.add_field(Field(
            name="requestStatus",
            type="Request",
            description="Subscribe to request status updates",
            required=True,
            args={"requestId": Argument(name="requestId", type="ID", required=True)}
        ))

        # Analytics subscription
        subscription.add_field(Field(
            name="analyticsUpdates",
            type="Analytics",
            description="Subscribe to real-time analytics",
            required=True
        ))

        self.schema.set_subscription_type(subscription)

    def get_sdl(self) -> str:
        """Get the GraphQL SDL."""
        return self.schema.to_sdl()


def build_tsm_schema() -> str:
    """Build and return the TSM GraphQL schema SDL."""
    schema_builder = TSMSchema()
    return schema_builder.get_sdl()


__all__ = [
    "Schema",
    "ObjectType",
    "InputType",
    "EnumType",
    "Field",
    "Argument",
    "DataLoader",
    "ResolverContext",
    "Resolver",
    "QueryComplexity",
    "TSMSchema",
    "build_tsm_schema",
]
