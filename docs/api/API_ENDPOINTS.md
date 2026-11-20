# API Endpoint Reference — Y TẾ MỞ

> Sinh tự động từ docs/api/openapi.json. Không tự suy diễn payload hoặc schema không được khai báo.

## Tổng quan

| Method | Endpoint | Mô tả |
|---|---|---|
| `GET` | `/` | Root |
| `GET` | `/agent/tasks` | List Agent Tasks |
| `POST` | `/agent/tasks` | Create Agent Task |
| `GET` | `/agent/tasks/{task_id}` | Get Agent Task |
| `POST` | `/agent/tasks/{task_id}/resume` | Resume Agent Task |
| `POST` | `/chat` | Chat Endpoint |
| `GET` | `/companion` | Companion Snapshot |
| `PUT` | `/companion/consent` | Companion Set Consent |
| `GET` | `/companion/context` | Companion Get Context |
| `POST` | `/companion/context` | Companion Save Context |
| `DELETE` | `/companion/context/{context_id}` | Companion Delete Context |
| `POST` | `/companion/follow-up` | Companion Record Follow Up |
| `POST` | `/companion/initialize` | Companion Initialize |
| `GET` | `/companion/needs` | Companion List Needs |
| `POST` | `/companion/needs` | Companion Create Need |
| `PATCH` | `/companion/needs/{need_id}` | Companion Update Need |
| `POST` | `/companion/proactive/evaluate` | Companion Evaluate Proactive |
| `GET` | `/companion/proactive/proposals` | Companion List Proposals |
| `PATCH` | `/companion/proactive/proposals/{proposal_id}` | Companion Update Proposal |
| `GET` | `/conversations/{conversation_id}/messages` | Get Conversation Messages |
| `GET` | `/health` | Health Check |
| `GET` | `/public-config` | Public Config |

## Chi tiết theo endpoint

### `GET /`

- **Mô tả:** Root
- **operationId:** `root__get`
- **Xác thực:** Chưa thể kết luận chỉ từ OpenAPI

**Parameters**

- `` (; required=):  — schema: `Không khai báo`

**Request body:** OpenAPI không khai báo.

**Responses**

- `200`: Successful Response
  - `application/json` schema: `{}`

---

### `GET /agent/tasks`

- **Mô tả:** List Agent Tasks
- **operationId:** `list_agent_tasks_agent_tasks_get`
- **Xác thực:** Có khai báo security trong OpenAPI; cần đối chiếu dependency Backend

**Parameters**

- `` (; required=):  — schema: `Không khai báo`

**Request body:** OpenAPI không khai báo.

**Responses**

- `200`: Successful Response
  - `application/json` schema: `{}`

---

### `POST /agent/tasks`

- **Mô tả:** Create Agent Task
- **operationId:** `create_agent_task_agent_tasks_post`
- **Xác thực:** Có khai báo security trong OpenAPI; cần đối chiếu dependency Backend

**Parameters**

- `` (; required=):  — schema: `Không khai báo`

**Request body**

- `application/json` — required=True; schema: `#/components/schemas/AgentTaskRequest`

**Responses**

- `202`: Successful Response
  - `application/json` schema: `{}`
- `422`: Validation Error
  - `application/json` schema: `#/components/schemas/HTTPValidationError`

---

### `GET /agent/tasks/{task_id}`

- **Mô tả:** Get Agent Task
- **operationId:** `get_agent_task_agent_tasks__task_id__get`
- **Xác thực:** Có khai báo security trong OpenAPI; cần đối chiếu dependency Backend

**Parameters**

- `task_id` (path; required=True):  — schema: `{"type":"string","title":"Task Id"}`

**Request body:** OpenAPI không khai báo.

**Responses**

- `200`: Successful Response
  - `application/json` schema: `{}`
- `422`: Validation Error
  - `application/json` schema: `#/components/schemas/HTTPValidationError`

---

### `POST /agent/tasks/{task_id}/resume`

- **Mô tả:** Resume Agent Task
- **operationId:** `resume_agent_task_agent_tasks__task_id__resume_post`
- **Xác thực:** Có khai báo security trong OpenAPI; cần đối chiếu dependency Backend

**Parameters**

- `task_id` (path; required=True):  — schema: `{"type":"string","title":"Task Id"}`

**Request body:** OpenAPI không khai báo.

**Responses**

- `202`: Successful Response
  - `application/json` schema: `{}`
- `422`: Validation Error
  - `application/json` schema: `#/components/schemas/HTTPValidationError`

