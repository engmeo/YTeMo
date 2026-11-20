# Y TE MO - Complete API Endpoint Inventory

Generated from openapi.json. Do not manually invent request/response fields.

## GET /
Summary: Root
Operation ID: root__get

### Responses
- HTTP 200: Successful Response

Security: No operation-level security declaration

## GET /health
Summary: Health Check
Operation ID: health_check_health_get

### Responses
- HTTP 200: Successful Response

Security: No operation-level security declaration

## GET /public-config
Summary: Public Config
Operation ID: public_config_public_config_get

### Responses
- HTTP 200: Successful Response

Security: No operation-level security declaration

## GET /conversations/{conversation_id}/messages
Summary: Get Conversation Messages
Operation ID: get_conversation_messages_conversations__conversation_id__messages_get

### Parameters
- conversation_id [path] Required: True
  - Type: string

### Responses
- HTTP 200: Successful Response
- HTTP 422: Validation Error
  - Schema: HTTPValidationError

Security: Required by operation

## POST /chat
Summary: Chat Endpoint
Operation ID: chat_endpoint_chat_post

### Request body
- Content-Type: application/json
- Schema: ChatRequest

### Responses
- HTTP 200: Successful Response
- HTTP 422: Validation Error
  - Schema: HTTPValidationError

Security: Required by operation

## GET /agent/tasks
Summary: List Agent Tasks
Operation ID: list_agent_tasks_agent_tasks_get

### Responses
- HTTP 200: Successful Response

Security: Required by operation

## POST /agent/tasks
Summary: Create Agent Task
Operation ID: create_agent_task_agent_tasks_post

### Request body
- Content-Type: application/json
- Schema: AgentTaskRequest

### Responses
- HTTP 202: Successful Response
- HTTP 422: Validation Error
  - Schema: HTTPValidationError

Security: Required by operation

## GET /agent/tasks/{task_id}
Summary: Get Agent Task
Operation ID: get_agent_task_agent_tasks__task_id__get

### Parameters
- task_id [path] Required: True
  - Type: string

### Responses
- HTTP 200: Successful Response
- HTTP 422: Validation Error
  - Schema: HTTPValidationError

Security: Required by operation

## POST /agent/tasks/{task_id}/resume
Summary: Resume Agent Task
Operation ID: resume_agent_task_agent_tasks__task_id__resume_post

### Parameters
- task_id [path] Required: True
  - Type: string

### Responses
- HTTP 202: Successful Response
- HTTP 422: Validation Error
  - Schema: HTTPValidationError

Security: Required by operation

## POST /companion/initialize
Summary: Companion Initialize
Operation ID: companion_initialize_companion_initialize_post

### Responses
- HTTP 200: Successful Response

Security: Required by operation

## GET /companion
Summary: Companion Snapshot
Operation ID: companion_snapshot_companion_get

### Responses
- HTTP 200: Successful Response

Security: Required by operation

## PUT /companion/consent
Summary: Companion Set Consent
Operation ID: companion_set_consent_companion_consent_put

### Request body
- Content-Type: application/json
- Schema: ConsentRequest

### Responses
- HTTP 200: Successful Response
- HTTP 422: Validation Error
  - Schema: HTTPValidationError

Security: Required by operation

## GET /companion/context
Summary: Companion Get Context
Operation ID: companion_get_context_companion_context_get

### Responses
- HTTP 200: Successful Response

Security: Required by operation

## POST /companion/context
Summary: Companion Save Context
Operation ID: companion_save_context_companion_context_post

### Request body
- Content-Type: application/json
- Schema: ContextRequest

### Responses
- HTTP 200: Successful Response
- HTTP 422: Validation Error
  - Schema: HTTPValidationError

Security: Required by operation

## DELETE /companion/context/{context_id}
Summary: Companion Delete Context
Operation ID: companion_delete_context_companion_context__context_id__delete

### Parameters
- context_id [path] Required: True
  - Type: string

### Responses
- HTTP 200: Successful Response
- HTTP 422: Validation Error
  - Schema: HTTPValidationError

Security: Required by operation

## POST /companion/needs
Summary: Companion Create Need
Operation ID: companion_create_need_companion_needs_post

### Request body
- Content-Type: application/json
- Schema: NeedRequest

### Responses
- HTTP 200: Successful Response
- HTTP 422: Validation Error
  - Schema: HTTPValidationError

Security: Required by operation

## GET /companion/needs
Summary: Companion List Needs
Operation ID: companion_list_needs_companion_needs_get

### Parameters
- include_resolved [query] Required: False
  - Type: boolean

### Responses
- HTTP 200: Successful Response
- HTTP 422: Validation Error
  - Schema: HTTPValidationError

Security: Required by operation

## PATCH /companion/needs/{need_id}
Summary: Companion Update Need
Operation ID: companion_update_need_companion_needs__need_id__patch

### Parameters
- need_id [path] Required: True
  - Type: string

### Request body
- Content-Type: application/json
- Schema: NeedUpdateRequest

### Responses
- HTTP 200: Successful Response
- HTTP 422: Validation Error
  - Schema: HTTPValidationError

Security: Required by operation

## POST /companion/follow-up
Summary: Companion Record Follow Up
Operation ID: companion_record_follow_up_companion_follow_up_post

### Request body
- Content-Type: application/json
- Schema: FollowUpRequest

### Responses
- HTTP 200: Successful Response
- HTTP 422: Validation Error
  - Schema: HTTPValidationError

Security: Required by operation

## POST /companion/proactive/evaluate
Summary: Companion Evaluate Proactive
Operation ID: companion_evaluate_proactive_companion_proactive_evaluate_post

### Request body
- Content-Type: application/json
- Schema: ProactiveEventRequest

### Responses
- HTTP 200: Successful Response
- HTTP 422: Validation Error
  - Schema: HTTPValidationError

Security: Required by operation

## GET /companion/proactive/proposals
Summary: Companion List Proposals
Operation ID: companion_list_proposals_companion_proactive_proposals_get

### Responses
- HTTP 200: Successful Response

Security: Required by operation

## PATCH /companion/proactive/proposals/{proposal_id}
Summary: Companion Update Proposal
Operation ID: companion_update_proposal_companion_proactive_proposals__proposal_id__patch

### Parameters
- proposal_id [path] Required: True
  - Type: string

### Request body
- Content-Type: application/json
- Schema: ProposalStatusRequest

### Responses
- HTTP 200: Successful Response
- HTTP 422: Validation Error
  - Schema: HTTPValidationError

Security: Required by operation

