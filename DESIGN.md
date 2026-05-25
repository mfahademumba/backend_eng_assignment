# Design for Multi-workspace Resource Access Manager API


## DB system (PostgreSQL):

- The multi-workspace aspect of resource management is handled using a pooled approach, i.e. all workspaces are part of the same database and schema.
  - This approach is chosen so that a large number of workspaces can be handled in a straightforward way.
    - Multiple schemas would require multiple migrations to run.
    - This would be inconvenient to manage for a large number of workspaces.
    - Therefore, the workspaces will be part of the same schema.
  - For isolation of workspaces and relevant users in the database, email and workspace are protected with a composite unique constraint.
  - Cross-workspace data leakage is prevented in the infrastructure layer. Here, workspace_id is a necessary requirement to check whether resources can be accessed.


## Schema Design

- Policies and resources have a many-to-many relationship through the `effective_policies` junction table.
- Policies are workspace-scoped, not directly resource-scoped. A policy is associated with one or more resources through `effective_policies`.
- A unique composite constraint is placed on `users.workspace_id` and `users.email` to ensure that within one workspace there are no duplicate emails, while allowing the same email in different workspaces.
- Every table besides `workspaces` has `workspace_id` so data can be scoped to a workspace.
- Workspace-scoped composite foreign keys are used where resource/policy links must be constrained to the same workspace.

**Workspaces**

| Field Name  | Type                     | Nullable | Constraints/Notes | Default Value       |
| :---------: | :----------------------: | :------: | :---------------: | :-----------------: |
| id          | UUID                     | No       | Primary Key       | gen\_random\_uuid() |
| name        | VARCHAR(255)             | No       | Unique            |                     |
| created\_at | TIMESTAMP WITH TIME ZONE | No       |                   | NOW()               |
| updated\_at | TIMESTAMP WITH TIME ZONE | No       | Updated by ORM on update | NOW()         |

**Users**

| Field Name     | Type                     | Nullable | Constraints/Notes                                              | Default Value       |
| :------------: | :----------------------: | :------: | :------------------------------------------------------------: | :-----------------: |
| id             | UUID                     | No       | Primary Key                                                    | gen\_random\_uuid() |
| workspace\_id  | UUID                     | No       | Foreign Key to Workspaces(id), ON DELETE CASCADE; Composite Unique Key with email |                     |
| email          | VARCHAR(255)             | No       | Composite Unique Key with workspace\_id                        |                     |
| full\_name     | VARCHAR(255)             | Yes      | Display name for the user                                      |                     |
| password\_hash | VARCHAR(255)             | No       | Hashed password                                                |                     |
| role           | ENUM('ADMIN', 'USER')    | No       | Python values are `admin` / `user`                             | 'USER'              |
| token\_version | INT                      | No       | Used to invalidate existing tokens                             | 0                   |
| created\_at    | TIMESTAMP WITH TIME ZONE | No       |                                                                | NOW()               |
| updated\_at    | TIMESTAMP WITH TIME ZONE | No       | Updated by ORM on update                                       | NOW()               |

Additional notes:

- A user email must be unique within a workspace.
- Users can be looked up efficiently by workspace and user id.

**Policies**

| Field Name    | Type                     | Nullable | Constraints/Notes                                                                 | Default Value       |
| :-----------: | :----------------------: | :------: | :-------------------------------------------------------------------------------: | :-----------------: |
| id            | UUID                     | No       | Primary Key; Composite Unique Key with workspace\_id                              | gen\_random\_uuid() |
| workspace\_id | UUID                     | No       | Foreign Key to Workspaces(id), ON DELETE CASCADE; Composite Unique Key with id    |                     |
| name          | VARCHAR(255)             | No       |                                                                                   |                     |
| effect        | ENUM('ALLOW', 'DENY')    | No       | Python values are `allow` / `deny`                                                |                     |
| target\_type  | Text                     | No       | Check constraint: must be `role` or `user`                                        |                     |
| target\_value | Text                     | No       | For `role`, stores role value; for `user`, stores user UUID as text               |                     |
| priority      | Integer                  | No       | Check constraint: priority > 0                                                    |                     |
| created\_at   | TIMESTAMP WITH TIME ZONE | No       |                                                                                   | NOW()               |
| updated\_at   | TIMESTAMP WITH TIME ZONE | No       | Updated by ORM on update                                                          | NOW()               |

