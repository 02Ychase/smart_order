# Auth and Address Persistence Design

**Date:** 2026-04-22
**Scope:** Complete the existing auth and address management flow so registration persists users to the database, login validates against stored users, and authenticated users can manage multiple saved addresses and immediately receive their saved address list after register/login.

## Goal

Turn the current partial auth and address scaffolding into a working persistence-backed user session flow. A user should be able to register with a unique `username`, be stored in the `users` table, automatically receive a logged-in session after registration, sign in later using the same persisted credentials, and see the addresses they previously saved in the database.

## Confirmed Product Decisions

1. `username` remains the login identifier. Phone stays as profile data, not the primary credential.
2. Registration should automatically log the user in rather than forcing a second explicit login call.
3. `POST /auth/register` and `POST /auth/login` should both return the same session-oriented payload.
4. That session payload should contain:
   - `access_token`
   - `refresh_token`
   - `user`
   - `addresses`
5. Users should still manage addresses through the existing `/addresses` endpoints after login.
6. Each user can store multiple addresses. Each address must persist its phone number and coordinates.

## Existing State

The current codebase already contains most of the building blocks, but the product flow is incomplete.

- `api/routes/auth.py` already exposes `/auth/register`, `/auth/login`, `/auth/refresh`, and `/auth/me`.
- `service/auth_service.py` already hashes passwords on registration, verifies stored hashes on login, and issues access/refresh tokens.
- `repository/user_repository.py` already persists users to `users` and supports CRUD-style operations for `user_addresses`.
- `api/models/user.py` already defines `User` and `UserAddress` with persisted fields for `contact_phone`, `longitude`, `latitude`, and multi-address ownership through `user_id`.
- `api/routes/address.py` and `service/user_profile_service.py` already expose authenticated address listing, creation, update, deletion, and default-address switching.

The main gap is not missing storage primitives; it is that auth responses are still too narrow for the intended product behavior. The current auth responses return either basic user info or token pairs, but not a full session payload that lets the client immediately hydrate the logged-in experience with the user’s saved addresses.

## Recommended Approach

Keep the existing auth and address architecture, and close the gap by introducing a unified session response at the auth boundary.

This means:
- preserving the current `auth` and `addresses` route split,
- preserving database-backed credential validation,
- preserving the existing `User` and `UserAddress` models,
- expanding auth response schemas so registration and login both return the user’s current session state,
- reusing the existing address repository/service path rather than inventing a second address-loading mechanism.

This is the best fit because the codebase already has the right table structure and service boundaries. A minimal architectural change can deliver the requested product behavior without creating redundant session endpoints or duplicating address logic.

## Alternatives Considered

### Option A — Recommended: Expand auth responses into a session payload
- Keep existing route structure.
- Add a new schema that combines tokens, current user data, and the user’s address list.
- Make both register and login return this unified shape.

**Why recommended:** smallest change that fully matches the requested UX and current architecture.

### Option B — Keep auth responses minimal and let frontend fetch addresses separately
- Register/login would keep returning only user info or token pairs.
- Client would call `/addresses` after authentication.

**Tradeoff:** cleaner separation, but it explicitly does not match the confirmed product choice that login should immediately return saved addresses.

### Option C — Add a separate session bootstrap endpoint
- Keep register/login mostly unchanged.
- Add a new `/auth/session` or similar endpoint that returns tokens, user, and addresses.

**Tradeoff:** works technically, but adds another endpoint and extra client choreography without solving a real complexity problem in this codebase.

## Design

### 1. Authentication model and behavior

Authentication will continue to use `username` plus password.

Registration behavior:
- Validate that the requested `username` does not already exist.
- Hash the submitted password.
- Persist a new user row to `users`.
- Immediately issue access and refresh tokens for that newly created user.
- Load the user’s saved addresses from the database (initially an empty list).
- Return a unified session response.

Login behavior:
- Load the user by `username`.
- Verify the submitted password against the stored `password_hash`.
- On success, issue access and refresh tokens.
- Load that user’s saved addresses from the database.
- Return the same unified session response used by registration.

Refresh behavior can remain token-only unless the existing consumer flow requires otherwise. This iteration does not require changing refresh into a full session bootstrap response.

### 2. Session response schema

The current response split between `CurrentUserResponse` and `TokenPairResponse` is too narrow for the desired behavior.

