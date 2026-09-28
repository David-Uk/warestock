import { Outlet } from "react-router-dom";

export default function AuthLayout() {
  return (
    <div className="bg-surface-dim font-body-md text-on-surface min-h-screen flex flex-col">
      <header className="w-full bg-primary-container px-space-24 py-space-12 flex items-center justify-between border-b border-outline/30">
        <div className="flex items-center gap-space-12">
          <span className="material-symbols-outlined text-secondary-fixed text-[24px]">
            precision_manufacturing
          </span>
          <span className="font-headline-md text-headline-md text-on-primary tracking-tight uppercase">
            WareStock<span className="text-secondary-fixed">.AI</span>
          </span>
        </div>
        <div className="flex items-center gap-space-8 px-space-8 py-space-4 bg-tertiary-container rounded border border-tertiary-fixed-dim/30">
          <div className="w-2 h-2 rounded-full bg-tertiary-fixed animate-pulse"></div>
          <span className="font-mono-sm text-mono-sm text-tertiary-fixed font-bold">
            SYS_LIVE: 99.98%
          </span>
        </div>
      </header>
      <main className="w-full min-h-[calc(100vh-48px)] flex items-center justify-center p-space-16">
        <Outlet />
      </main>
    </div>
  );
}
