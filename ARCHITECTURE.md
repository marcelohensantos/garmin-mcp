# Architecture — garmin-mcp

## Overview

FastMCP server that exposes Garmin Connect data and workout management to AI agents. Tools are Python functions registered via the `@mcp.tool()` decorator; the framework handles JSON-RPC transport.

---

## Layer diagram

```mermaid
flowchart TD
    Agent(["AI Agent / Claude"])

    subgraph mcp["FastMCP — app.py"]
        subgraph builders["Workout Builders  (tools/)"]
            running["running.py\ncreate_running_workout\nupdate_running_workout"]
            swimming["swimming.py\ncreate_swimming_workout"]
            strength["strength.py\ncreate_strength_workout"]
            builder["builder.py\nWorkoutBuilder · repeat_group"]
        end

        subgraph ops["Operations  (tools/)"]
            calendar["calendar.py\nschedule · get · delete · get_scheduled"]
            data["activities · health · training\nprofile · plans"]
        end
    end

    auth["auth.py\nGarmin client singleton"]
    garmin[("Garmin Connect API")]

    Agent -->|"MCP / JSON-RPC over stdio"| mcp

    running --> builder
    swimming --> builder
    strength --> builder
    builder -->|"auth.get_client()"| auth
    calendar -->|"auth.get_client()"| auth
    data -->|"auth.get_client()"| auth

    auth -->|"HTTPS / garth OAuth2"| garmin
```

---

## Class diagram

```mermaid
classDiagram
    class WorkoutBuilder {
        +build_payload(spec: dict) dict
        +create(spec: dict) dict
        +update(workout_id: str, spec: dict) dict
    }

    class RunningBuilder {
        +build_payload(spec: dict) dict
    }
    class SwimmingBuilder {
        +build_payload(spec: dict) dict
    }
    class StrengthBuilder {
        +build_payload(spec: dict) dict
    }

    WorkoutBuilder <|-- RunningBuilder
    WorkoutBuilder <|-- SwimmingBuilder
    WorkoutBuilder <|-- StrengthBuilder

    class GarminClient {
        +upload_workout(payload: dict) dict
        +schedule_workout(id, date) dict
        +get_workouts(start, limit) list
        +delete_workout(id) None
        +get_scheduled_workouts(year, month) list
        +client.put(domain, path, json) Response
    }

    WorkoutBuilder --> GarminClient : auth.get_client()

    class FastMCP {
        +tool() decorator
        +run()
    }

    class RunningTools {
        +create_running_workout(json) str
        +update_running_workout(id, json) str
    }
    class SwimmingTools {
        +create_swimming_workout(json) str
    }
    class StrengthTools {
        +create_strength_workout(json) str
    }
    class CalendarTools {
        +schedule_workout(id, date) str
        +get_workouts(limit) str
        +delete_workout(id) str
        +get_scheduled_workouts(start, end) str
    }

    FastMCP <-- RunningTools : registers via @mcp.tool()
    FastMCP <-- SwimmingTools : registers via @mcp.tool()
    FastMCP <-- StrengthTools : registers via @mcp.tool()
    FastMCP <-- CalendarTools : registers via @mcp.tool()

    RunningTools --> RunningBuilder : _builder.create / update
    SwimmingTools --> SwimmingBuilder : _builder.create
    StrengthTools --> StrengthBuilder : _builder.create
    CalendarTools --> GarminClient : auth.get_client()
```

---

## Sequence: create workout

```mermaid
sequenceDiagram
    participant Agent as AI Agent
    participant Tool as MCP Tool<br/>(e.g. create_running_workout)
    participant Builder as ConcreteBuilder<br/>(RunningBuilder)
    participant Auth as auth.get_client()
    participant API as Garmin Connect API

    Agent->>Tool: workout_json: str
    Tool->>Tool: json.loads(workout_json)
    alt invalid JSON
        Tool-->>Agent: {"error": "Invalid JSON: ..."}
    end

    Tool->>Builder: _builder.create(spec)
    activate Builder
    Builder->>Builder: build_payload(spec)
    Note right of Builder: pace zone math<br/>step assembly<br/>raw dict output

    Builder->>Auth: get_client()
    Auth-->>Builder: GarminClient (cached singleton)

    Builder->>API: POST /workout-service/workout
    API-->>Builder: {workoutId, workoutName, ...}
    deactivate Builder

    Builder-->>Tool: {workoutId, name}
    Tool-->>Agent: serialize({workoutId, name})
```

