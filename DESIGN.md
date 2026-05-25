# Design for Multi-workspace Resource Access Manager API


## Multi-tenancy strategy

The API uses a pooled/shared-schema multi-tenancy approach. All workspaces are stored in the same PostgreSQL database and schema, and tenant isolation is enforced through `workspace_id` columns, composite constraints, and application-layer authorization checks.

This approach was chosen over database-per-tenant or schema-per-tenant isolation because it is simpler to operate for a large number of workspaces:

- Database-per-tenant provides strong isolation, but adds operational overhead for provisioning, migrations, backups, connection management, and monitoring.
- Schema-per-tenant provides moderate isolation, but still requires running and tracking migrations across many schemas.
- Shared-schema tenancy keeps migrations and connection management simple, and works well for many small-to-medium workspaces.

The trade-off is that isolation depends on consistently scoping all workspace-owned data access by `workspace_id`. To reduce cross-workspace leakage risk:

- Every tenant-owned table includes `workspace_id`.
- User email uniqueness is scoped by `(workspace_id, email)`, allowing the same email to exist in multiple workspaces while preventing duplicates inside one workspace.
- Resources and policies are referenced through workspace-scoped composite foreign keys.
- Authenticated requests carry the user's `workspace_id` in the token claims.
- Repository/service queries must filter by the authenticated `workspace_id` when reading or mutating workspace-scoped data.


## DB system (PostgreSQL):


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

- Users sign in using email and password.
- On successful login, the API issues two JWTs:
  - An access token for authenticated API routes.
  - A refresh token for obtaining a new access token without logging in again.
- JWT claims include `user_email`, `workspace_id`, `role`, `token_version`, expiration, and token type. A user identifier should also be included as the subject claim where applicable.
- Passwords are hashed using Argon2 before storage. Plaintext passwords are never stored.
- Token validation happens through middleware.
- Access token expiry is 15 minutes and refresh token expiry is 7 days. Both values are configurable through environment variables.
- After the refresh token expires, the user must log in again.
- Refresh tokens are not stored directly in the database. Instead, token invalidation is handled using the `token_version` stored on the user row.
- If the token version in the JWT does not match the current value in the database, authentication fails.
- If a user logs out, the version is incremented to prevent previously issued access and refresh tokens from being used again.
- When the user logs in again, new tokens are issued with the current token version.
- Currently, logging out is the only action that increments `token_version`.

Token storage expectations:

- API clients send access tokens using the `Authorization: Bearer <token>` header.
- For browser clients, the safest refresh-token storage approach would be an HttpOnly, Secure, SameSite cookie to reduce exposure to XSS. Access tokens should ideally be stored in memory and not in long-lived browser storage.
- For non-browser clients, tokens should be stored using the platform's secure credential storage.
- Tokens must not be logged or exposed in API responses beyond the login/refresh response.

Security considerations:

- JWT signing secrets must be strong and stored in environment variables or a secret manager.
- Access and refresh tokens should include a token type claim so refresh tokens cannot be used on access-token-only routes.
- Production deployments should use HTTPS so tokens are not transmitted in plaintext.
- Short-lived access tokens reduce the impact of access-token theft.
- `token_version` provides coarse-grained revocation for all active sessions of a user.


## Authorization flow

Authorization is enforced in layers so both API permissions and workspace isolation are checked before data is returned or modified.

1. The request includes an access token in the `Authorization` header.
2. Authentication middleware verifies the JWT signature, expiration, token type, and required claims.
3. The middleware loads or validates the user using the token claims, including `workspace_id` and `token_version`.
4. If `token_version` does not match the database value, the request is rejected.
5. Route-level authorization middleware checks role requirements for protected API operations.
6. Admin-only routes require the authenticated user's role to be `admin` in the current workspace.
7. Workspace-scoped service/repository methods query data using the authenticated `workspace_id`, resource ids or policy ids alone are not trusted.
8. For resource access decisions, the policy engine evaluates only policies linked to the requested resource within the authenticated workspace.
9. If the resource does not belong to the authenticated workspace, access is rejected rather than falling back to policy evaluation.


## Role based access to APIs

- Role based access is validated through middleware.
  - Two roles: `admin` and `user`.
  - These roles are per workspace.
  - An admin in one workspace does not automatically have permissions in another workspace.

## Policy validation strategy
Core logic is implemented in `policy_engine.py`
As per requirement the following implementation is necessary:

1. Admin Override: Admins always have access to all resources in their workspace.
2. Policy Order: Policies must be evaluated in priority order, with the highest priority being checked first.
3. First Match: The first matching policy (either "allow" or "deny") determines the outcome.
4. Default Deny: If no policy matches the user or role, access is denied by default.

