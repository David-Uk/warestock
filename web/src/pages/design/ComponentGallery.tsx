import { useMemo, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import {
  AlertBanner,
  Badge,
  Button,
  Card,
  Checkbox,
  ConfirmModal,
  EmptyState,
  Input,
  LocationCard,
  Modal,
  Pagination,
  ProgressBar,
  Radio,
  RadioGroup,
  RoleBadge,
  Select,
  Skeleton,
  SkeletonRows,
  Spinner,
  StatTile,
  Table,
  Textarea,
  type Column,
  type SortState,
} from "../../components/ui";
import { toast } from "../../store/toastStore";
import { PageHeader } from "../../components/layout";

function Section({
  id,
  title,
  description,
  children,
}: {
  id: string;
  title: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <section id={id} className="scroll-mt-24">
      <div className="mb-space-12 border-b border-frame pb-space-8">
        <h2 className="font-label-caps text-label-caps uppercase text-primary-container">
          {title}
        </h2>
        {description && <p className="text-body-sm text-on-surface-variant">{description}</p>}
      </div>
      <div className="flex flex-col gap-space-16">{children}</div>
    </section>
  );
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-space-8">
      <p className="font-mono text-mono-sm uppercase text-on-surface-variant">{label}</p>
      <div className="flex flex-wrap items-center gap-space-12">{children}</div>
    </div>
  );
}

const swatches: Array<{ token: string; hex: string }> = [
  { token: "primary-container", hex: "#16283D" },
  { token: "status-success", hex: "#3C8558" },
  { token: "status-warning", hex: "#E8A33D" },
  { token: "status-danger", hex: "#C1443C" },
  { token: "frame", hex: "#C8C5BD" },
  { token: "panel", hex: "#E8E6E0" },
  { token: "surface", hex: "#FCF9F2" },
  { token: "surface-container-lowest", hex: "#FFFFFF" },
];

const typeScale: Array<{ token: string; sample: string; font: string }> = [
  {
    token: "headline-lg",
    sample: "Stock Discrepancies",
    font: "font-headline-lg text-headline-lg",
  },
  { token: "headline-md", sample: "Reorder Alerts", font: "font-headline-md text-headline-md" },
  {
    token: "body-lg",
    sample: "Long-form body copy for instructions.",
    font: "font-body-lg text-body-lg",
  },
  {
    token: "body-md",
    sample: "Default UI copy for tables and forms.",
    font: "font-body-md text-body-md",
  },
  { token: "mono-xl", sample: "12,480", font: "font-mono-xl text-mono-xl" },
  { token: "mono-md", sample: "SKU-48291", font: "font-mono-md text-mono-md" },
  { token: "mono-sm", sample: "LAST UPDATED 09:41", font: "font-mono-sm text-mono-sm" },
  {
    token: "label-caps",
    sample: "ZONE A — ACTIVE",
    font: "font-label-caps text-label-caps uppercase",
  },
];

interface DemoRow {
  id: string;
  sku: string;
  description: string;
  qty: number;
  status: "ok" | "low";
}

const demoRows: DemoRow[] = [
  { id: "1", sku: "SKU-48291", description: "M8 hex bolt, zinc plated", qty: 12480, status: "ok" },
  { id: "2", sku: "SKU-10934", description: "Corrugated carton 400×300", qty: 320, status: "low" },
  { id: "3", sku: "SKU-77502", description: 'Thermal label roll 4"', qty: 6400, status: "ok" },
  { id: "4", sku: "SKU-30118", description: "Pallet wrap 500mm clear", qty: 88, status: "low" },
];