---

## Sequence: update workout

```mermaid
sequenceDiagram
    participant Agent as AI Agent
    participant Tool as MCP Tool<br/>(update_running_workout)
    participant Builder as RunningBuilder
    participant Auth as auth.get_client()
    participant API as Garmin Connect API

    Agent->>Tool: workout_id: str, workout_json: str
    Tool->>Tool: json.loads(workout_json)
    alt invalid JSON
        Tool-->>Agent: {"error": "Invalid JSON: ..."}
    end

    Tool->>Builder: _builder.update(workout_id, spec)
    activate Builder
    Builder->>Builder: build_payload(spec)
    Builder->>Builder: payload["workoutId"] = int(workout_id)

    Builder->>Auth: get_client()
    Auth-->>Builder: GarminClient (cached singleton)

    Builder->>API: PUT /workout-service/workout/{id}
    Note right of API: Preserves workoutScheduleId<br/>Calendar scheduling intact
    API-->>Builder: 204 No Content
    deactivate Builder

    Builder-->>Tool: {workoutId, name, updated: true}
    Tool-->>Agent: serialize({workoutId, name, updated: true})
```

---

## Module responsibilities

| File | Responsibility |
|------|---------------|
| `server.py` | Entry point. Imports all tool modules to trigger `@mcp.tool()` registration. |
| `app.py` | FastMCP instance — single shared object across all modules. |
| `auth.py` | `get_client()` singleton — lazily creates and caches the authenticated Garmin client. |
| `utils.py` | `serialize()` — JSON-safe serialization of Garmin API responses. |
| `tools/builder.py` | `WorkoutBuilder` base class + `repeat_group()` shared helper. |
| `tools/running.py` | `RunningBuilder` — pace zone math, distance/time-based step assembly. MCP tools: `create_running_workout`, `update_running_workout`. |
| `tools/swimming.py` | `SwimmingBuilder` — stroke types, pool length, fixed/lap-button rests. MCP tool: `create_swimming_workout`. |
| `tools/strength.py` | `StrengthBuilder` — exercise steps, sets/reps/weight, repeat groups. MCP tool: `create_strength_workout`. |
| `tools/calendar.py` | Sport-agnostic workout CRUD: `schedule_workout`, `get_workouts`, `delete_workout`, `get_scheduled_workouts`. |
| `tools/activities.py` | Activity retrieval and export (GPX, TCX, CSV). |
| `tools/health.py` | Sleep, HRV, body battery, stress, SpO2, heart rate, body composition. |
| `tools/training.py` | Training status, VO2 max, personal records. |
| `tools/plans.py` | `save_plan` — persists agent-generated training plans as JSON to `~/devel/garmin/data/`. |
| `tools/profile.py` | User profile, devices, gear. |

---

## Design patterns

### Template Method — `WorkoutBuilder`

`create()` and `update()` define the algorithm skeleton (parse → build → upload/PUT). Sport-specific subclasses override only `build_payload()` — the part that varies. The upload call, error path, and return format are inherited and never duplicated.

### Strategy — concrete builders

Each builder is a strategy for assembling a `workoutSegments` payload. Swapping the strategy changes the sport without touching the MCP tool registration or the upload logic.

### Decorator — `@mcp.tool()`

FastMCP discovers tools at import time via the decorator. `server.py` imports all tool modules; the side-effect of each import is tool registration. No explicit registry — the framework owns discovery.

### Singleton — `auth.get_client()`