Additional notes:

- Policy priority must always be greater than zero.
- Policy targets can only be a role or a specific user.
- A policy id is guaranteed to belong to only one workspace when referenced together with `workspace_id`.
- Policies can be queried efficiently by workspace and priority.


**Resources**

| Field Name    | Type                     | Nullable | Constraints/Notes                                  | Default Value       |
| :-----------: | :----------------------: | :------: | :------------------------------------------------: | :-----------------: |
| id            | UUID                     | No       | Primary Key; Composite Unique Key with workspace\_id | gen\_random\_uuid() |
| workspace\_id | UUID                     | No       | Foreign Key to Workspaces(id), ON DELETE CASCADE; Composite Unique Key with id |                     |
| name          | VARCHAR(255)             | No       |                                                    |                     |
| type          | VARCHAR(255)             | No       | Check constraint: must be one of `document`, `database`, `service`, `api`, `file` |                     |
| status        | VARCHAR(255)             | No       |                                                    |                     |
| description   | Text                     | Yes      |                                                    |                     |
| created\_at   | TIMESTAMP WITH TIME ZONE | No       |                                                    | NOW()               |
| updated\_at   | TIMESTAMP WITH TIME ZONE | No       | Updated by ORM on update                           | NOW()               |

Additional notes:

- Resource type must be one of: `document`, `database`, `service`, `api`, or `file`.
- A resource id is guaranteed to belong to only one workspace when referenced together with `workspace_id`.
- Resources can be queried efficiently by workspace.

**Effective policies**

| Field Name    | Type                     | Nullable | Constraints/Notes                                                              | Default Value       |
| :-----------: | :----------------------: | :------: | :----------------------------------------------------------------------------: | :-----------------: |
| id            | UUID                     | No       | Primary Key                                                                    | gen\_random\_uuid() |
| workspace\_id | UUID                     | No       | Foreign Key to Workspaces(id), ON DELETE CASCADE                               |                     |
| resource\_id  | UUID                     | No       | Composite Foreign Key with workspace\_id to Resources(id, workspace\_id), ON DELETE CASCADE |                     |
| policies\_id  | UUID                     | No       | Composite Foreign Key with workspace\_id to Policies(id, workspace\_id), ON DELETE CASCADE |                     |
| created\_at   | TIMESTAMP WITH TIME ZONE | No       |                                                                                | NOW()               |
| updated\_at   | TIMESTAMP WITH TIME ZONE | No       | Updated by ORM on update                                                       | NOW()               |

Additional notes:

- The same policy cannot be linked to the same resource more than once.
- Effective policies can be queried efficiently by workspace and resource.


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
- Access token expiry would be 15 minutes whereas refresh token expiry would be 7 days (both expiries being configurable through environment variables)
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
Core logic is implemented in `policy_engine.py`
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

Policy rows are workspace-scoped and are linked to resources through `effective_policies`. Deleting a resource cascades to its effective policy links. The policy deletion behavior in application code removes the policy only when no remaining effective policy links exist for that policy in the workspace.


## Security measures
- To prevent SQL injection, ORM is used for interacting with the DB (SQLAlchemy in particular)
- Passwords are hashed before storage in DB
- When user logs out, all access and refresh tokens are invalidated by using a token versioning system. On logout the token version stored in the DB is incremented.
  - All following login attempts require the token to have this new token version otherwise they are invalid.


## Tradeoffs
I would do the following if I had more time:
- Currently logging out of one device logs out all users. I would implement a system where user can securely log out of one device at a time.
- Adding a logout of all devices feature separately.


## Scaleability Considerations
- FastAPI is used in an asynchronous fashion to improve concurrency allowing multiple requests to be handled at the same time.
- Currently monolithic architecture is used for the app. If something crashes, the entire service goes down.
