# Work IQ verification status

The Work IQ provider is implemented and permission-verified.

A dedicated Entra app was created and the token contained the required delegated Microsoft Graph scopes: `User.Read`, `Files.Read.All`, and `Sites.Read.All`.

A live Microsoft Graph Copilot Retrieval API call was attempted against SharePoint content. Microsoft Graph accepted the token/scopes but returned:

```text
Authorization Failed - User does not have valid license
```

This repo does not claim completed Work IQ tenant retrieval. It claims the Work IQ path is implemented, guarded, permission-verified, and fail-closed until the tenant has the required Retrieval API entitlement.
