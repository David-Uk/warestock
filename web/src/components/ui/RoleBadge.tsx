import { cn } from "../../lib/utils";

/**
 * Mirrors backend `PlatformRole`, `TenantRole` and `WarehouseRole` enums
 * (backend/app/models/user.py) plus a "warehouse_staff" tenant value.
 */
export type RoleName =
  | "superadmin"
  | "system_admin"
  | "helpdesk"
  | "org_admin"
  | "warehouse_admin"
  | "warehouse_staff"
  | "warehouse_manager"
  | "inventory_controller"
  | "receiving_associate"
  | "dispatch_associate"
  | "cycle_count_auditor"
  | "shift_supervisor";

type Tier = "platform" | "org" | "warehouse";

const ROLE_META: Record<RoleName, { label: string; tier: Tier }> = {
  superadmin: { label: "Superadmin", tier: "platform" },
  system_admin: { label: "System Admin", tier: "platform" },
  helpdesk: { label: "Helpdesk", tier: "platform" },
  org_admin: { label: "Org Admin", tier: "org" },
  warehouse_admin: { label: "Warehouse Admin", tier: "org" },
  warehouse_staff: { label: "Warehouse Staff", tier: "warehouse" },
  warehouse_manager: { label: "Warehouse Manager", tier: "warehouse" },
  inventory_controller: { label: "Inventory Controller", tier: "warehouse" },
  receiving_associate: { label: "Receiving Associate", tier: "warehouse" },
  dispatch_associate: { label: "Dispatch Associate", tier: "warehouse" },
  cycle_count_auditor: { label: "Cycle Count Auditor", tier: "warehouse" },
  shift_supervisor: { label: "Shift Supervisor", tier: "warehouse" },
};

const tierClasses: Record<Tier, string> = {
  platform: "bg-tier-platform-bg text-tier-platform border-tier-platform",
  org: "bg-tier-org-bg text-tier-org border-tier-org",
  warehouse: "bg-tier-warehouse-bg text-tier-warehouse border-tier-warehouse",
};

export interface RoleBadgeProps {
  role: string;
  className?: string;
}

/**
 * Colour-coded pill for a role string — tier tint (platform violet,
 * org blue, warehouse slate) with human-readable label. Unknown roles
 * fall back to a neutral chip so nothing renders blank.
 */
export function RoleBadge({ role, className }: RoleBadgeProps) {
  const meta = ROLE_META[role as RoleName];

  if (!meta) {
    return (
      <span
        className={cn(
          "inline-flex w-fit items-center rounded border border-outline-variant bg-surface-container px-space-8 py-space-2 font-mono text-mono-sm font-bold uppercase text-on-surface-variant",
          className
        )}
      >
        {role}
      </span>
    );
  }

  return (
    <span
      className={cn(
        "inline-flex w-fit items-center rounded border px-space-8 py-space-2 font-mono text-mono-sm font-bold uppercase",
        tierClasses[meta.tier],
        className
      )}
    >
      {meta.label}
    </span>
  );
}
