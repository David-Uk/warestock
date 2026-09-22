"""Seed default permissions and role-permission mappings.

Run with: python -m app.db.seed_rbac
"""
import asyncio

from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.permission import Permission, PermissionScope, RolePermission

# ── Default Permissions ──────────────────────────────────────────────────────

DEFAULT_PERMISSIONS = [
    # Platform-level
    {"code": "platform:manage", "name": "Manage Platform", "description": "Full platform administration", "scope": PermissionScope.PLATFORM},
    {"code": "organisations:read", "name": "View Organisations", "description": "View all organisations", "scope": PermissionScope.PLATFORM},
    {"code": "organisations:manage", "name": "Manage Organisations", "description": "Create/edit/delete organisations", "scope": PermissionScope.PLATFORM},
    {"code": "platform_users:read", "name": "View Platform Users", "description": "View platform-level users", "scope": PermissionScope.PLATFORM},
    {"code": "platform_users:manage", "name": "Manage Platform Users", "description": "Create/edit/delete platform users", "scope": PermissionScope.PLATFORM},
    {"code": "rbac:manage", "name": "Manage RBAC", "description": "Manage permissions and role assignments", "scope": PermissionScope.PLATFORM},

    # Tenant-level (organisation-scoped)
    {"code": "org:read", "name": "View Organisation", "description": "View own organisation details", "scope": PermissionScope.TENANT},
    {"code": "org:manage", "name": "Manage Organisation", "description": "Edit own organisation settings", "scope": PermissionScope.TENANT},
    {"code": "org_users:read", "name": "View Org Users", "description": "View users in own organisation", "scope": PermissionScope.TENANT},
    {"code": "org_users:manage", "name": "Manage Org Users", "description": "Invite/edit/deactivate users in own organisation", "scope": PermissionScope.TENANT},
    {"code": "org_warehouses:read", "name": "View Org Warehouses", "description": "View warehouses in own organisation", "scope": PermissionScope.TENANT},
    {"code": "org_warehouses:manage", "name": "Manage Org Warehouses", "description": "Create/edit/delete warehouses in own organisation", "scope": PermissionScope.TENANT},
    {"code": "org_warehouse_roles:manage", "name": "Manage Warehouse Roles", "description": "Assign roles within warehouses in own organisation", "scope": PermissionScope.TENANT},
    {"code": "temporal_permissions:grant", "name": "Grant Temporal Permissions", "description": "Grant temporary permissions to users", "scope": PermissionScope.TENANT},

    # Warehouse-level
    {"code": "stock:read", "name": "View Stock", "description": "View stock levels and movements", "scope": PermissionScope.WAREHOUSE},
    {"code": "stock:write", "name": "Manage Stock", "description": "Create/edit stock levels and movements", "scope": PermissionScope.WAREHOUSE},
    {"code": "stock:adjust", "name": "Adjust Stock", "description": "Perform stock adjustments", "scope": PermissionScope.WAREHOUSE},
    {"code": "shipments:receive", "name": "Receive Shipments", "description": "Process incoming shipments", "scope": PermissionScope.WAREHOUSE},
    {"code": "shipments:dispatch", "name": "Dispatch Shipments", "description": "Process outgoing shipments", "scope": PermissionScope.WAREHOUSE},
    {"code": "cycle_count:perform", "name": "Perform Cycle Count", "description": "Conduct cycle counts", "scope": PermissionScope.WAREHOUSE},
    {"code": "cycle_count:audit", "name": "Audit Cycle Count", "description": "Audit and approve cycle counts", "scope": PermissionScope.WAREHOUSE},
    {"code": "shifts:manage", "name": "Manage Shifts", "description": "Manage warehouse shifts", "scope": PermissionScope.WAREHOUSE},
    {"code": "reports:read", "name": "View Reports", "description": "View warehouse reports", "scope": PermissionScope.WAREHOUSE},
    {"code": "photos:count", "name": "Count Photos", "description": "Upload and count photos", "scope": PermissionScope.WAREHOUSE},
]


# ── Default Role-Permission Mappings ────────────────────────────────────────