The Garmin client is created once and cached. OAuth tokens are persisted at `~/.garminconnect/`. All tools call `auth.get_client()` directly — no dependency injection, justified by the single-user, single-account nature of the server.

### Module-level instance — `_builder`

Each sport module instantiates its builder once at module load (`_builder = RunningBuilder()`). MCP tool functions close over this instance. Avoids re-instantiation on every call while keeping the builder stateless (all state lives in `spec`).

---

## Key decisions and trade-offs

### Raw dicts over Pydantic models

**Decision:** All workout payloads are plain Python dicts sent directly to `upload_workout(dict)`.

**Why:** The garminconnect typed helpers (`upload_running_workout`, `upload_swimming_workout`) are thin wrappers that call `upload_workout(model.to_dict())`. Bypassing them removes a serialization indirection, makes the payload directly inspectable in tests, and unifies all sports under one upload path.

**Trade-off:** No Pydantic validation on the way out. A malformed field silently produces a Garmin API 400 error instead of a local `ValidationError`. Acceptable because the builder functions are the single source of truth for field names.

### PUT over delete + recreate

**Decision:** `update_running_workout` issues a `PUT /workout-service/workout/{id}` rather than deleting and recreating.

**Why:** Deleting breaks the workout's calendar scheduling (the `workoutScheduleId` reference becomes orphaned). PUT preserves the ID and all scheduled dates — the agent never needs to reschedule after an edit.

### Flat `tools/` over a `tools/workouts/` subpackage

**Decision:** All tool modules live at the same level in `tools/`.

**Why:** With three sport-specific builders, a subpackage adds structural overhead without improving navigability. A fourth sport would revisit this — the `WorkoutBuilder` base is already in place to make that migration trivial.

### `calendar.py` name over `workouts.py`

**Decision:** The CRUD module is named `calendar.py`, not `workouts.py`.

**Why:** `schedule_workout`, `get_workouts`, `delete_workout`, `get_scheduled_workouts` operate on the Garmin calendar, not on workout content. `workouts.py` implied ownership of workout creation, which now belongs to the sport-specific builders.

### Pace zone in m/s, not s/m

**Decision:** `pace.zone` targets use meters-per-second (`targetValueOne`, `targetValueTwo`), where `targetValueOne > targetValueTwo` (faster pace = higher m/s).

**Why:** The Garmin API stores pace zones in m/s regardless of the `min/km` display on the device. Tolerance is applied before conversion: fast bound = `1000 / (total_sec - tol)`, slow bound = `1000 / (total_sec + tol)`.

---

## Pace math reference

```
pace "4:31" = 271 s/km  |  tolerance ±5 s
  fast bound (targetValueOne) = 1000 / 266 ≈ 3.7594 m/s
  slow bound (targetValueTwo) = 1000 / 276 ≈ 3.6232 m/s

E zone "5:26"–"5:59"  (range target, no tolerance)
  fast = 1000 / 326 ≈ 3.0675 m/s
  slow = 1000 / 359 ≈ 2.7855 m/s
```

---

## Running workout spec reference

```
Distance-based (quality sessions):          Time-based (run/walk):
{                                           {
  "name": "Limiar — 3×14' T",               "name": "Run/Walk",
  "warmup_km": 2,                            "warmup_minutes": 5,
  "warmup_pace": ["5:26", "5:59"],           "main_set": [
  "main_set": [{                               {"type": "interval", "minutes": 2},
    "type": "repeat", "repeat": 3,             {"type": "recovery", "minutes": 2}
    "steps": [                               ],
      {"type": "interval",                   "repeat": 7,
       "minutes": 14, "pace": "4:31"},       "cooldown_minutes": 5
      {"type": "recovery", "minutes": 2}    }
    ]
  }],
  "cooldown_km": 1,
  "cooldown_pace": ["5:26", "5:59"],
  "pace_tolerance_sec": 5
}

Easy / long run:
{"name": "Rodagem — 12 km", "main_km": 12, "main_pace": ["5:26", "5:59"]}
```