export default function ComponentGallery() {
  const navigate = useNavigate();
  const [modalOpen, setModalOpen] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmLoading, setConfirmLoading] = useState(false);
  const [sort, setSort] = useState<SortState | null>(null);
  const [loading, setLoading] = useState(false);
  const [showEmpty, setShowEmpty] = useState(false);
  const [page, setPage] = useState(3);
  const [capacity, setCapacity] = useState(82);

  const rows = useMemo(() => {
    if (showEmpty) return [];
    if (!sort) return demoRows;
    const factor = sort.dir === "asc" ? 1 : -1;
    return [...demoRows].sort((a, b) => {
      const key = sort.key as keyof DemoRow;
      if (typeof a[key] === "number" && typeof b[key] === "number") {
        return ((a[key] as number) - (b[key] as number)) * factor;
      }
      return String(a[key]).localeCompare(String(b[key])) * factor;
    });
  }, [sort, showEmpty]);

  const columns: Array<Column<DemoRow>> = [
    { key: "sku", header: "SKU", accessor: "sku", mono: true, sortable: true, width: "140px" },
    { key: "description", header: "Description", accessor: "description", sortable: true },
    {
      key: "qty",
      header: "On hand",
      align: "right",
      mono: true,
      sortable: true,
      render: (row) => row.qty.toLocaleString("en-GB"),
    },
    {
      key: "status",
      header: "Status",
      align: "right",
      render: (row) => (
        <Badge tone={row.status === "ok" ? "success" : "warning"}>
          {row.status === "ok" ? "Reconciled" : "Low stock"}
        </Badge>
      ),
    },
  ];

  const runConfirm = () => {
    setConfirmLoading(true);
    setTimeout(() => {
      setConfirmLoading(false);
      setConfirmOpen(false);
      toast.success("Acknowledged", "Alert ACK-2041 marked as resolved.");
    }, 800);
  };

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-space-48 p-space-16 md:p-space-32">
      <PageHeader
        title="WareStock Component Library"
        eyebrow="DESIGN SYSTEM › COMPONENT GALLERY"
        description="React implementations of the Stitch WareStock AI Design System screens — IBM Plex Sans + JetBrains Mono, 4px radii, hairline frames, 48px touch targets."
        chips={
          <>
            <Badge tone="info">Tailwind v4</Badge>
            <Badge tone="neutral" icon={false}>
              24 components
            </Badge>
          </>
        }
        actions={
          <div className="flex flex-wrap gap-space-8">
            <Button
              variant="ghost"
              icon="dashboard_customize"
              onClick={() => navigate("/design/shell")}
            >
              Shell preview
            </Button>
            <Button
              variant="ghost"
              icon="campaign"
              onClick={() =>
                toast.info("Gallery", "Use the sections below to inspect each component.")
              }
            >
              Announce
            </Button>
          </div>
        }
      />

      <Section
        id="foundations"
        title="Foundations"
        description="Colour, type and status palette from the Stitch tokens."
      >
        <div className="grid grid-cols-2 gap-space-8 sm:grid-cols-4">
          {swatches.map((swatch) => (
            <div
              key={swatch.token}
              className="overflow-hidden rounded border border-frame bg-white"
            >
              <div className="h-16" style={{ backgroundColor: swatch.hex }} aria-hidden="true" />
              <div className="flex flex-col gap-space-2 p-space-8">
                <span className="font-mono text-mono-sm text-primary-container">{swatch.hex}</span>
                <span className="truncate font-label-caps text-label-caps uppercase text-on-surface-variant">
                  {swatch.token}
                </span>
              </div>
            </div>
          ))}
        </div>
        <div className="flex flex-col gap-space-12 rounded border border-frame bg-white p-space-16">
          {typeScale.map((entry) => (
            <div
              key={entry.token}
              className="flex items-baseline gap-space-16 border-b border-frame pb-space-8 last:border-b-0 last:pb-0"
            >
              <span className="w-32 shrink-0 font-mono text-mono-sm text-on-surface-variant">
                {entry.token}
              </span>
              <span className={entry.font}>{entry.sample}</span>
            </div>
          ))}
        </div>
      </Section>

      <Section
        id="buttons"
        title="Buttons"
        description="52px handheld / 48px desktop minimum, hard 2px borders."
      >
        <Row label="Variants">
          <Button variant="primary">Primary</Button>
          <Button variant="secondary">Secondary</Button>
          <Button variant="hazard">Hazard</Button>
          <Button variant="cancel">Cancel</Button>
          <Button variant="ghost" icon="tune">
            Ghost
          </Button>
        </Row>
        <Row label="Sizes">
          <Button size="sm">Small</Button>
          <Button size="md">Medium</Button>
          <Button size="lg">Large</Button>
        </Row>
        <Row label="States">
          <Button loading>Saving</Button>
          <Button disabled>Disabled</Button>
          <Button variant="secondary" icon="download">
            With icon
          </Button>
          <Button fullWidth className="max-w-64">
            Full width
          </Button>
        </Row>
      </Section>

      <Section
        id="badges"
        title="Badges & alerts"
        description="Mono uppercase flags with 1px borders — no soft pills."
      >
        <Row label="Status chips">
          <Badge tone="success">Reconciled</Badge>
          <Badge tone="warning">Low stock</Badge>
          <Badge tone="danger">Discrepancy</Badge>
          <Badge tone="info">In transit</Badge>
          <Badge tone="live">Live count</Badge>
          <Badge tone="neutral" icon={false}>
            Draft
          </Badge>
        </Row>
        <Row label="Micro tags">
          <Badge tone="success" size="tag">
            On hand 12,480
          </Badge>
          <Badge tone="danger" size="tag">
            Zona 4
          </Badge>
        </Row>
        <Row label="Role tiers">
          <RoleBadge role="superadmin" />
          <RoleBadge role="org_admin" />
          <RoleBadge role="warehouse_manager" />
          <RoleBadge role="cycle_count_auditor" />
          <RoleBadge role="unknown_role" />
        </Row>
        <div className="flex flex-col gap-space-12">
          <AlertBanner tone="critical" title="Discrepancy — SKU-48291">
            System 12,480 vs counted 12,340 — variance −140 units at A-04-BAY-12-LVL-2.
          </AlertBanner>
          <AlertBanner
            tone="warning"
            title="Reorder threshold breached"
            action={<Button size="sm">Acknowledge</Button>}
            onDismiss={() => toast.info("Dismissed", "Alert hidden from the feed.")}
          >
            4 SKUs in Zone A are below safety stock.
          </AlertBanner>
          <AlertBanner tone="success" title="Cycle count complete" onDismiss={() => undefined}>
            128 locations reconciled with no variance.
          </AlertBanner>
        </div>
      </Section>

      <Section
        id="forms"
        title="Form controls"
        description="48–52px fields, mono values, label-caps captions."
      >
        <div className="grid gap-space-16 md:grid-cols-2">
          <Input label="Email" placeholder="operator@warestock.io" defaultValue="" />
          <Input
            label="Password"
            type="password"
            placeholder="••••••••"
            icon={<span className="material-symbols-outlined text-[20px]">visibility</span>}
          />
          <Input
            label="SKU"
            placeholder="Scan or type SKU"
            scanner
            hint="Pull the trigger to scan."
          />
          <Input
            label="Location"
            placeholder="A-04-BAY-12"
            error="Location does not exist in Zone A."
          />
          <Select
            label="Zone"
            icon="grid_view"
            defaultValue="zone-a"
            options={[
              { value: "zone-a", label: "Zone A" },
              { value: "zone-b", label: "Zone B" },
              { value: "zone-c", label: "Zone C" },
            ]}
          />
          <Textarea
            label="Notes"
            placeholder="Optional note for the audit log"
            maxLength={120}
            showCount
            defaultValue=""
          />
        </div>
        <div className="grid gap-space-16 md:grid-cols-2">
          <div className="rounded border border-frame bg-white p-space-12">
            <Checkbox
              label="Include zero-stock SKUs"
              description="Shows locations with no on-hand units."
              defaultChecked
            />
            <Checkbox label="Flag variance over 5%" description="Marks rows red in the manifest." />
            <Checkbox
              label="Invalid example"
              error="This option is currently unavailable."
              disabled
            />
          </div>
          <div className="rounded border border-frame bg-white p-space-12">
            <RadioGroup legend="Count method">
              <Radio
                name="method"
                label="Barcode scan"
                description="Fastest for full pallets"
                defaultChecked
              />
              <Radio
                name="method"
                label="Manual entry"
                description="For damaged or missing labels"
              />
              <Radio
                name="method"
                label="Photo count"
                description="AI-assisted quantity estimate"
              />
            </RadioGroup>
          </div>
        </div>
      </Section>

      <Section
        id="cards"
        title="Cards & data display"
        description="Section cards, KPI tiles and capacity meters."
      >
        <div className="grid gap-space-16 md:grid-cols-3">
          <StatTile
            label="Stock turnover"
            value="82.6"
            unit="%"
            delta={{ label: "+12%", direction: "up" }}
            accent="top"
            meta="Last updated 09:41"
            icon="autorenew"
          />
          <StatTile
            label="Open discrepancies"
            value="12"
            accent="left"
            tone="danger"
            delta={{ label: "▼ 4", direction: "down" }}
            meta="Zone A · 8 unresolved"
            icon="rule"
          />
          <StatTile
            label="Reorder alerts"
            value="34"
            accent="none"
            meta="Replenish before 18:00"
            icon="notification_important"
          />
        </div>

        <div className="grid gap-space-16 md:grid-cols-2">
          <Card
            title="Capacity — Zone A"
            icon="inventory_2"
            headerAction={<Badge tone="success">82% free</Badge>}
            footer={
              <div className="flex justify-between font-mono text-mono-sm uppercase text-on-surface-variant">
                <span>Last updated 09:41</span>
                <span>4 locations</span>
              </div>
            }
          >
            <div className="flex flex-col gap-space-16">
              <ProgressBar value={capacity} label="Bay 12 — Level 2" />
              <ProgressBar value={97} label="Bay 08 — Level 1" />
              <ProgressBar value={40} label="Bay 03 — Level 1" tone="success" />
              <Button
                size="sm"
                variant="secondary"
                onClick={() => setCapacity((c) => (c === 82 ? 34 : 82))}
              >
                Simulate fill change
              </Button>
            </div>
          </Card>

          <LocationCard
            coordinate="A-04-BAY-12-LVL-2"
            zone="Zone A — Racking Level 2"
            description="Fast-moving consumables"
            sku="SKU-48291"
            quantity={12480}
            capacity={82}
            status="online"
            lastCounted="today 09:41"
            onOpen={() => toast.info("Bay opened", "A-04-BAY-12-LVL-2")}
          />
        </div>
      </Section>

      <Section
        id="table"
        title="Manifest table & pagination"
        description="Navy header, hairline grid, mono numerics, sortable columns."
      >
        <div className="flex flex-wrap gap-space-8">
          <Button size="sm" variant="secondary" onClick={() => setLoading((v) => !v)}>
            {loading ? "Stop loading" : "Show loading"}
          </Button>
          <Button size="sm" variant="secondary" onClick={() => setShowEmpty((v) => !v)}>
            {showEmpty ? "Show rows" : "Show empty state"}
          </Button>
        </div>

        <div className="rounded border border-frame bg-white">
          <Table
            caption="Stock manifest"
            columns={columns}
            rows={rows}
            getRowId={(row) => row.id}
            loading={loading}
            sort={sort}
            onSort={setSort}
            emptyState={
              <EmptyState
                icon="search_off"
                heading="No stock found"
                description="Adjust the filters and try again."
              />
            }
          />
          <Pagination
            page={page}
            pageCount={20}
            onPageChange={setPage}
            total={1240}
            pageSize={20}
            onPageSizeChange={() => undefined}
          />
        </div>

        <div className="grid gap-space-16 md:grid-cols-3">
          <Card title="Loading" flush>
            <SkeletonRows rows={4} />
          </Card>
          <Card title="Empty state">
            <EmptyState
              icon="package_2"
              heading="No shipments"
              description="Goods-in has not posted anything for this shift."
            />
          </Card>
          <Card title="Feedback">
            <div className="flex flex-wrap items-center gap-space-16">
              <Spinner />
              <Spinner size="lg" />
              <div className="flex flex-col gap-space-8">
                <Skeleton width={160} />
                <Skeleton width={120} />
              </div>
            </div>
          </Card>
        </div>
      </Section>

      <Section
        id="overlays"
        title="Overlays & notifications"
        description="Focus-trapped dialog, confirmation pattern and toast queue."
      >
        <Row label="Dialogs">
          <Button variant="primary" onClick={() => setModalOpen(true)}>
            Open modal
          </Button>
          <Button variant="hazard" onClick={() => setConfirmOpen(true)}>
            Destructive confirm
          </Button>
        </Row>
        <Row label="Toasts">
          <Button
            variant="secondary"
            onClick={() => toast.success("Count saved", "A-04-BAY-12-LVL-2 reconciled.")}
          >
            Success
          </Button>
          <Button
            variant="secondary"
            onClick={() => toast.error("Scan failed", "Barcode 48291 is not in this zone.")}
          >
            Error
          </Button>
          <Button
            variant="secondary"
            onClick={() => toast.warning("Low stock", "SKU-10934 below safety stock.")}
          >
            Warning
          </Button>
          <Button
            variant="secondary"
            onClick={() => toast.info("Shift handover", "Notes published to the ops board.")}
          >
            Info
          </Button>
        </Row>

        <Modal
          open={modalOpen}
          onClose={() => setModalOpen(false)}
          title="Transfer stock"
          description="ZONE A › ZONE B"
          footer={
            <>
              <Button variant="cancel" onClick={() => setModalOpen(false)}>
                Cancel
              </Button>
              <Button variant="primary" data-autofocus onClick={() => setModalOpen(false)}>
                Confirm transfer
              </Button>
            </>
          }
        >
          <div className="flex flex-col gap-space-16">
            <Input label="From location" defaultValue="A-04-BAY-12-LVL-2" data-autofocus />
            <Input label="To location" placeholder="B-01-BAY-04-LVL-1" />
            <Textarea
              label="Reason"
              placeholder="Optional audit note"
              maxLength={200}
              showCount
              defaultValue=""
            />
          </div>
        </Modal>

        <ConfirmModal
          open={confirmOpen}
          onClose={() => setConfirmOpen(false)}
          onConfirm={runConfirm}
          title="Delete organisation?"
          message="Acme Logistics and its 3 warehouses will be suspended. This action is recorded in the audit log."
          confirmLabel="Delete"
          cancelLabel="Keep"
          tone="danger"
          loading={confirmLoading}
        />
      </Section>
    </div>
  );
}
