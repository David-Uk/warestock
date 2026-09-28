import { useState } from "react";
import { Link } from "react-router-dom";

interface FieldProps {
  id: string;
  label: string;
  icon: string;
  type: string;
  placeholder: string;
  value: string;
  onChange: (v: string) => void;
  toggleLabel?: string;
  onToggle?: () => void;
}

function AuthField({
  id,
  label,
  icon,
  type,
  placeholder,
  value,
  onChange,
  toggleLabel,
  onToggle,
}: FieldProps) {
  return (
    <div className="flex flex-col gap-space-4">
      <label
        className="font-label-caps text-label-caps text-primary tracking-wider uppercase flex items-center gap-space-4"
        htmlFor={id}
      >
        <span className="material-symbols-outlined text-[16px] text-primary">{icon}</span>
        {label}
      </label>
      <div className="relative flex items-center">
        <input
          className="w-full h-[48px] px-space-12 pr-space-12 bg-surface-container-lowest border-2 border-[#969288] focus:border-primary-container focus:bg-[#FAF3E6] focus:outline-none rounded font-mono-md text-mono-md text-on-surface transition-colors placeholder:text-outline-variant"
          id={id}
          placeholder={placeholder}
          required
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
        {onToggle && (
          <button
            aria-label={toggleLabel ?? "Toggle password visibility"}
            className="absolute right-space-8 w-9 h-9 flex items-center justify-center text-outline hover:text-on-surface transition-colors rounded"
            type="button"
            onClick={onToggle}
          >
            <span className="material-symbols-outlined text-[20px]">
              {type === "password" ? "visibility" : "visibility_off"}
            </span>
          </button>
        )}
      </div>
    </div>
  );
}

export default function Signup() {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  return (
    <div className="w-full max-w-[520px] flex flex-col gap-space-16">
      {/* Registration Terminal Card */}
      <div className="w-full bg-surface-container-lowest rounded border-2 border-outline-variant/80 shadow-md p-space-24 sm:p-space-32 flex flex-col relative overflow-hidden">
        <div className="absolute top-0 left-0 right-0 h-1.5 bg-primary-container"></div>

        {/* Brand Header */}
        <div className="flex items-start gap-space-16 pb-space-20 border-b border-outline-variant/50">
          <div className="w-14 h-14 bg-primary-container rounded flex items-center justify-center shrink-0 shadow-sm">
            <span className="material-symbols-outlined text-secondary-fixed text-[28px]">
              person_add
            </span>
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

        {/* Title */}
        <div className="pt-space-20 pb-space-16">
          <h1 className="font-headline-md text-headline-md text-on-surface">Register Operator</h1>
          <p className="font-body-sm text-body-sm text-on-surface-variant mt-space-4">
            Provision a new operator credential bound to your organization and assigned terminal
            stations.
          </p>
        </div>

        <form className="flex flex-col gap-space-20" onSubmit={(e) => e.preventDefault()}>
          <AuthField
            id="signup-name"
            label="Full Name / Operator"
            icon="badge"
            type="text"
            placeholder="e.g. Jordan Reyes"
            value={fullName}
            onChange={setFullName}
          />
          <AuthField
            id="signup-email"
            label="Corporate Email / Employee Badge ID"
            icon="mail"
            type="email"
            placeholder="e.g. OP-884291@warestock.io"
            value={email}
            onChange={setEmail}
          />
          <AuthField
            id="signup-password"
            label="Access Code (Min 8 Chars)"
            icon="key"
            type={showPassword ? "text" : "password"}
            placeholder="••••••••"
            value={password}
            onChange={setPassword}
            onToggle={() => setShowPassword(!showPassword)}
            toggleLabel={showPassword ? "Hide access code" : "Show access code"}
          />
          <AuthField
            id="signup-confirm"
            label="Confirm Access Code"
            icon="verified_user"
            type={showConfirm ? "text" : "password"}
            placeholder="••••••••"
            value={confirm}
            onChange={setConfirm}
            onToggle={() => setShowConfirm(!showConfirm)}
            toggleLabel={showConfirm ? "Hide confirmation" : "Show confirmation"}
          />

          <div className="flex flex-col gap-space-12 pt-space-4">
            <button
              className="w-full h-[52px] px-space-16 bg-primary-container hover:bg-[#1F3752] active:bg-[#0E1A29] text-on-primary rounded font-headline-md text-headline-md tracking-wide flex items-center justify-center gap-space-8 transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-container"
              type="submit"
            >
              <span className="material-symbols-outlined text-[20px]">person_add</span>
              <span>Create Operator Account</span>
            </button>
          </div>
        </form>

        {/* Status Strip */}
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

      {/* Existing Account Footer */}
      <div className="w-full bg-surface-container rounded border border-outline-variant/60 p-space-12 flex flex-wrap items-center justify-between gap-space-8 text-on-surface-variant">
        <span className="font-body-sm text-body-sm">Already provisioned an operator account?</span>
        <Link
          className="font-body-sm text-body-sm text-primary hover:text-secondary font-semibold underline underline-offset-4 decoration-outline-variant"
          to="/auth/login"
        >
          Return to Sign In
        </Link>
      </div>
    </div>
  );
}
