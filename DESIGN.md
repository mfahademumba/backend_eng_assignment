# Design for Multi-workspace Resource Access Manager API

The repo will follow layered architecture.

## Tech stack:
- FastAPI
- uvicorn
- PostgreSQL DB
- SQLAlchemy ORM
- Alembic (for handling migrations)
- Pytest (for testing)

## DB system (PostgreSQL):

- Mult-workspace aspect for resoruce management is to be handled using pool based approach i.e. all workspaces will be part of same DB and schema.
  - This approach is chosen so that a large number of workspaces can be handled in a straght forward way.
    - Multiple schemas would required multiple migrations to run.
    - Inconvenient to manage for large number of workspaces
    - Therefore, the workspaces will be part of the same schema.
  - For isolation of workspaces and relevant users in DB, the email and the workspace with a composite unique constraint.
  - Cross workspace data leakage would be enforced in the infrastructure layer. Here, workspace_id will be a necessary requirement to check if resources can be accessed or not.


## Schema Design

**Workspaces**

| Field Name  | Type                     | Nullable | Constraints/Notes | Default Value       |
| :---------: | :----------------------: | :------: | :---------------: | :-----------------: |
| id          | UUID                     | No       | Primary Key       | gen\_random\_uuid() |
| name        | VARCHAR(255)             | No       | Unique            |                     |
| created\_at | TIMESTAMP WITH TIME ZONE | No       |                   | NOW()               |
| updated\_at | TIMESTAMP WITH TIME ZONE | No       |                   | NOW()               |

**Users**

| Field Name    | Type                     | Nullable | Constraints/Notes                                              | Default Value       |
| :-----------: | :----------------------: | :------: | :------------------------------------------------------------: | :-----------------: |
| id            | UUID                     | No       | Primary Key                                                    | gen\_random\_uuid() |
| workspace\_id | UUID                     | No       | Foreign Key to Workspaces(id), Composite Unique Key with email |                     |
| email         | VARCHAR(255)             | No       | Composite Unique Key with workspace\_id                        |                     |
| full\_name    | VARCHAR(255)             | Yes      | Display name for the user                                      |                     |
| role          | ENUM('admin', 'user')    | No       |                                                                | 'user'              |
| token\_version | INT                      | No      |                                                                |          0           |
| created\_at   | TIMESTAMP WITH TIME ZONE | No       |                                                                | NOW()               |
| updated\_at   | TIMESTAMP WITH TIME ZONE | No       |                                                                | NOW()               |

**Policies**

| Field Name    | Type                     | Nullable | Constraints/Notes                                                                 | Default Value       |
| :-----------: | :----------------------: | :------: | :-------------------------------------------------------------------------------: | :-----------------: |
| id            | UUID                     | No       | Primary Key                                                                       | gen\_random\_uuid() |
| workspace\_id | UUID                     | No       | Foreign Key to Workspaces(id), Composite Unique Key with id                       |                     |
| resource\_id  | UUID                     | No       | Composite Foreign Key with workspace\_id to Resources(id, workspace\_id), ON DELETE CASCADE |                     |
| name          | VARCHAR(255)             | No       |                                                                                   |                     |
| effect        | ENUM('allow', 'deny')    | No       |                                                                                   |                     |
| target\_type  | Text                     | No       |                                                                                   |                     |
| target\_value | Text                     | No       |                                                                                   |                     |
| priority      | Positive Integer         | No       | Check constraint: priority > 0                                                    |                     |
| created\_at   | TIMESTAMP WITH TIME ZONE | No       |                                                                                   | NOW()               |
| updated\_at   | TIMESTAMP WITH TIME ZONE | No       |                                                                                   | NOW()               |

**Resources**

| Field Name    | Type                     | Nullable | Constraints/Notes                                  | Default Value       |
| :-----------: | :----------------------: | :------: | :------------------------------------------------: | :-----------------: |
| id            | UUID                     | No       | Primary Key, Composite Unique Key with workspace\_id | gen\_random\_uuid() |
| workspace\_id | UUID                     | No       | Foreign Key to Workspaces(id), Composite Unique Key with id |                     |
| name          | VARCHAR(255)             | No       |                                                    |                     |
| type          | VARCHAR(255)             | No       |                                                    |                     |
| status        | VARCHAR(255)             | No       |                                                    |                     |
| description   | Text                     | Yes      |                                                    |                     |
| created\_at   | TIMESTAMP WITH TIME ZONE | No       |                                                    | NOW()               |
| updated\_at   | TIMESTAMP WITH TIME ZONE | No       |                                                    | NOW()               |

**Effective policies**

| Field Name    | Type                     | Nullable | Constraints/Notes                                                              | Default Value       |
| :-----------: | :----------------------: | :------: | :----------------------------------------------------------------------------: | :-----------------: |
| id            | UUID                     | No       | Primary Key                                                                    | gen\_random\_uuid() |
| workspace\_id | UUID                     | No       | Foreign Key to Workspaces(id), ON DELETE CASCADE                               |                     |
| resource\_id  | UUID                     | No       | Composite Foreign Key with workspace\_id to Resources(id, workspace\_id), ON DELETE CASCADE |                     |
| policies\_id  | UUID                     | No       | Composite Foreign Key with workspace\_id to Policies(id, workspace\_id), ON DELETE CASCADE |                     |
| created\_at   | TIMESTAMP WITH TIME ZONE | No       |                                                                                | NOW()               |
| updated\_at   | TIMESTAMP WITH TIME ZONE | No       |                                                                                | NOW()               |


## Logs
- Logs will follow consistent easy to read pattern
- API call logs will be handled through mdidleware


## Auth system

- Users will signin using email and passwords
- They will received access token and refresh token for login
- They will need to have access token for authenticated routes
- JWT claim would include user_email, workspace_id, role, token_version
- Passwords will be hashed using bcrypt
- Validation will happen through middleware approach
- Access token expiry would be 15 minutes whereas refresh token expiry would be 7 days
- After refresh token expires, user will have to login again
- If token version does not match the one in the DB, auth fails
- If user logs out the version is incremented to disallow the same token to be used again.
- When user logs in again they receive a token based on the current token version.
- Currently logging out is the only way token version would be incremented.


## Role based access to APIs

- Role based access will be validated through middleware approach
  - Two roles: 'admin' and 'user'
  - These roles are per workspace

## Policy validation strategy
Core logic will be implemented in policy_engin.py
As per requirement the following implementation is necessary:

1. Admin Override: Admins always have access to all resources in their workspace.
2. Policy Order: Policies must be evaluated in priority order, with the highest priority being checked first.
3. First Match: The first matching policy (either "allow" or "deny") determines the outcome.
4. Default Deny: If no policy matches the user or role, access is denied by default.

When user requests a resource policy validation would happen based on this flow assuming auth and workspace checks are cleared:
1. Policies are fetched from DB against the resource id requested going through the junction table (Effective Policies).
2. The policies fetched will be sorted in descending order when queried for.
3. Outcome determined from first available policy either allowed or denied.
4. Default would be denied against user role considering admins can access all resources.

Policy rows are resource-scoped through `policies.resource_id`. Deleting a resource cascades to its policies and effective policy links at the database level.