---

### `POST /chat`

- **Mô tả:** Chat Endpoint
- **operationId:** `chat_endpoint_chat_post`
- **Xác thực:** Có khai báo security trong OpenAPI; cần đối chiếu dependency Backend

**Parameters**

- `` (; required=):  — schema: `Không khai báo`

**Request body**

- `application/json` — required=True; schema: `#/components/schemas/ChatRequest`

**Responses**

- `200`: Successful Response
  - `application/json` schema: `{}`
- `422`: Validation Error
  - `application/json` schema: `#/components/schemas/HTTPValidationError`

---

### `GET /companion`

- **Mô tả:** Companion Snapshot
- **operationId:** `companion_snapshot_companion_get`
- **Xác thực:** Có khai báo security trong OpenAPI; cần đối chiếu dependency Backend

**Parameters**

- `` (; required=):  — schema: `Không khai báo`

**Request body:** OpenAPI không khai báo.

**Responses**

- `200`: Successful Response
  - `application/json` schema: `{}`

---

### `PUT /companion/consent`

- **Mô tả:** Companion Set Consent
- **operationId:** `companion_set_consent_companion_consent_put`
- **Xác thực:** Có khai báo security trong OpenAPI; cần đối chiếu dependency Backend

**Parameters**

- `` (; required=):  — schema: `Không khai báo`

**Request body**

- `application/json` — required=True; schema: `#/components/schemas/ConsentRequest`

**Responses**

- `200`: Successful Response
  - `application/json` schema: `{}`
- `422`: Validation Error
  - `application/json` schema: `#/components/schemas/HTTPValidationError`

---

### `GET /companion/context`

- **Mô tả:** Companion Get Context
- **operationId:** `companion_get_context_companion_context_get`
- **Xác thực:** Có khai báo security trong OpenAPI; cần đối chiếu dependency Backend

**Parameters**

- `` (; required=):  — schema: `Không khai báo`

**Request body:** OpenAPI không khai báo.

**Responses**

- `200`: Successful Response
  - `application/json` schema: `{}`

---

### `POST /companion/context`

- **Mô tả:** Companion Save Context
- **operationId:** `companion_save_context_companion_context_post`
- **Xác thực:** Có khai báo security trong OpenAPI; cần đối chiếu dependency Backend

**Parameters**

- `` (; required=):  — schema: `Không khai báo`

**Request body**

- `application/json` — required=True; schema: `#/components/schemas/ContextRequest`

**Responses**

- `200`: Successful Response
  - `application/json` schema: `{}`
- `422`: Validation Error
  - `application/json` schema: `#/components/schemas/HTTPValidationError`

---

### `DELETE /companion/context/{context_id}`

- **Mô tả:** Companion Delete Context
- **operationId:** `companion_delete_context_companion_context__context_id__delete`
- **Xác thực:** Có khai báo security trong OpenAPI; cần đối chiếu dependency Backend

**Parameters**

- `context_id` (path; required=True):  — schema: `{"type":"string","title":"Context Id"}`

**Request body:** OpenAPI không khai báo.

**Responses**

- `200`: Successful Response
  - `application/json` schema: `{}`
- `422`: Validation Error
  - `application/json` schema: `#/components/schemas/HTTPValidationError`

---

### `POST /companion/follow-up`

- **Mô tả:** Companion Record Follow Up
- **operationId:** `companion_record_follow_up_companion_follow_up_post`
- **Xác thực:** Có khai báo security trong OpenAPI; cần đối chiếu dependency Backend

**Parameters**

- `` (; required=):  — schema: `Không khai báo`

**Request body**

- `application/json` — required=True; schema: `#/components/schemas/FollowUpRequest`

**Responses**

- `200`: Successful Response
  - `application/json` schema: `{}`
- `422`: Validation Error
  - `application/json` schema: `#/components/schemas/HTTPValidationError`

---

### `POST /companion/initialize`

- **Mô tả:** Companion Initialize
- **operationId:** `companion_initialize_companion_initialize_post`
- **Xác thực:** Có khai báo security trong OpenAPI; cần đối chiếu dependency Backend

**Parameters**

- `` (; required=):  — schema: `Không khai báo`

**Request body:** OpenAPI không khai báo.

**Responses**

- `200`: Successful Response
  - `application/json` schema: `{}`

---

### `GET /companion/needs`

- **Mô tả:** Companion List Needs
- **operationId:** `companion_list_needs_companion_needs_get`
- **Xác thực:** Có khai báo security trong OpenAPI; cần đối chiếu dependency Backend