Introduce a session-oriented response schema that contains:
- `access_token: str`
- `refresh_token: str`
- `user: CurrentUserResponse`
- `addresses: list[AddressResponse]`

Planned endpoint contracts:
- `POST /auth/register` → session response
- `POST /auth/login` → session response
- `POST /auth/refresh` → existing token refresh response can stay as-is
- `GET /auth/me` → current user response can stay as-is

This keeps the API easy to reason about:
- auth bootstrap endpoints return everything the client needs to render the signed-in state,
- identity-check endpoint stays lightweight,
- address management endpoints continue to own address mutation.

### 3. Address management model

Each `User` may own multiple `UserAddress` records.

Persisted address fields remain:
- `label`
- `contact_name`
- `contact_phone`
- `city`
- `district`
- `detail_address`
- `longitude`
- `latitude`
- `is_default`

The current route structure is already correct and should be preserved:
- `GET /addresses`
- `POST /addresses`
- `PUT /addresses/{address_id}`
- `POST /addresses/{address_id}/default`
- `DELETE /addresses/{address_id}`

The required behavior is:
- an authenticated user can create multiple addresses,
- listing returns only that user’s addresses,
- default switching only affects that user’s own addresses,
- update/delete can only affect that user’s own addresses,
- login/register session payloads should reflect what is currently stored for that user.

### 4. Service and repository boundaries

No new subsystem is needed.

Recommended responsibilities:
- `UserRepository`
  - remains the persistence layer for `User` and `UserAddress`
  - continues to own `get_by_username`, `create_user`, `list_addresses`, and address mutations
- `UserProfileService`
  - remains the address-focused serializer/service for `/addresses`
- `AuthService`
  - gains responsibility for composing the new session response
  - should reuse `UserRepository.list_addresses(...)` or a small internal serializer helper so auth responses and address responses stay structurally aligned

The important design rule is to avoid duplicating business rules in routes. Routes should remain thin wrappers around service methods.

### 5. Error handling

Required error behavior:
- duplicate username on registration → `409 Conflict`
- invalid username/password on login → `401 Unauthorized`
- invalid refresh token → keep current `401 Unauthorized`
- authenticated request for a missing/non-owned address on update/delete/default switch → `404 Not Found`
- unauthenticated access to `/addresses` → `401 Unauthorized`

Address ownership checks must stay user-scoped at the repository/service boundary so one user cannot read or mutate another user’s address records.

### 6. Testing and verification

This work should be verified against the real test database flow, not only mocks, because the user explicitly wants registration/login/address persistence to truly read and write stored data.

Required auth coverage:
- registration persists a new user row in the database,
- duplicate username registration returns `409`,
- login validates against stored password hashes,
- invalid login returns `401`,
- successful registration returns a session response with empty `addresses`,
- successful login returns a session response with the user’s previously saved addresses,
- `/auth/me` still resolves the authenticated user correctly.

Required address coverage:
- authenticated user can create multiple addresses,
- created addresses are visible on later `GET /addresses`,
- default address switching reorders/default-flags correctly,
- one user cannot see another user’s addresses,
- after creating addresses, a later login returns those addresses in the auth session payload,
- unauthenticated address access is rejected.

Manual verification after implementation:
- register a new user,
- confirm login works with the same stored credentials,
- create multiple addresses including coordinates and phone numbers,
- log out and log back in,
- confirm the returned auth payload already includes the previously stored addresses.

## Non-Goals

- No switch to phone-number-based authentication.
- No OAuth, SMS verification, captcha, or email verification.
- No profile editing workflow beyond existing stored fields.
- No redesign of token format or auth middleware.
- No address geocoding service; longitude/latitude are accepted as client-provided values.

## Risks and Mitigations

- **Risk: auth and address serializers drift apart.**  
  Mitigation: keep one canonical address response shape and reuse it when composing auth session responses.

- **Risk: registration/login appear to work but do not verify true persistence.**  
  Mitigation: use database-backed API tests that assert rows exist and can be reloaded across requests.

- **Risk: address ownership bugs expose other users’ data.**  
  Mitigation: keep every address lookup scoped by `user_id` and cover cross-user access in tests.

- **Risk: refresh semantics become inconsistent with the richer auth responses.**  
  Mitigation: explicitly keep refresh as token-only in this iteration unless a concrete consumer need appears.
