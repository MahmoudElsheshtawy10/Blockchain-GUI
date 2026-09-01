# Sprint 1 — Authentication + Users + Roles + Permissions (Enterprise Edition)

> [!NOTE]
> This plan covers **Sprint 1 only**. All 12 enterprise improvements are integrated.

---

## Current State

| Aspect | Current |
|---|---|
| Framework | ASP.NET Core MVC (.NET 10), EF Core 10 |
| Auth | None — custom `User`, `Role`, `UserRole` models, no login flow |
| DbContext | `AppDbContext : DbContext` |
| Controllers | 11 controllers, all unprotected |
| Services Layer | None — controllers talk directly to `AppDbContext` |
| Employee | Standalone entity, no user link |

---

## Strategy

**Extend, don't replace.** We will:
1. Add Identity alongside the existing models (staged migration — old tables stay)
2. Link `Employee` ↔ `ApplicationUser` (one-to-one)
3. Build a service layer with proper DI
4. Cache permissions in-memory with targeted invalidation
5. Track login history and active sessions
6. Prepare audit log interfaces for Sprint 2

---

## Proposed Changes

### Component 1 — NuGet Package

#### [MODIFY] [Smart Inventory System.csproj](file:///c:/Users/641578/source/repos/Smart%20Inventory%20System/Smart%20Inventory%20System/Smart%20Inventory%20System.csproj)
```xml
<PackageReference Include="Microsoft.AspNetCore.Identity.EntityFrameworkCore" Version="10.0.7" />
```

---

### Component 2 — Enums

