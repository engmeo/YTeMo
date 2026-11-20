# Y TE MO - API Schemas

Generated from OpenAPI components.schemas.

## AgentTaskRequest

| Field | Type | Required | Default | Allowed values |
|---|---|---|---|---|
| goal | string | Yes | - | - |
| conversation_id | object / unspecified | No | - | - |

## ChatRequest

| Field | Type | Required | Default | Allowed values |
|---|---|---|---|---|
| message | string | Yes | - | - |
| conversation_id | object / unspecified | No | - | - |

## ConsentRequest

| Field | Type | Required | Default | Allowed values |
|---|---|---|---|---|
| scope | ConsentScope | Yes | - | - |
| granted | boolean | Yes | - | - |

## ConsentScope

| Field | Type | Required | Default | Allowed values |
|---|---|---|---|---|

## ContextRequest

| Field | Type | Required | Default | Allowed values |
|---|---|---|---|---|
| scope | ConsentScope | Yes | - | - |
| category | string | Yes | - | - |
| content | string | Yes | - | - |
| source | string | No | user_provided | - |
| expires_at | object / unspecified | No | - | - |

## FollowUpRequest

| Field | Type | Required | Default | Allowed values |
|---|---|---|---|---|
| summary | string | Yes | - | - |

## HTTPValidationError

| Field | Type | Required | Default | Allowed values |
|---|---|---|---|---|
| detail | array | No | - | - |

## NeedRequest

| Field | Type | Required | Default | Allowed values |
|---|---|---|---|---|
| title | string | Yes | - | - |
| description | string | No | Chưa có mô tả | - |
| priority | UserPriority | No | normal | - |
| next_step | object / unspecified | No | - | - |

## NeedStatus

| Field | Type | Required | Default | Allowed values |
|---|---|---|---|---|

## NeedUpdateRequest

| Field | Type | Required | Default | Allowed values |
|---|---|---|---|---|
| status | object / unspecified | No | - | - |
| next_step | object / unspecified | No | - | - |

## ProactiveEventRequest

| Field | Type | Required | Default | Allowed values |
|---|---|---|---|---|
| trigger_type | TriggerType | Yes | - | - |
| summary | string | Yes | - | - |
| source | string | No | user_action | - |

## ProposalStatus

| Field | Type | Required | Default | Allowed values |
|---|---|---|---|---|

## ProposalStatusRequest

| Field | Type | Required | Default | Allowed values |
|---|---|---|---|---|
| status | ProposalStatus | Yes | - | - |

## TriggerType

| Field | Type | Required | Default | Allowed values |
|---|---|---|---|---|

## UserPriority

| Field | Type | Required | Default | Allowed values |
|---|---|---|---|---|

## ValidationError

| Field | Type | Required | Default | Allowed values |
|---|---|---|---|---|
| loc | array | Yes | - | - |
| msg | string | Yes | - | - |
| type | string | Yes | - | - |
| input | object / unspecified | No | - | - |
| ctx | object | No | - | - |