**Parameters**

- `include_resolved` (query; required=False):  — schema: `{"type":"boolean","default":false,"title":"Include Resolved"}`

**Request body:** OpenAPI không khai báo.

**Responses**

- `200`: Successful Response
  - `application/json` schema: `{}`
- `422`: Validation Error
  - `application/json` schema: `#/components/schemas/HTTPValidationError`

---

### `POST /companion/needs`

- **Mô tả:** Companion Create Need
- **operationId:** `companion_create_need_companion_needs_post`
- **Xác thực:** Có khai báo security trong OpenAPI; cần đối chiếu dependency Backend

**Parameters**

- `` (; required=):  — schema: `Không khai báo`

**Request body**

- `application/json` — required=True; schema: `#/components/schemas/NeedRequest`

**Responses**

- `200`: Successful Response
  - `application/json` schema: `{}`
- `422`: Validation Error
  - `application/json` schema: `#/components/schemas/HTTPValidationError`

---

### `PATCH /companion/needs/{need_id}`

- **Mô tả:** Companion Update Need
- **operationId:** `companion_update_need_companion_needs__need_id__patch`
- **Xác thực:** Có khai báo security trong OpenAPI; cần đối chiếu dependency Backend

**Parameters**

- `need_id` (path; required=True):  — schema: `{"type":"string","title":"Need Id"}`

**Request body**

- `application/json` — required=True; schema: `#/components/schemas/NeedUpdateRequest`

**Responses**

- `200`: Successful Response
  - `application/json` schema: `{}`
- `422`: Validation Error
  - `application/json` schema: `#/components/schemas/HTTPValidationError`

---

### `POST /companion/proactive/evaluate`

- **Mô tả:** Companion Evaluate Proactive
- **operationId:** `companion_evaluate_proactive_companion_proactive_evaluate_post`
- **Xác thực:** Có khai báo security trong OpenAPI; cần đối chiếu dependency Backend

**Parameters**

- `` (; required=):  — schema: `Không khai báo`

**Request body**

- `application/json` — required=True; schema: `#/components/schemas/ProactiveEventRequest`

**Responses**

- `200`: Successful Response
  - `application/json` schema: `{}`
- `422`: Validation Error
  - `application/json` schema: `#/components/schemas/HTTPValidationError`

---

### `GET /companion/proactive/proposals`

- **Mô tả:** Companion List Proposals
- **operationId:** `companion_list_proposals_companion_proactive_proposals_get`
- **Xác thực:** Có khai báo security trong OpenAPI; cần đối chiếu dependency Backend

**Parameters**

- `` (; required=):  — schema: `Không khai báo`

**Request body:** OpenAPI không khai báo.

**Responses**

- `200`: Successful Response
  - `application/json` schema: `{}`

---

### `PATCH /companion/proactive/proposals/{proposal_id}`

- **Mô tả:** Companion Update Proposal
- **operationId:** `companion_update_proposal_companion_proactive_proposals__proposal_id__patch`
- **Xác thực:** Có khai báo security trong OpenAPI; cần đối chiếu dependency Backend

**Parameters**

- `proposal_id` (path; required=True):  — schema: `{"type":"string","title":"Proposal Id"}`

**Request body**

- `application/json` — required=True; schema: `#/components/schemas/ProposalStatusRequest`

**Responses**

- `200`: Successful Response
  - `application/json` schema: `{}`
- `422`: Validation Error
  - `application/json` schema: `#/components/schemas/HTTPValidationError`

---

### `GET /conversations/{conversation_id}/messages`

- **Mô tả:** Get Conversation Messages
- **operationId:** `get_conversation_messages_conversations__conversation_id__messages_get`
- **Xác thực:** Có khai báo security trong OpenAPI; cần đối chiếu dependency Backend

**Parameters**

- `conversation_id` (path; required=True):  — schema: `{"type":"string","title":"Conversation Id"}`

**Request body:** OpenAPI không khai báo.

**Responses**

- `200`: Successful Response
  - `application/json` schema: `{}`
- `422`: Validation Error
  - `application/json` schema: `#/components/schemas/HTTPValidationError`

---

### `GET /health`

- **Mô tả:** Health Check
- **operationId:** `health_check_health_get`
- **Xác thực:** Chưa thể kết luận chỉ từ OpenAPI

**Parameters**

- `` (; required=):  — schema: `Không khai báo`

**Request body:** OpenAPI không khai báo.

**Responses**