When user requests a resource policy validation would happen based on this flow assuming auth and workspace checks are cleared:
1. Policies are fetched from DB against the requested resource id and authenticated workspace id through the junction table (`effective_policies`).
2. The policies fetched are sorted by priority in descending order.
3. Each policy is checked to determine whether it matches the authenticated user:
   - If `target_type = 'user'`, the policy matches only when `target_value` equals the authenticated user's UUID.
   - If `target_type = 'role'`, the policy matches only when `target_value` equals the authenticated user's role.
4. The first matching policy determines the outcome:
   - `ALLOW` grants access.
   - `DENY` rejects access.
5. If no policy matches, access is denied by default.
6. Admin users bypass policy evaluation for resources inside their own workspace.

If two policies have the same priority, the ordering should be deterministic, for example by `created_at` or `id`. This should be enforced in the query to avoid inconsistent first-match results.

Policy rows are workspace-scoped and are linked to resources through `effective_policies`. Deleting a resource cascades to its effective policy links. The policy deletion behavior in application code removes the policy only when no remaining effective policy links exist for that policy in the workspace.


## Security measures
- SQL injection is mitigated by using SQLAlchemy ORM queries instead of string-concatenated SQL.
- Passwords are hashed using Argon2 before storage. Plaintext passwords are never stored.
- JWTs are signed and include expiration claims. Access tokens are intentionally short-lived.
- Refresh/access token invalidation is supported through `token_version`.
- When a user logs out, all access and refresh tokens for that user are invalidated by incrementing the token version stored in the database.
  - Future requests require the token's version to match the current database value, otherwise authentication fails.
- Workspace isolation is enforced by requiring `workspace_id` in tenant-scoped tables and queries.
- Workspace-scoped composite foreign keys prevent linking a policy from one workspace to a resource in another workspace.
- Admin-only routes are protected through role middleware.
- Sensitive fields such as `password_hash` should not be returned in API responses.
- Default-deny policy evaluation prevents accidental access when no matching policy exists.
- Production deployments should use HTTPS and secure secret management for JWT signing keys.
- Role changes and privileged operations should be restricted to admins to avoid privilege escalation.


## Trade-offs
I made the following trade-offs to keep the implementation focused and achievable within the assignment timeline:

- Shared-schema tenancy was chosen for simplicity and speed. This reduces operational complexity, but it means every query must be carefully scoped by `workspace_id`.
- Refresh tokens are handled with stateless JWTs plus `token_version` instead of storing individual refresh-token sessions. This is simpler, but logging out from one device invalidates all active sessions for that user.
- Per-device logout is not supported yet. With more time, I would store refresh-token/session records per device and support both single-device logout and logout from all devices.
- The app is kept monolithic. This is easier to develop and deploy for the assignment, but auth, policy evaluation, and resource management scale together.
- Policy priority ties need deterministic ordering. With more time, I would enforce a secondary order or prevent conflicting same-priority policies through constraints/validation.


## Scalability Considerations
- FastAPI is used in an asynchronous fashion to improve concurrency, allowing multiple I/O-bound requests to be handled efficiently.
- The shared-schema model scales well for many small-to-medium workspaces because migrations and connection management remain simple.
- The first likely bottleneck would be database load, especially policy evaluation queries that join `effective_policies` and `policies`.
- Large workspaces with many resources and policies could make policy evaluation slower unless the relevant composite indexes are present.
- If every authenticated request checks `token_version` against the database, user lookup/auth validation can become a hot path.
- The monolithic architecture means all API areas scale together. If one part of the app has high load or crashes, it can affect the whole service.
- List endpoints should use pagination to avoid returning large workspace datasets in a single response.

To improve scalability, I would add:

- Composite indexes for workspace/resource/policy lookups.
- Caching for policy evaluation results where safe.
- Short-TTL caching for user/token-version checks.
- Read replicas for read-heavy workloads.
- Horizontal scaling behind a load balancer.
- Database partitioning by `workspace_id` or hash partitioning if tables become very large.
- Background workers for expensive or non-request-critical operations.


## Known limitations

- Per-device logout is not supported. Logging out increments `token_version`, which invalidates all active tokens for that user.
- Refresh tokens are not stored individually, so suspicious sessions cannot be revoked one at a time.
- Tenant isolation depends on application-layer checks and schema constraints.
- Policy evaluation may become slow for resources with many linked policies unless properly indexed or cached.
- The monolithic architecture means a failure in one area can affect the entire API.
- Token invalidation is coarse-grained at the user level rather than session/device level.
