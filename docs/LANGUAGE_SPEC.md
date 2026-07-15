# Quinny Language Specification — v0.1

Quinny is an **executable specification language**. A Quinny program is not code
that runs; it is a **structured description of what a piece of software must do** —
its components and their acceptance criteria. Its primary use is `quinny verify`,
which compiles the `test`/`success` criteria into a test suite and checks any
implementation against them. (`task`/`component`/`depends`/`uses` organize the
spec and were originally used to drive code generation, now experimental.)

## 1. Philosophy

Existing languages describe **how** to compute. Quinny describes **what** must
be true when the work is done. It has **no loops, no variables, no control
flow** — those belong to the target language the agent emits.

A Quinny program is one serialization of a **task graph**. Every node in the
graph carries at minimum:

- a **goal** (what "done" means in prose)
- optional **inputs** and **outputs**
- optional **constraints** (engineering boundaries)
- optional **dependencies** (edges to other tasks)
- optional **tests** and **success criteria** (verification)

## 2. Reserved keywords (v0.1)

```
project    task       component
goal       input      output
constraint depends    uses
test       success
```

Ten keywords. That's the entire surface area of v0.1.

## 3. Syntax

Quinny is **indentation-sensitive**, like Python. One declaration per line;
fields are indented one level (4 spaces) under their owner; field content is
indented one level under the field keyword.

```
project MyApp

task Login
    goal
        Authenticate users securely.
    input
        email
        password
    output
        jwt_token
    constraint
        Under 200ms latency.
        Support OAuth.
    depends
        Database
    test
        Reject invalid passwords.
    success
        User reaches feed.
```

### 3.1 Comments

`#` starts a line comment.

```
# Retry policy defined in the platform spec.
constraint
    Retry failures 3 times.
```

### 3.2 Blank lines

Blank lines are ignored. They exist for humans.

## 4. Declarations

### 4.1 `project`

Every file starts with exactly one project declaration.

```
project <Name>
```

The name is a `CamelCase` identifier. It labels the root of the task graph.

### 4.2 `task`

A unit of engineering work.

```
task <Name>
    <field>+
```

Task names are unique within a project.

### 4.3 `component`

An architectural building block (a service, module, screen). Same field
grammar as `task`, plus a `uses` field for architectural composition.

```
component AuthService
    goal
        Issue and verify JWTs.
    uses
        Postgres
        Redis
```

## 5. Fields

Every field is a keyword followed by an **indented block** of content lines.

### 5.1 Prose fields

`goal`, `constraint`, `test`, `success` take free-text lines. Each line is
one statement.

```
constraint
    No third-party analytics SDKs.
    Bundle size under 5MB.
```

### 5.2 Identifier fields

`input`, `output`, `depends`, `uses` take one identifier per line. These are
edges in the graph.

```
depends
    Database
    AuthService
```

## 6. Semantics

- A **task graph** is built from the file. Nodes are `task` and `component`
  declarations. Edges come from `depends` and `uses`.
- A `depends` or `uses` target must resolve to a declared name in the same
  project. Unresolved names are a semantic error.
- The graph must be a **DAG**. Cycles are a semantic error.
- `goal` is **required** on every task and component.
- All other fields are optional but strongly recommended.

## 7. Non-goals for v0.1

The following are explicitly out of scope and will be considered for later
versions:

- Cross-file imports / namespaces
- Parameterized / templated tasks
- Priorities, deadlines, budgets
- Runtime values, expressions, functions
- Multiple projects per file

Keeping the core small is the point. Everything an AI agent needs to *plan*
must be expressible in v0.1. Everything else waits.