- `200`: Successful Response
  - `application/json` schema: `{}`

---

### `GET /public-config`

- **Mô tả:** Public Config
- **operationId:** `public_config_public_config_get`
- **Xác thực:** Chưa thể kết luận chỉ từ OpenAPI

**Parameters**

- `` (; required=):  — schema: `Không khai báo`

**Request body:** OpenAPI không khai báo.

**Responses**

- `200`: Successful Response
  - `application/json` schema: `{}`

---

## Components / Schemas

### `AgentTaskRequest`

```json
{
    "properties":  {
                       "goal":  {
                                    "type":  "string",
                                    "maxLength":  4000,
                                    "minLength":  1,
                                    "title":  "Goal"
                                },
                       "conversation_id":  {
                                               "anyOf":  [
                                                             {
                                                                 "type":  "string"
                                                             },
                                                             {
                                                                 "type":  "null"
                                                             }
                                                         ],
                                               "title":  "Conversation Id"
                                           }
                   },
    "type":  "object",
    "required":  [
                     "goal"
                 ],
    "title":  "AgentTaskRequest"
}
```

### `ChatRequest`

```json
{
    "properties":  {
                       "message":  {
                                       "type":  "string",
                                       "maxLength":  4000,
                                       "minLength":  1,
                                       "title":  "Message"
                                   },
                       "conversation_id":  {
                                               "anyOf":  [
                                                             {
                                                                 "type":  "string"
                                                             },
                                                             {
                                                                 "type":  "null"
                                                             }
                                                         ],
                                               "title":  "Conversation Id"
                                           }
                   },
    "type":  "object",
    "required":  [
                     "message"
                 ],
    "title":  "ChatRequest"
}
```

### `ConsentRequest`

```json
{
    "properties":  {
                       "scope":  {
                                     "$ref":  "#/components/schemas/ConsentScope"
                                 },
                       "granted":  {
                                       "type":  "boolean",
                                       "title":  "Granted"
                                   }
                   },
    "type":  "object",
    "required":  [
                     "scope",
                     "granted"
                 ],
    "title":  "ConsentRequest"
}
```

### `ConsentScope`

```json
{
    "type":  "string",
    "enum":  [
                 "basic_profile",
                 "care_needs",
                 "health_context",
                 "follow_up",
                 "proactive_contact"
             ],
    "title":  "ConsentScope"
}
```

### `ContextRequest`

```json
{
    "properties":  {
                       "scope":  {
                                     "$ref":  "#/components/schemas/ConsentScope"
                                 },
                       "category":  {
                                        "type":  "string",
                                        "maxLength":  100,
                                        "minLength":  1,
                                        "title":  "Category"
                                    },
                       "content":  {
                                       "type":  "string",
                                       "maxLength":  8000,
                                       "minLength":  1,
                                       "title":  "Content"
                                   },
                       "source":  {
                                      "type":  "string",
                                      "maxLength":  100,
                                      "title":  "Source",
                                      "default":  "user_provided"
                                  },
                       "expires_at":  {
                                          "anyOf":  [
                                                        {
                                                            "type":  "string"
                                                        },
                                                        {
                                                            "type":  "null"
                                                        }
                                                    ],
                                          "title":  "Expires At"
                                      }
                   },
    "type":  "object",
    "required":  [
                     "scope",
                     "category",
                     "content"
                 ],
    "title":  "ContextRequest"
}
```

### `FollowUpRequest`

```json
{
    "properties":  {
                       "summary":  {
                                       "type":  "string",
                                       "maxLength":  2000,
                                       "minLength":  1,
                                       "title":  "Summary"
                                   }
                   },
    "type":  "object",
    "required":  [
                     "summary"
                 ],
    "title":  "FollowUpRequest"
}
```

### `HTTPValidationError`

```json
{
    "properties":  {
                       "detail":  {
                                      "items":  {
                                                    "$ref":  "#/components/schemas/ValidationError"
                                                },
                                      "type":  "array",
                                      "title":  "Detail"
                                  }
                   },
    "type":  "object",
    "title":  "HTTPValidationError"
}
```

### `NeedRequest`

