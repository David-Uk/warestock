import { useState } from "react";
import { Link } from "react-router-dom";

export default function Login() {
  const [showPassword, setShowPassword] = useState(false);
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [authSuccess, setAuthSuccess] = useState(false);

  const triggerAuth = (e: React.FormEvent) => {
    e.preventDefault();
    setIsAuthenticating(true);
    setTimeout(() => {
      setIsAuthenticating(false);
      setAuthSuccess(true);
    }, 1200);
  };

  return (
    <div className="w-full max-w-[520px] flex flex-col gap-space-16">
      {/* Top System Telemetry Bar */}
      <div className="flex flex-wrap items-center justify-between gap-space-8 px-space-12 py-space-4 bg-surface-container-high rounded border border-outline-variant/60 shadow-sm text-on-surface-variant">
        <div className="flex items-center gap-space-8">
          <span className="w-2 h-2 rounded-full bg-[#3C8558] animate-pulse"></span>
          <span className="font-mono-sm text-mono-sm font-semibold tracking-wider text-on-surface">
            SYS_LIVE 99.98%
          </span>
          <span className="text-outline-variant">|</span>
          <span className="font-mono-sm text-mono-sm">FIPS-140-3</span>
        </div>
        <div className="flex items-center gap-space-4">
          <span className="material-symbols-outlined text-[16px] text-secondary">encrypted</span>
          <span className="font-mono-sm text-mono-sm font-bold text-secondary uppercase tracking-tight">
            ENCRYPTED_TLS_1.3
          </span>
        </div>
      </div>

      {/* Main Authentication Terminal Card */}
      <div className="w-full bg-surface-container-lowest rounded border-2 border-outline-variant/80 shadow-md p-space-24 sm:p-space-32 flex flex-col relative overflow-hidden">
        {/* Top Zone Color-Coded Structural Accent Strip */}
        <div className="absolute top-0 left-0 right-0 h-1.5 bg-primary-container"></div>

        {/* Header & Icon Brand Area */}
        <div className="flex items-start gap-space-16 pb-space-20 border-b border-outline-variant/50">
          {/* SVG Brand Logo Artifact */}
          <div className="w-14 h-14 bg-primary-container rounded flex items-center justify-center p-2 shrink-0 shadow-sm">
            <svg
              className="w-full h-full"
              fill="none"
              viewBox="0 0 100 100"
              xmlns="http://www.w3.org/2000/svg"
            >
              <rect
                fill="#16283d"
                height="70"
                stroke="#e4e2db"
                strokeWidth="6"
                width="70"
                x="15"
                y="15"
              ></rect>
              <line stroke="#e4e2db" strokeWidth="4" x1="15" x2="85" y1="50" y2="50"></line>
              <rect fill="#3C8558" height="20" width="7" x="23" y="23"></rect>
              <rect fill="#e4e2db" height="20" width="4" x="33" y="23"></rect>
              <rect fill="#3C8558" height="20" width="9" x="40" y="23"></rect>
              <rect fill="#e4e2db" height="20" width="5" x="52" y="23"></rect>
              <line
                stroke="#feb64e"
                strokeLinecap="round"
                strokeWidth="7"
                x1="10"
                x2="88"
                y1="88"
                y2="14"
              ></line>
              <circle cx="50" cy="50" fill="#ba1a1a" r="7.5"></circle>
            </svg>
          </div>
          <div className="flex flex-col min-w-0">
            <div className="flex items-center gap-space-8 flex-wrap">
              <span className="font-headline-lg text-headline-lg text-primary tracking-tight">
                WareStock<span className="text-secondary">.AI</span>
              </span>
              <span className="px-space-8 py-0.5 bg-surface-container-high rounded text-[11px] font-mono-sm font-bold text-on-surface-variant tracking-wider uppercase border border-outline-variant/70">
                NODE_04
              </span>
            </div>
            <p className="font-label-caps text-label-caps text-outline uppercase tracking-wider mt-0.5">
              INDUSTRIAL LOGISTICS INTELLIGENCE // AUTH v4.12
            </p>
          </div>
        </div>

        {/* Card Title & Scope Briefing */}
        <div className="pt-space-20 pb-space-16">
          <h1 className="font-headline-md text-headline-md text-on-surface">
            Operator Terminal Sign In
          </h1>
          <p className="font-body-sm text-body-sm text-on-surface-variant mt-space-4">
            Deterministic authentication for warehouse distribution, multi-tenant inventory ledger,
            and robotics dispatch.
          </p>
        </div>

        {/* Authentication Form */}
        <form className="flex flex-col gap-space-20" onSubmit={triggerAuth}>
          {/* Input Field: Badge / Corporate Email */}
          <div className="flex flex-col gap-space-4">
            <div className="flex justify-between items-center">
              <label
                className="font-label-caps text-label-caps text-primary tracking-wider uppercase flex items-center gap-space-4"
                htmlFor="terminal-id"
              >
                <span className="material-symbols-outlined text-[16px] text-primary">badge</span>
                Corporate Email / Employee Badge ID
              </label>
              <span className="font-mono-sm text-[11px] px-space-4 py-0.5 bg-secondary-fixed/40 text-on-secondary-fixed rounded font-semibold border border-secondary-container hidden sm:inline-block">
                [LASER / RFID READY]
              </span>
            </div>
            <div className="relative flex items-center">
              <input
                className="w-full h-[48px] px-space-12 bg-surface-container-lowest border-2 border-[#969288] focus:border-primary-container focus:bg-[#FAF3E6] focus:outline-none rounded font-mono-md text-mono-md text-on-surface transition-colors placeholder:text-outline-variant"
                id="terminal-id"
                placeholder="e.g. OP-884291@warestock.io"
                required
                type="text"
              />
              <div className="absolute right-3 text-outline pointer-events-none flex items-center">
                <span className="material-symbols-outlined text-[20px]">barcode_scanner</span>
              </div>
            </div>
          </div>

          {/* Input Field: Password / Security PIN */}
          <div className="flex flex-col gap-space-4">
            <div className="flex justify-between items-center">
              <label
                className="font-label-caps text-label-caps text-primary tracking-wider uppercase flex items-center gap-space-4"
                htmlFor="terminal-pin"
              >
                <span className="material-symbols-outlined text-[16px] text-primary">key</span>
                Security Password / PIN
              </label>
              <span className="font-mono-sm text-[11px] text-outline font-medium tracking-wide">
                MIN 8 CHARS
              </span>
            </div>
            <div className="relative flex items-center">
              <input
                className="w-full h-[48px] px-space-12 pr-12 bg-surface-container-lowest border-2 border-[#969288] focus:border-primary-container focus:bg-[#FAF3E6] focus:outline-none rounded font-mono-md text-mono-md text-on-surface transition-colors tracking-widest placeholder:text-outline-variant"
                id="terminal-pin"
                placeholder="••••••••••••"
                required
                type={showPassword ? "text" : "password"}
              />
              <button
                aria-label="Toggle password visibility"
                className="absolute right-2 w-9 h-9 flex items-center justify-center text-outline hover:text-on-surface transition-colors focus:outline-none rounded"
                type="button"
                onClick={() => setShowPassword(!showPassword)}
              >
                <span className="material-symbols-outlined text-[20px]">
                  {showPassword ? "visibility_off" : "visibility"}
                </span>
              </button>
            </div>
          </div>

          {/* Controls Row: Rigid Industrial Checkbox & Forgot Password */}
          <div className="flex items-center justify-between pt-space-2">
            <label className="flex items-center gap-space-8 cursor-pointer select-none group min-h-[48px] py-1">
              <input className="peer sr-only" id="remember-device" type="checkbox" />
              <div className="w-[22px] h-[22px] border-2 border-primary rounded-sm bg-surface-container-lowest peer-checked:bg-primary-container peer-checked:border-primary-container flex items-center justify-center transition-colors">
                <span className="material-symbols-outlined text-on-primary text-[18px] opacity-0 peer-checked:opacity-100 font-bold">
                  check
                </span>
              </div>
              <span className="font-body-md text-body-md text-on-surface group-hover:text-primary font-medium">
                Keep Terminal Session Active
              </span>
            </label>
            <Link
              className="font-body-sm text-body-sm text-primary hover:text-secondary font-semibold underline underline-offset-4 decoration-outline-variant"
              to="/auth/recover-password"
            >
              Forgot Password?
            </Link>
          </div>

          {/* Primary Operational Action */}
          <div className="flex flex-col gap-space-12 pt-space-4">
            <button
              className={`w-full h-[52px] px-space-16 text-on-primary rounded font-headline-md text-headline-md tracking-wide flex items-center justify-center gap-space-8 transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-container ${authSuccess ? "bg-tertiary-container" : "bg-primary-container hover:bg-[#1F3752] active:bg-[#0E1A29]"}`}
              type="submit"
              disabled={isAuthenticating || authSuccess}
            >
              {isAuthenticating ? (
                <>
                  <span className="material-symbols-outlined text-[20px] animate-spin">
                    refresh
                  </span>
                  <span>AUTHENTICATING NODE...</span>
                </>
              ) : authSuccess ? (
                <>
                  <span className="material-symbols-outlined text-[20px] text-tertiary-fixed">
                    check_circle
                  </span>
                  <span>AUTH_SUCCESS // REDIRECTING</span>
                </>
              ) : (
                <>
                  <span className="material-symbols-outlined text-[20px]">login</span>
                  <span>Sign In to Terminal</span>
                </>
              )}
            </button>

            {/* Alternative Enterprise SSO Button */}
            <Link
              className="w-full h-[48px] px-space-16 bg-surface-container-lowest hover:bg-surface-container border-2 border-primary-container text-primary rounded font-headline-md text-[15px] flex items-center justify-center gap-space-8 transition-colors focus:outline-none"
              to="/auth/signup"
            >
              <span className="material-symbols-outlined text-[20px]">corporate_fare</span>
              <span>Register New Operator</span>
            </Link>
          </div>
        </form>

        {/* Security Hardware Token & Status Badges Strip */}
        <div className="mt-space-24 pt-space-16 border-t border-outline-variant/60 flex flex-wrap items-center justify-between gap-space-8">
          <div className="flex items-center gap-space-4 px-space-8 py-1 bg-[#EDF5F0] rounded border border-[#3C8558]/40">
            <span className="material-symbols-outlined text-[#3C8558] text-[16px]">
              verified_user
            </span>
            <span className="font-mono-sm text-mono-sm text-[#3C8558] font-bold">
              [✓] ENCRYPTED_TLS_1.3
            </span>
          </div>
          <div className="flex items-center gap-space-4 px-space-8 py-1 bg-surface-container-high rounded border border-outline-variant">
            <span className="material-symbols-outlined text-on-surface-variant text-[16px]">
              usb
            </span>
            <span className="font-mono-sm text-mono-sm text-on-surface-variant font-bold">
              [YUBIKEY FIDO2 READY]
            </span>
          </div>
        </div>
      </div>

      {/* Terminal Dispatch Footer Card / Telemetry Notice */}
      <div className="w-full bg-surface-container rounded border border-outline-variant/60 p-space-12 flex flex-col gap-space-4 text-on-surface-variant">
        <div className="flex flex-wrap items-center justify-between font-mono-sm text-[11px] font-semibold tracking-wider text-outline">
          <span>NODE: US-EAST-DOCK-04</span>
          <span>GATEWAY: BMT-809</span>
          <span>SESSION_TTL: 08:00:00</span>
        </div>
        <p className="font-body-sm text-[11px] leading-tight text-on-surface-variant/80">
          Strict access controlled under federal logistics data standards. Authorized dock personnel
          and automated AMR operators only. All interaction packets are cryptographically signed and
          stored in physical ledger storage.
        </p>
      </div>

      {/* Quick Help & Network Diagnostic Indicators */}
      <div className="flex items-center justify-center gap-space-16 text-outline py-space-4">
        <a
          className="font-mono-sm text-mono-sm text-on-surface-variant hover:text-primary flex items-center gap-space-4 transition-colors"
          href="#"
        >
          <span className="material-symbols-outlined text-[16px]">support_agent</span>
          <span>Terminal Dispatch Support</span>
        </a>
        <span className="text-outline-variant">•</span>
        <a
          className="font-mono-sm text-mono-sm text-on-surface-variant hover:text-primary flex items-center gap-space-4 transition-colors"
          href="#"
        >
          <span className="material-symbols-outlined text-[16px]">router</span>
          <span>Network Diagnostics</span>
        </a>
      </div>
    </div>
  );
}