DEFAULT_ROLE_PERMISSIONS = {
    # Platform roles
    "platform:superadmin": [
        "platform:manage", "organisations:read", "organisations:manage",
        "platform_users:read", "platform_users:manage", "rbac:manage",
        "org:read", "org:manage", "org_users:read", "org_users:manage",
        "org_warehouses:read", "org_warehouses:manage", "org_warehouse_roles:manage",
        "temporal_permissions:grant",
        "stock:read", "stock:write", "stock:adjust",
        "shipments:receive", "shipments:dispatch",
        "cycle_count:perform", "cycle_count:audit",
        "shifts:manage", "reports:read", "photos:count",
    ],
    "platform:system_admin": [
        "organisations:read", "organisations:manage",
        "platform_users:read", "platform_users:manage",
        "rbac:manage",
    ],
    "platform:helpdesk": [
        "organisations:read",
        "platform_users:read",
    ],

    # Tenant roles
    "tenant:org_admin": [
        "org:read", "org:manage",
        "org_users:read", "org_users:manage",
        "org_warehouses:read", "org_warehouses:manage",
        "org_warehouse_roles:manage",
        "temporal_permissions:grant",
        "stock:read", "stock:write", "stock:adjust",
        "shipments:receive", "shipments:dispatch",
        "cycle_count:perform", "cycle_count:audit",
        "shifts:manage", "reports:read", "photos:count",
    ],
    "tenant:warehouse_admin": [
        "stock:read", "stock:write", "stock:adjust",
        "shipments:receive", "shipments:dispatch",
        "cycle_count:perform", "cycle_count:audit",
        "shifts:manage", "reports:read", "photos:count",
        "temporal_permissions:grant",
    ],
    "tenant:warehouse_staff": [
        "stock:read",
        "reports:read",
    ],

    # Warehouse roles
    "warehouse:warehouse_manager": [
        "stock:read", "stock:write", "stock:adjust",
        "shipments:receive", "shipments:dispatch",
        "cycle_count:perform", "cycle_count:audit",
        "shifts:manage", "reports:read", "photos:count",
        "temporal_permissions:grant",
    ],
    "warehouse:inventory_controller": [
        "stock:read", "stock:write", "stock:adjust",
        "cycle_count:perform", "cycle_count:audit",
        "reports:read",
    ],
    "warehouse:receiving_associate": [
        "stock:read", "stock:write",
        "shipments:receive",
        "photos:count",
    ],
    "warehouse:dispatch_associate": [
        "stock:read", "stock:write",
        "shipments:dispatch",
        "photos:count",
    ],
    "warehouse:cycle_count_auditor": [
        "stock:read",
        "cycle_count:perform", "cycle_count:audit",
        "reports:read",
    ],
    "warehouse:shift_supervisor": [
        "stock:read",
        "shifts:manage",
        "reports:read",
        "temporal_permissions:grant",
    ],
}


async def seed_rbac() -> None:
    """Seed default permissions and role-permission mappings."""
    async with async_session_factory() as db:
        # Seed permissions
        existing_result = await db.execute(select(Permission))
        existing_codes = {p.code for p in existing_result.scalars().all()}

        created = 0
        for perm_data in DEFAULT_PERMISSIONS:
            if perm_data["code"] not in existing_codes:
                perm = Permission(**perm_data)
                db.add(perm)
                created += 1

        await db.flush()
        print(f"Created {created} new permissions ({len(DEFAULT_PERMISSIONS)} total defined)")

        # Seed role-permission mappings
        perm_result = await db.execute(select(Permission))
        perm_map = {p.code: p.id for p in perm_result.scalars().all()}

        existing_rp_result = await db.execute(select(RolePermission))
        existing_rp = {(rp.role_key, rp.permission_id) for rp in existing_rp_result.scalars().all()}

        rp_created = 0
        for role_key, perm_codes in DEFAULT_ROLE_PERMISSIONS.items():
            for code in perm_codes:
                if code in perm_map:
                    perm_id = perm_map[code]
                    if (role_key, perm_id) not in existing_rp:
                        rp = RolePermission(role_key=role_key, permission_id=perm_id)
                        db.add(rp)
                        rp_created += 1

        await db.flush()
        print(f"Created {rp_created} new role-permission mappings")

        await db.commit()
        print("RBAC seed complete.")


if __name__ == "__main__":
    asyncio.run(seed_rbac())