#### [NEW] `Models/Enums/UserStatus.cs`
Replaces the boolean `IsActive` flag (#7):
```csharp
public enum UserStatus
{
    Pending = 0,
    Active = 1,
    Locked = 2,
    Disabled = 3,
    Archived = 4
}
```

#### [NEW] `Models/Enums/LoginResult.cs`
```csharp
public enum LoginResult
{
    Success,
    Failed,
    LockedOut,
    Disabled,
    Archived,
    NotFound
}
```

---

### Component 3 — Identity Models

#### [NEW] `Models/ApplicationUser.cs`
Extends `IdentityUser` with enterprise fields:
```csharp
public class ApplicationUser : IdentityUser
{
    [Required, StringLength(200)]
    public string FullName { get; set; }
    public string? ProfileImagePath { get; set; }
    public UserStatus Status { get; set; } = UserStatus.Active;
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public DateTime? LastLogin { get; set; }
    public int? CompanyId { get; set; }        // Future multi-tenant
    public int? EmployeeId { get; set; }       // Link to Employee (#2)
    public Employee? Employee { get; set; }
    public UserPreference? Preferences { get; set; }
    public ICollection<LoginHistory> LoginHistories { get; set; }
    public ICollection<UserSession> Sessions { get; set; }
}
```

#### [NEW] `Models/ApplicationRole.cs`
```csharp
public class ApplicationRole : IdentityRole
{
    [StringLength(500)]
    public string? Description { get; set; }
    public bool IsSystemRole { get; set; }
    public ICollection<RolePermission> RolePermissions { get; set; }
}
```

#### [NEW] `Models/Permission.cs`
```csharp
public class Permission
{
    public int PermissionId { get; set; }
    [Required, StringLength(100)]
    public string Key { get; set; }           // "Products.View"
    [Required, StringLength(100)]
    public string GroupName { get; set; }      // "Products"
    [Required, StringLength(200)]
    public string DisplayName { get; set; }    // "View Products"
    public ICollection<RolePermission> RolePermissions { get; set; }
}
```

#### [NEW] `Models/RolePermission.cs`
Composite PK `(RoleId, PermissionId)`:
```csharp
public class RolePermission
{
    public string RoleId { get; set; }
    public ApplicationRole Role { get; set; }
    public int PermissionId { get; set; }
    public Permission Permission { get; set; }
}
```

---

### Component 4 — Login History & Sessions (#5, #6)

#### [NEW] `Models/LoginHistory.cs`
```csharp
public class LoginHistory
{
    public long LoginHistoryId { get; set; }
    public string UserId { get; set; }
    public ApplicationUser User { get; set; }
    public DateTime LoginTime { get; set; }
    public DateTime? LogoutTime { get; set; }
    public string? IpAddress { get; set; }
    public string? Browser { get; set; }
    public string? Device { get; set; }
    public string? OperatingSystem { get; set; }
    public LoginResult Result { get; set; }
}
```

#### [NEW] `Models/UserSession.cs`
```csharp
public class UserSession
{
    public string UserSessionId { get; set; } = Guid.NewGuid().ToString();
    public string UserId { get; set; }
    public ApplicationUser User { get; set; }
    public string SessionToken { get; set; }    // Maps to auth cookie
    public DateTime StartedAt { get; set; }
    public DateTime? LastActivity { get; set; }
    public DateTime? TerminatedAt { get; set; }
    public bool IsActive { get; set; } = true;
    public string? IpAddress { get; set; }
    public string? Browser { get; set; }
    public string? Device { get; set; }
    public string? TerminatedBy { get; set; }   // Admin who terminated
}
```

---

### Component 5 — User Preferences (#8)

#### [NEW] `Models/UserPreference.cs`
```csharp
public class UserPreference
{
    public int UserPreferenceId { get; set; }
    public string UserId { get; set; }
    public ApplicationUser User { get; set; }
    public string Theme { get; set; } = "light";
    public string Language { get; set; } = "en";
    public bool SidebarCollapsed { get; set; } = false;
    public int TablePageSize { get; set; } = 25;
    public bool NotifyLowStock { get; set; } = true;
    public bool NotifyNewOrders { get; set; } = true;
    public bool NotifySystemAlerts { get; set; } = true;
}
```

---

### Component 6 — Employee Link (#2)

#### [MODIFY] [Employee.cs](file:///c:/Users/641578/source/repos/Smart%20Inventory%20System/Smart%20Inventory%20System/Models/Employee.cs)
Add navigation property (Employee stays unchanged otherwise):
```csharp
// Add at end of class:
public string? ApplicationUserId { get; set; }
public ApplicationUser? ApplicationUser { get; set; }
```

#### Old User/Role/UserRole tables
> [!IMPORTANT]
> **Staged migration (#1)**: The old `User`, `Role`, `UserRole` models will NOT be deleted. They will be renamed in the DbContext to `LegacyUsers`, `LegacyRoles`, `LegacyUserRoles` to avoid name collisions with Identity tables. They remain in the database for data reference. Removal will happen in a future sprint after confirming all data is migrated.

---

### Component 7 — Authorization Infrastructure

#### [NEW] `Authorization/Permissions.cs`
Single source of truth — static const strings for all permission keys:
```
Dashboard.View
Products.View, Products.Create, Products.Edit, Products.Delete
Categories.Manage
Suppliers.Manage
Customers.Manage
Inventory.View, Inventory.Edit, Inventory.Transfer
PurchaseOrders.View, PurchaseOrders.Create, PurchaseOrders.Approve
Sales.View, Sales.Create
Reports.View, Reports.Export
Users.Manage, Roles.Manage, Settings.Manage
AuditLogs.View, Notifications.Manage
```
Plus `GetGrouped()` method returning `Dictionary<string, List<(string Key, string Display)>>`.

#### [NEW] `Authorization/HasPermissionAttribute.cs`
```csharp
[AttributeUsage(AttributeTargets.Class | AttributeTargets.Method, AllowMultiple = true)]
public class HasPermissionAttribute : AuthorizeAttribute
{
    public HasPermissionAttribute(string permission) => Policy = permission;
}
```

#### [NEW] `Authorization/PermissionRequirement.cs`
```csharp
public class PermissionRequirement : IAuthorizationRequirement
{
    public string Permission { get; }
    public PermissionRequirement(string permission) => Permission = permission;
}
```

#### [NEW] `Authorization/PermissionAuthorizationHandler.cs`
Checks `User.HasClaim("Permission", requirement.Permission)`:
```csharp
public class PermissionAuthorizationHandler : AuthorizationHandler<PermissionRequirement>
{
    protected override Task HandleRequirementAsync(
        AuthorizationHandlerContext context, PermissionRequirement requirement)
    {
        if (context.User.HasClaim("Permission", requirement.Permission))
            context.Succeed(requirement);
        return Task.CompletedTask;
    }
}
```

#### [NEW] `Authorization/PermissionPolicyProvider.cs`
Dynamically generates authorization policies — no manual policy registration:
```csharp
public class PermissionPolicyProvider : IAuthorizationPolicyProvider
{
    private readonly DefaultAuthorizationPolicyProvider _fallback;

    public Task<AuthorizationPolicy?> GetPolicyAsync(string policyName)
    {
        if (policyName.Contains('.'))
        {
            var policy = new AuthorizationPolicyBuilder()
                .AddRequirements(new PermissionRequirement(policyName))
                .Build();
            return Task.FromResult<AuthorizationPolicy?>(policy);
        }
        return _fallback.GetPolicyAsync(policyName);
    }
    // GetDefaultPolicyAsync returns RequireAuthenticatedUser
    // GetFallbackPolicyAsync returns null
}
```

---

### Component 8 — Service Interfaces & Implementations

> [!IMPORTANT]
> **All business logic lives in services, never in controllers** (#12). Controllers are thin — they validate input, call services, and return views.

#### [NEW] `Services/ICurrentUserService.cs` (#3)
```csharp
public interface ICurrentUserService
{
    string? UserId { get; }
    string? FullName { get; }
    string? Email { get; }
    string? UserName { get; }
    UserStatus? Status { get; }
    bool IsAuthenticated { get; }
    bool HasPermission(string permission);
    IReadOnlyList<string> Permissions { get; }
    IReadOnlyList<string> Roles { get; }
}
```

#### [NEW] `Services/CurrentUserService.cs`
Reads from `IHttpContextAccessor.HttpContext.User` claims. Injected as **Scoped**. No DB queries — reads from the claims principal only.

#### [NEW] `Services/IPermissionService.cs`
```csharp
public interface IPermissionService
{
    Task<IList<string>> GetPermissionsForUserAsync(string userId);
    Task<IList<string>> GetPermissionsForRoleAsync(string roleId);
    Task SetPermissionsForRoleAsync(string roleId, IEnumerable<int> permissionIds);
    Task<List<Permission>> GetAllPermissionsAsync();
    Task<Dictionary<string, List<Permission>>> GetAllPermissionsGroupedAsync();
}
```

#### [NEW] `Services/PermissionService.cs`
EF Core implementation. Queries `RolePermission` → `Permission` through user roles.

#### [NEW] `Services/IPermissionCacheService.cs` (#4)
```csharp
public interface IPermissionCacheService
{
    Task<IList<string>> GetPermissionsAsync(string userId);
    void InvalidateUser(string userId);
    void InvalidateRole(string roleId);
    void InvalidateAll();
}
```

#### [NEW] `Services/PermissionCacheService.cs`
Uses `IMemoryCache` with per-user cache keys. TTL: 30 minutes. Invalidated when:
- A role's permissions are changed → `InvalidateRole()` clears all users with that role
- A user's role assignment changes → `InvalidateUser()`
- Manual cache clear from admin

#### [NEW] `Services/ApplicationUserClaimsPrincipalFactory.cs` (#10)
Extends `UserClaimsPrincipalFactory<ApplicationUser, ApplicationRole>`:
- On login, loads permissions from cache (which calls `IPermissionService` on miss)
- Adds `Claim("Permission", "Products.View")` for each permission
- Adds `Claim("FullName", user.FullName)`
- Adds `Claim("UserStatus", user.Status.ToString())`

#### [NEW] `Services/ILoginHistoryService.cs` (#5)
```csharp
public interface ILoginHistoryService
{
    Task RecordLoginAsync(string userId, LoginResult result, HttpContext context);
    Task RecordLogoutAsync(string userId);
    Task<List<LoginHistory>> GetHistoryForUserAsync(string userId, int count = 50);
}
```

#### [NEW] `Services/LoginHistoryService.cs`
Parses User-Agent for browser/device/OS. Records IP from `HttpContext.Connection.RemoteIpAddress`.

#### [NEW] `Services/ISessionService.cs` (#6)
```csharp
public interface ISessionService
{
    Task CreateSessionAsync(string userId, string sessionToken, HttpContext context);
    Task EndSessionAsync(string sessionToken);
    Task TerminateSessionAsync(string sessionId, string terminatedByUserId);
    Task TerminateAllSessionsAsync(string userId, string exceptSessionToken = null);
    Task<List<UserSession>> GetActiveSessionsAsync(string userId);
    Task<bool> IsSessionValidAsync(string sessionToken);
    Task UpdateLastActivityAsync(string sessionToken);
}
```

#### [NEW] `Services/SessionService.cs`
Implementation + custom `CookieAuthenticationEvents` class:
```csharp
public class SessionValidationEvents : CookieAuthenticationEvents
{
    public override async Task ValidateTicket(CookieValidatePrincipalContext context)
    {
        // Check if session is still active in DB
        // If terminated by admin → reject → forces re-login
        // Also checks if user Status != Active
        // Also re-loads claims if permission cache was invalidated (#10)
    }
}
```
This handles **immediate claims refresh** after role/permission changes and **admin session termination**.

#### [NEW] `Services/IUserPreferenceService.cs` (#8)
```csharp
public interface IUserPreferenceService
{
    Task<UserPreference> GetPreferencesAsync(string userId);
    Task SavePreferencesAsync(string userId, UserPreference preferences);
    Task UpdateThemeAsync(string userId, string theme);
    Task UpdateLanguageAsync(string userId, string language);
}
```

#### [NEW] `Services/UserPreferenceService.cs`
EF Core implementation. Creates default preferences on first access.

#### [NEW] `Services/IAuditService.cs` (#11)
Prepared interface — implementation in Sprint 2:
```csharp
public interface IAuditService
{
    Task LogAsync(string action, string entity, string? entityId = null,
        object? oldValues = null, object? newValues = null);
}
```

#### [NEW] `Services/NullAuditService.cs`
No-op implementation for Sprint 1:
```csharp
public class NullAuditService : IAuditService
{
    public Task LogAsync(...) => Task.CompletedTask;
}
```

---

### Component 9 — Data Layer

#### [MODIFY] [AppDbContext.cs](file:///c:/Users/641578/source/repos/Smart%20Inventory%20System/Smart%20Inventory%20System/Data/AppDbContext.cs)

Changes:
1. **Base class**: `DbContext` → `IdentityDbContext<ApplicationUser, ApplicationRole, string>`
2. **Rename** old sets (#1): `DbSet<User> Users` → `DbSet<User> LegacyUsers`, same for `LegacyRoles`, `LegacyUserRoles`
3. **Add new** DbSets:
   - `DbSet<Permission> Permissions`
   - `DbSet<RolePermission> RolePermissions`
   - `DbSet<LoginHistory> LoginHistories`
   - `DbSet<UserSession> UserSessions`
   - `DbSet<UserPreference> UserPreferences`
4. **Fluent API**:
   - Composite key `RolePermission(RoleId, PermissionId)`
   - One-to-one `ApplicationUser ↔ Employee`
   - One-to-one `ApplicationUser ↔ UserPreference`
   - Rename old `UserRole` composite key config to use `LegacyUserRoles`
   - Index on `LoginHistory(UserId, LoginTime)`
   - Index on `UserSession(SessionToken)`, `UserSession(UserId, IsActive)`
5. **Table mapping**: Map old models to their existing table names to avoid data loss

#### [NEW] `Data/SeedData.cs`
Seeds on startup (idempotent):
1. **21 Permissions** with GroupName/DisplayName
2. **9 Roles** with `IsSystemRole = true` and mapped permissions:

| Role | Permissions |
|---|---|
| Super Admin | All 21 |
| Company Owner | All except AuditLogs.View |
| Manager | Dashboard, Products.*, Categories, Suppliers, Customers, Inventory.View/Edit, PurchaseOrders.*, Sales.*, Reports.* |
| Warehouse Manager | Dashboard, Products.View, Categories, Inventory.*, PurchaseOrders.View |
| Warehouse Employee | Dashboard, Products.View, Inventory.View, Inventory.Edit |
| Purchasing Officer | Dashboard, Products.View, Suppliers, PurchaseOrders.* |
| Sales Employee | Dashboard, Products.View, Customers, Sales.*, Inventory.View |
| Accountant | Dashboard, Reports.*, Sales.View, PurchaseOrders.View |
| Read Only | Dashboard, Products.View, Inventory.View, PurchaseOrders.View, Sales.View, Reports.View |

3. **Default Super Admin user**: `admin@smartinventory.com` / `Admin@123456`

---

### Component 10 — Program.cs

#### [MODIFY] [Program.cs](file:///c:/Users/641578/source/repos/Smart%20Inventory%20System/Smart%20Inventory%20System/Program.cs)

Full service registration:
```csharp
// Identity
builder.Services.AddIdentity<ApplicationUser, ApplicationRole>(opts =>
{
    opts.Password.RequireDigit = true;
    opts.Password.RequiredLength = 8;
    opts.Password.RequireUppercase = true;
    opts.Password.RequireLowercase = true;
    opts.Password.RequireNonAlphanumeric = true;
    opts.Lockout.MaxFailedAccessAttempts = 5;
    opts.Lockout.DefaultLockoutEnd = TimeSpan.FromMinutes(15);
    opts.User.RequireUniqueEmail = true;
})
.AddEntityFrameworkStores<AppDbContext>()
.AddDefaultTokenProviders();

// Custom Claims Factory
builder.Services.AddScoped<IUserClaimsPrincipalFactory<ApplicationUser>,
    ApplicationUserClaimsPrincipalFactory>();

// Authorization
builder.Services.AddSingleton<IAuthorizationPolicyProvider, PermissionPolicyProvider>();
builder.Services.AddScoped<IAuthorizationHandler, PermissionAuthorizationHandler>();

// Services
builder.Services.AddScoped<IPermissionService, PermissionService>();
builder.Services.AddScoped<ICurrentUserService, CurrentUserService>();
builder.Services.AddSingleton<IPermissionCacheService, PermissionCacheService>();
builder.Services.AddScoped<ILoginHistoryService, LoginHistoryService>();
builder.Services.AddScoped<ISessionService, SessionService>();
builder.Services.AddScoped<IUserPreferenceService, UserPreferenceService>();
builder.Services.AddScoped<IAuditService, NullAuditService>();
builder.Services.AddHttpContextAccessor();
builder.Services.AddMemoryCache();

// Cookie Configuration
builder.Services.ConfigureApplicationCookie(opts =>
{
    opts.LoginPath = "/Account/Login";
    opts.LogoutPath = "/Account/Logout";
    opts.AccessDeniedPath = "/Account/AccessDenied";
    opts.ExpireTimeSpan = TimeSpan.FromHours(8);
    opts.SlidingExpiration = true;
    opts.EventsType = typeof(SessionValidationEvents);
});
builder.Services.AddScoped<SessionValidationEvents>();
```

Pipeline:
```csharp
app.UseAuthentication();   // BEFORE UseAuthorization
app.UseAuthorization();

// Seed data
using (var scope = app.Services.CreateScope())
{
    await SeedData.InitializeAsync(scope.ServiceProvider);
}
```

---

### Component 11 — Controllers

#### [NEW] `Controllers/AccountController.cs`
No `[HasPermission]` — public login page:
- `GET Login` — shows login form (redirects if already authenticated)
- `POST Login` — authenticates, records login history (#5), creates session (#6), updates `LastLogin`, checks `UserStatus` (#7), loads preferences (#8)
- `POST Logout` — ends session, records logout time
- `GET AccessDenied` — professional 403 page
- `GET ChangePassword` / `POST ChangePassword`
- `POST SavePreferences` — AJAX endpoint for saving theme/language preferences (#8)

#### [NEW] `Controllers/UsersController.cs`
`[HasPermission(Permissions.UsersManage)]`:
- `Index` — user list with search, status badges (UserStatus), role badges
- `Create (GET/POST)` — full form with role multi-select
- `Edit (GET/POST)` — update details and roles; on role change: invalidate permission cache + invalidate sessions (#10)
- `Details` — profile with assigned roles, effective permissions, login history, active sessions
- `ToggleStatus (POST)` — change UserStatus; terminate sessions if Disabled/Archived
- `ResetPassword (GET/POST)` — admin password reset
- `TerminateSession (POST)` — admin kills a specific session (#6)
- `TerminateAllSessions (POST)` — admin kills all sessions for a user

#### [NEW] `Controllers/RolesController.cs`
`[HasPermission(Permissions.RolesManage)]`:
- `Index` — role list with user count, permission count, IsSystemRole badge
- `Create (GET/POST)` — name, description, grouped permission checkboxes
- `Edit (GET/POST)` — on permission change: invalidate cache for all users in that role (#10)
- `Details` — view role permissions grouped by module
- `Delete (POST)` — only non-system roles; reassign users first

#### [MODIFY] All 11 existing controllers

Add `[HasPermission]` at controller or action level:

| Controller | Attribute Placement | Permissions |
|---|---|---|
| `DashboardController` | Controller level | `Dashboard.View` |
| `ProductsController` | Action level | View: `Products.View`, Create: `Products.Create`, Edit: `Products.Edit`, Delete: `Products.Delete` |
| `CategoriesController` | Controller level | `Categories.Manage` |
| `SuppliersController` | Controller level | `Suppliers.Manage` |
| `CustomersController` | Controller level | `Customers.Manage` |
| `PurchaseOrdersController` | Action level | View: `PurchaseOrders.View`, Create: `PurchaseOrders.Create` |
| `SalesInvoicesController` | Action level | View: `Sales.View`, Create: `Sales.Create` |
| `InventoryController` | Controller level | `Inventory.View` |
| `InventoryHistoryController` | Controller level | `Inventory.View` |
| `SmartReorderController` | Controller level | `Inventory.View` |
| `HomeController` | No attribute | Just redirects to Dashboard |

#### [MODIFY] `Controllers/DashboardController.cs` (#9)
Inject `ICurrentUserService`. Dashboard becomes **permission-aware**:
- **All users** see: Total Products, Current Stock
- **Sales permission** → Today's Sales widget
- **PurchaseOrders permission** → Pending POs widget  
- **Inventory permission** → Low Stock widget, Stock Metrics
- **Reports permission** → Inventory Value
- Pass `UserPermissions` to ViewBag so the view can conditionally render widgets

---

### Component 12 — ViewModels

#### [NEW] `ViewModels/Account/LoginViewModel.cs`
`UsernameOrEmail`, `Password`, `RememberMe` — with validation attributes

#### [NEW] `ViewModels/Account/ChangePasswordViewModel.cs`
`CurrentPassword`, `NewPassword`, `ConfirmNewPassword`

#### [NEW] `ViewModels/Admin/UserCreateViewModel.cs`
`FullName`, `UserName`, `Email`, `PhoneNumber`, `Password`, `ConfirmPassword`, `Status` (UserStatus), `SelectedRoleIds` (List\<string\>), `AvailableRoles`, `EmployeeId?`

#### [NEW] `ViewModels/Admin/UserEditViewModel.cs`
Same as Create minus Password. Adds `Id`, `ProfileImagePath`, `CreatedAt`, `LastLogin`.

#### [NEW] `ViewModels/Admin/UserDetailsViewModel.cs`
Includes: user info, roles, effective permissions (grouped), login history (last 10), active sessions.

#### [NEW] `ViewModels/Admin/ResetPasswordViewModel.cs`
`UserId`, `UserFullName`, `NewPassword`, `ConfirmPassword`

#### [NEW] `ViewModels/Admin/RoleFormViewModel.cs`
`Id`, `Name`, `Description`, `PermissionGroups` → `Dictionary<string, List<PermissionCheckItem>>`
```csharp
public class PermissionCheckItem
{
    public int PermissionId { get; set; }
    public string Key { get; set; }
    public string DisplayName { get; set; }
    public bool IsSelected { get; set; }
}
```

#### [NEW] `ViewModels/Admin/RoleDetailsViewModel.cs`
Role info + grouped permissions + users in role.

---

### Component 13 — Views

#### [NEW] `Views/Shared/_LoginLayout.cshtml`
Minimal layout — no sidebar/topbar. Preserves:
- Dark mode support via `data-theme`
- Language toggle support
- RTL support
- Same CSS variables and fonts

#### [NEW] `Views/Account/Login.cshtml`
Professional login page:
- Centered card with brand/logo area
- Username/Email + Password inputs
- Remember Me checkbox
- Dark/Light + Language toggle in corner
- Bootstrap + existing CSS variables
- RTL-compatible

#### [NEW] `Views/Account/AccessDenied.cshtml`
Professional 403 page:
- Shield/lock icon
- "Access Denied" heading
- Explanation text
- "Go to Dashboard" + "Go Back" buttons

#### [NEW] `Views/Account/ChangePassword.cshtml`
Password change form card.

#### [NEW] `Views/Users/Index.cshtml`
Table matching existing patterns:
- Search bar
- Columns: FullName, Email, Roles (badges), Status (colored badge per UserStatus), LastLogin
- Actions: Details, Edit, Toggle Status, Reset Password

#### [NEW] `Views/Users/Create.cshtml`, `Edit.cshtml`
Form matching existing card pattern. Role checkboxes section.

#### [NEW] `Views/Users/Details.cshtml`
Multi-card layout:
- User Info card
- Assigned Roles card
- Effective Permissions card (grouped accordion)
- Login History table (last 10)
- Active Sessions table with "Terminate" buttons

#### [NEW] `Views/Users/ResetPassword.cshtml`
Simple form card.

#### [NEW] `Views/Roles/Index.cshtml`, `Create.cshtml`, `Edit.cshtml`, `Details.cshtml`
Role management views. Create/Edit includes permission accordion with grouped checkboxes (one accordion panel per module: Products, Inventory, Sales, etc.).

#### [MODIFY] [_Layout.cshtml](file:///c:/Users/641578/source/repos/Smart%20Inventory%20System/Smart%20Inventory%20System/Views/Shared/_Layout.cshtml)

Changes:
1. **Permission-aware sidebar** — each nav item wrapped in permission checks:
```razor
@if (User.HasClaim("Permission", "Products.View"))
{
    <li class="nav-item">
        <a class="nav-link" asp-controller="Products" asp-action="Index">
            <i class="bi bi-box-seam"></i> <span data-lang="products">Products</span>
        </a>
    </li>
}
```
2. **Administration section** — new nav group visible only with Users.Manage or Roles.Manage:
```
Administration
├── Users       (if Users.Manage)
└── Roles       (if Roles.Manage)
```
3. **Topbar user area** — show actual logged-in user:
```razor
<div class="user-avatar">@User.FindFirst("FullName")?.Value?.Substring(0, 2).ToUpper()</div>
<span class="user-name">@User.FindFirst("FullName")?.Value</span>
```
4. **User dropdown menu** — with Profile, Change Password, Logout links
5. **Preferences sync** (#8) — read initial theme/language from server-side preferences via `ViewBag` (falls back to localStorage)
6. **Auth guard** — non-authenticated users don't see sidebar (handled by `[Authorize]` on controllers)

#### [MODIFY] [_ViewImports.cshtml](file:///c:/Users/641578/source/repos/Smart%20Inventory%20System/Smart%20Inventory%20System/Views/_ViewImports.cshtml)
Add:
```razor
@using Smart_Inventory_System.Authorization
@using Smart_Inventory_System.Models.Enums
@using Microsoft.AspNetCore.Identity
```

---

### Component 14 — Dashboard Permission-Awareness (#9)

#### [MODIFY] `Views/Dashboard/Index.cshtml`
Wrap each widget section in permission checks:
```razor
@if (ViewBag.CanViewSales == true)
{
    <!-- Today's Sales stat card -->
}
@if (ViewBag.CanViewPurchaseOrders == true)
{
    <!-- Pending POs stat card -->
}
@if (ViewBag.CanViewInventory == true)
{
    <!-- Low Stock widget, Stock Metrics -->
}
@if (ViewBag.CanViewReports == true)
{
    <!-- Inventory Value -->
}
```
The Smart Reorder banner only shows if user has `Inventory.View`.

---

### Component 15 — CSS & JavaScript

#### [MODIFY] `wwwroot/css/site.css`
Add styles for:
- Login page layout (`.login-page`, `.login-card`, `.login-brand`)
- Access denied page (`.access-denied`)
- User status badges (`.badge-pending`, `.badge-active`, `.badge-locked`, `.badge-disabled`, `.badge-archived`)
- Permission checkbox groups (`.permission-group`, `.permission-check`)
- Session table actions
- User profile card layout
- All with dark mode variants

#### [MODIFY] `wwwroot/js/site.js`
Add translations (both EN and AR):
```javascript
// New keys:
administration, users, roles, permissions, login, logout, accessDenied,
changePassword, resetPassword, fullName, username, password, rememberMe,
confirmPassword, userStatus, pending, locked, disabled, archived,
loginHistory, activeSessions, terminateSession, terminateAllSessions,
assignRoles, assignPermissions, systemRole, selectRoles, profile,
lastLogin, createdAt, ipAddress, browser, device, loginTime
```

Add preference sync function:
```javascript
// On page load, sync preferences from server data attribute
function initPreferencesFromServer() {
    const body = document.body;
    const serverTheme = body.getAttribute('data-server-theme');
    const serverLang = body.getAttribute('data-server-lang');
    if (serverTheme) { /* apply and save to localStorage */ }
    if (serverLang) { /* apply and save to localStorage */ }
}
```

---

### Component 16 — Migration & Seed

#### [NEW] Migration: `AddIdentityAndPermissions`

This migration will:
1. Create Identity tables: `AspNetUsers`, `AspNetRoles`, `AspNetUserRoles`, `AspNetUserClaims`, `AspNetRoleClaims`, `AspNetUserTokens`, `AspNetUserLogins`
2. Create `Permissions` table
3. Create `RolePermissions` table (composite PK)
4. Create `LoginHistories` table
5. Create `UserSessions` table
6. Create `UserPreferences` table
7. Add `ApplicationUserId` FK to `Employees` table
8. **Keep** old `Users`, `Roles`, `UserRoles` tables (renamed in DbContext only, not in DB)

---

## File Inventory

| Category | Files |
|---|---|
| **Enums** | `UserStatus.cs`, `LoginResult.cs` |
| **Models** | `ApplicationUser.cs`, `ApplicationRole.cs`, `Permission.cs`, `RolePermission.cs`, `LoginHistory.cs`, `UserSession.cs`, `UserPreference.cs` |
| **Authorization** | `Permissions.cs`, `HasPermissionAttribute.cs`, `PermissionRequirement.cs`, `PermissionAuthorizationHandler.cs`, `PermissionPolicyProvider.cs` |
| **Services** | `ICurrentUserService.cs`, `CurrentUserService.cs`, `IPermissionService.cs`, `PermissionService.cs`, `IPermissionCacheService.cs`, `PermissionCacheService.cs`, `ApplicationUserClaimsPrincipalFactory.cs`, `SessionValidationEvents.cs`, `ILoginHistoryService.cs`, `LoginHistoryService.cs`, `ISessionService.cs`, `SessionService.cs`, `IUserPreferenceService.cs`, `UserPreferenceService.cs`, `IAuditService.cs`, `NullAuditService.cs` |
| **Data** | `SeedData.cs` (new), `AppDbContext.cs` (modified) |
| **Controllers** | `AccountController.cs`, `UsersController.cs`, `RolesController.cs` (new) + 11 existing (modified) |
| **ViewModels** | `LoginViewModel.cs`, `ChangePasswordViewModel.cs`, `UserCreateViewModel.cs`, `UserEditViewModel.cs`, `UserDetailsViewModel.cs`, `ResetPasswordViewModel.cs`, `RoleFormViewModel.cs`, `RoleDetailsViewModel.cs` |
| **Views** | 15 new + 4 modified (`_Layout`, `_ViewImports`, `Dashboard/Index`, `_LoginLayout`) |
| **Config** | `Program.cs`, `.csproj` (modified) |
| **CSS/JS** | `site.css`, `site.js` (modified) |

---

## Verification Plan

### Build
```bash
dotnet build
```
✔ Zero compilation errors

### Database
```bash
dotnet ef migrations add AddIdentityAndPermissions
dotnet ef database update
```
✔ Migration applies cleanly
✔ Old tables preserved
✔ Seed data creates roles, permissions, admin user

### Functional Testing

| # | Test | Expected |
|---|---|---|
| 1 | Navigate to any page (unauthenticated) | Redirect to `/Account/Login` |
| 2 | Login with `admin@smartinventory.com` / `Admin@123456` | Dashboard with all menu items |
| 3 | All existing modules (Products, Categories, etc.) | Work exactly as before |
| 4 | Create user with "Warehouse Employee" role | Only sees Dashboard, Products (view), Inventory |
| 5 | As Warehouse Employee, navigate to `/Users` | 403 Access Denied page |
| 6 | As Super Admin, change Warehouse Employee's role | Cache invalidated, next request reflects new permissions (#10) |
| 7 | As Super Admin, terminate a user's session (#6) | User is logged out on next request |
| 8 | Test UserStatus: Disabled → Login fails with message | Login rejected |
| 9 | Test lockout: 5 failed attempts → account locked | Returns lockout message |
| 10 | Change Password flow | Old password verified, new password set |
| 11 | Reset Password (admin) | New password works |
| 12 | Login History on user details | Shows login records with IP/browser |
| 13 | Dark mode, Light mode, Arabic, English, RTL | All still work |
| 14 | Preferences persist across login (#8) | Theme/language saved server-side |
| 15 | Dashboard widgets respect permissions (#9) | Sales Employee doesn't see PO widget |