```json
{
    "properties":  {
                       "title":  {
                                     "type":  "string",
                                     "maxLength":  200,
                                     "minLength":  1,
                                     "title":  "Title"
                                 },
                       "description":  {
                                           "type":  "string",
                                           "maxLength":  4000,
                                           "minLength":  1,
                                           "title":  "Description",
                                           "default":  "Chưa có mô tả"
                                       },
                       "priority":  {
                                        "$ref":  "#/components/schemas/UserPriority",
                                        "default":  "normal"
                                    },
                       "next_step":  {
                                         "anyOf":  [
                                                       {
                                                           "type":  "string",
                                                           "maxLength":  1000
                                                       },
                                                       {
                                                           "type":  "null"
                                                       }
                                                   ],
                                         "title":  "Next Step"
                                     }
                   },
    "type":  "object",
    "required":  [
                     "title"
                 ],
    "title":  "NeedRequest"
}
```

### `NeedStatus`

```json
{
    "type":  "string",
    "enum":  [
                 "open",
                 "in_progress",
                 "waiting",
                 "resolved",
                 "paused"
             ],
    "title":  "NeedStatus"
}
```

### `NeedUpdateRequest`

```json
{
    "properties":  {
                       "status":  {
                                      "anyOf":  [
                                                    {
                                                        "$ref":  "#/components/schemas/NeedStatus"
                                                    },
                                                    {
                                                        "type":  "null"
                                                    }
                                                ]
                                  },
                       "next_step":  {
                                         "anyOf":  [
                                                       {
                                                           "type":  "string",
                                                           "maxLength":  1000
                                                       },
                                                       {
                                                           "type":  "null"
                                                       }
                                                   ],
                                         "title":  "Next Step"
                                     }
                   },
    "type":  "object",
    "title":  "NeedUpdateRequest"
}
```

### `ProactiveEventRequest`

```json
{
    "properties":  {
                       "trigger_type":  {
                                            "$ref":  "#/components/schemas/TriggerType"
                                        },
                       "summary":  {
                                       "type":  "string",
                                       "maxLength":  2000,
                                       "minLength":  1,
                                       "title":  "Summary"
                                   },
                       "source":  {
                                      "type":  "string",
                                      "maxLength":  100,
                                      "title":  "Source",
                                      "default":  "user_action"
                                  }
                   },
    "type":  "object",
    "required":  [
                     "trigger_type",
                     "summary"
                 ],
    "title":  "ProactiveEventRequest"
}
```

### `ProposalStatus`

```json
{
    "type":  "string",
    "enum":  [
                 "proposed",
                 "dismissed",
                 "accepted",
                 "expired"
             ],
    "title":  "ProposalStatus"
}
```

### `ProposalStatusRequest`

```json
{
    "properties":  {
                       "status":  {
                                      "$ref":  "#/components/schemas/ProposalStatus"
                                  }
                   },
    "type":  "object",
    "required":  [
                     "status"
                 ],
    "title":  "ProposalStatusRequest"
}
```

### `TriggerType`

```json
{
    "type":  "string",
    "enum":  [
                 "user_returned",
                 "user_requested_follow_up",
                 "scheduled_review",
                 "task_completed",
                 "need_status_changed"
             ],
    "title":  "TriggerType"
}
```

### `UserPriority`

```json
{
    "type":  "string",
    "enum":  [
                 "low",
                 "normal",
                 "high"
             ],
    "title":  "UserPriority"
}
```

### `ValidationError`

```json
{
    "properties":  {
                       "loc":  {
                                   "items":  {
                                                 "anyOf":  [
                                                               {
                                                                   "type":  "string"
                                                               },
                                                               {
                                                                   "type":  "integer"
                                                               }
                                                           ]
                                             },
                                   "type":  "array",
                                   "title":  "Location"
                               },
                       "msg":  {
                                   "type":  "string",
                                   "title":  "Message"
                               },
                       "type":  {
                                    "type":  "string",
                                    "title":  "Error Type"
                                },
                       "input":  {
                                     "title":  "Input"
                                 },
                       "ctx":  {
                                   "type":  "object",
                                   "title":  "Context"
                               }
                   },
    "type":  "object",
    "required":  [
                     "loc",
                     "msg",
                     "type"
                 ],
    "title":  "ValidationError"
}
```


## Quy tắc sử dụng

- Frontend lấy Supabase session bằng SDK, sau đó gửi access token dưới dạng `Authorization: Bearer <access_token>` tới endpoint yêu cầu xác thực.
- Không đưa Supabase `service_role` key vào trình duyệt.
- Không tự tạo payload theo phỏng đoán; dùng schema trong phần chi tiết hoặc OpenAPI.
- API public như health/config không thay thế xác thực người dùng.
- Có endpoint trong OpenAPI không đồng nghĩa Frontend đã tích hợp hoặc production đã triển khai.
