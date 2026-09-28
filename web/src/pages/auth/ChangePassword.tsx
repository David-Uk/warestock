import { useState } from "react";
import { Link } from "react-router-dom";

const NIST_CHECKS = [
  "Min 12 Characters (14)",
  "Uppercase & Numeric Mix",
  "Special Symbol Inset",
  "No Lexical Dictionary Match",
];

const POLICY_RULES = [
  {
    icon: "timer",
    strong: "Session Inactivity:",
    text: " Vehicle Mounted Terminals lock after 15 minutes of scanner dormancy.",
  },
  {
    icon: "sync_disabled",
    strong: "Credential Rotation:",
    text: " Passwords expire after 90 days. History enforces no repetition of prior 6 keys.",
  },
  {
    icon: "leak_remove",
    strong: "Isolation Boundary:",
    text: " Cross-tenant warehouse manifest reads are cryptographically fenced.",
  },
];

export default function ChangePassword() {
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [keyState, setKeyState] = useState<"idle" | "probing" | "bound">("idle");

  const enrollKey = () => {
    setKeyState("probing");
    setTimeout(() => setKeyState("bound"), 1400);
  };

  return (
    <div className="w-full max-w-xl flex flex-col">
      {/* Security Context Topstrip */}
      <div className="bg-primary-container text-on-primary rounded-t-lg p-space-12 flex flex-wrap items-center justify-between gap-space-8 shadow-sm">
        <div className="flex items-center space-x-space-8">
          <span
            className="material-symbols-outlined text-secondary-fixed text-mono-md"
            style={{ fontVariationSettings: "'FILL' 1" }}
          >
            shield_locked
          </span>
          <span className="font-mono-sm text-mono-sm tracking-widest text-primary-fixed uppercase">
            SEC_ID // PROV-AUTH-882
          </span>
        </div>
        <div className="space-x-space-16 text-primary-fixed-dim font-mono-sm text-mono-sm">
          <span>
            EPOCH: <strong className="text-on-primary font-mono-sm">1711928420</strong>
          </span>
          <span className="hidden sm:inline">
            {" "}
            NONCE: <strong className="text-on-primary font-mono-sm">0x9F4C...B21</strong>
          </span>
        </div>
      </div>

      {/* Primary Outer Shell */}
      <div className="bg-surface-container-lowest p-space-24 shadow-md rounded-b-lg flex flex-col space-y-space-20">
        {/* Header Block */}
        <div className="space-y-space-4">
          <div className="flex items-center space-x-space-8">
            <span className="px-space-8 py-space-2 bg-primary-container text-on-primary rounded font-label-caps text-label-caps uppercase tracking-wider">
              Secure Bootstrap
            </span>
            <span className="px-space-8 py-space-2 bg-surface-container-high text-on-surface font-mono-sm text-mono-sm">
              SYS-REV.4
            </span>
          </div>
          <h1 className="font-headline-lg text-headline-lg text-primary tracking-tight">
            Welcome to WareStock AI // Initial Credential Provisioning
          </h1>
          <p className="font-body-md text-body-md text-on-surface-variant">
            Configure your root-access operational credentials and bind a mandatory physical
            hardware token before accessing industrial manifests.
          </p>
        </div>

        {/* Metadata Context Bar */}
        <div className="bg-surface-container-high p-space-12 rounded-lg flex flex-col md:flex-row md:items-center justify-between gap-space-8">
          <div className="flex items-center space-x-space-8">
            <span className="material-symbols-outlined text-primary text-mono-md">person_pin</span>
            <div className="flex flex-col">
              <span className="font-label-caps text-label-caps text-on-surface-variant uppercase">
                Invitation Recipient
              </span>
              <span className="font-mono-md text-mono-md text-on-surface font-semibold">
                m.vance@apexlogistics.io
              </span>
            </div>
          </div>
          <div className="flex items-center space-x-space-8">
            <span className="material-symbols-outlined text-primary text-mono-md">domain</span>
            <div className="flex flex-col">
              <span className="font-label-caps text-label-caps text-on-surface-variant uppercase">
                Tenant Scope
              </span>
              <span className="font-mono-md text-mono-md text-on-surface font-semibold">
                Apex Global Logistics (ORG-0982)
              </span>
            </div>
          </div>
        </div>

        {/* Form & Policy Split */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-space-20">
          {/* Left: Form Fields */}
          <div className="lg:col-span-8 flex flex-col space-y-space-16">
            {/* Temporary Token */}
            <div className="flex flex-col space-y-space-4">
              <label className="font-label-caps text-label-caps text-on-surface font-semibold uppercase flex items-center justify-between">
                <span>Temporary Invitation Token</span>
                <span className="text-tertiary-container font-mono-sm flex items-center gap-space-4 font-bold">
                  <span
                    className="material-symbols-outlined text-mono-sm"
                    style={{ fontVariationSettings: "'FILL' 1" }}
                  >
                    check_circle
                  </span>
                  TOKEN_VERIFIED
                </span>
              </label>
              <div className="relative flex items-center">
                <input
                  className="w-full bg-surface-container font-mono-md text-mono-md text-on-surface py-space-12 px-space-12 rounded outline-none cursor-not-allowed select-all"
                  readOnly
                  type="text"
                  defaultValue="TOK-9921-XRF-8834-APEX"
                />
                <span className="material-symbols-outlined absolute right-space-12 text-on-surface-variant text-mono-lg pointer-events-none">
                  lock
                </span>
              </div>
            </div>

            {/* New Password */}
            <div className="flex flex-col space-y-space-4">
              <div className="flex items-center justify-between">
                <label
                  className="font-label-caps text-label-caps text-on-surface font-semibold uppercase"
                  htmlFor="password-input"
                >
                  New Strong Password
                </label>
                <span className="font-mono-sm text-mono-sm text-on-surface-variant">
                  Entropy: <span className="text-secondary font-bold">Medium (64-bit)</span>
                </span>
              </div>
              <div className="relative flex items-center">
                <input
                  className="w-full bg-surface-container-lowest font-mono-md text-mono-md text-on-surface py-space-12 px-space-12 rounded shadow-sm focus:outline-none focus:bg-surface-container-low transition-all pr-space-48"
                  id="password-input"
                  placeholder="Enter minimum 12 characters..."
                  type={showPassword ? "text" : "password"}
                  defaultValue="K9#mQv!78z9xLp"
                />
                <button
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  className="absolute right-space-12 text-on-surface-variant hover:text-on-surface flex items-center justify-center p-space-4"
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  <span className="material-symbols-outlined text-mono-md">
                    {showPassword ? "visibility_off" : "visibility"}
                  </span>
                </button>
              </div>

              {/* NIST Compliance Checklist */}
              <div className="bg-surface-container-low p-space-12 rounded flex flex-col space-y-space-8 mt-space-4">
                <div className="flex items-center justify-between">
                  <span className="font-label-caps text-label-caps text-on-surface uppercase tracking-wider">
                    NIST SP 800-63B Compliance Specification
                  </span>
                  <span className="font-mono-sm text-mono-sm text-tertiary-container font-semibold">
                    ALL CHECKS ACTIVE
                  </span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-space-4 font-mono-sm text-mono-sm">
                  {NIST_CHECKS.map((check) => (
                    <div
                      key={check}
                      className="flex items-center space-x-space-4 text-tertiary-container"
                    >
                      <span className="material-symbols-outlined text-mono-sm">check_circle</span>
                      <span>{check}</span>
                    </div>
                  ))}
                </div>
                <div className="flex items-center justify-between pt-space-4 bg-surface-container p-space-8 rounded">
                  <div className="flex items-center space-x-space-8">
                    <span className="material-symbols-outlined text-tertiary-container text-mono-sm">
                      verified_user
                    </span>
                    <span className="font-mono-sm text-mono-sm text-on-surface">
                      HIBP Credential Exposure Filter:
                    </span>
                  </div>
                  <span className="font-mono-sm text-mono-sm text-tertiary-container font-bold uppercase">
                    PASSED // 0 BREACHES
                  </span>
                </div>
              </div>
            </div>

            {/* Confirm Password */}
            <div className="flex flex-col space-y-space-4">
              <label
                className="font-label-caps text-label-caps text-on-surface font-semibold uppercase"
                htmlFor="confirm-input"
              >
                Confirm New Password
              </label>
              <div className="relative flex items-center">
                <input
                  className="w-full bg-surface-container-lowest font-mono-md text-mono-md text-on-surface py-space-12 px-space-12 rounded shadow-sm focus:outline-none focus:bg-surface-container-low transition-all pr-space-48"
                  id="confirm-input"
                  placeholder="Re-enter password to verify exact parity..."
                  type={showConfirmPassword ? "text" : "password"}
                  defaultValue="K9#mQv!78z9xLp"
                />
                <button
                  aria-label={
                    showConfirmPassword
                      ? "Hide password confirmation"
                      : "Show password confirmation"
                  }
                  className="absolute right-space-12 text-tertiary-container flex items-center justify-center p-space-4"
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                >
                  <span className="material-symbols-outlined text-mono-lg">
                    {showConfirmPassword ? "visibility_off" : "task_alt"}
                  </span>
                </button>
              </div>
            </div>

            {/* FIDO2 / Passkey Registration */}
            <div className="bg-surface-container-low p-space-16 rounded-lg flex flex-col space-y-space-12">
              <div className="flex items-start justify-between">
                <div className="flex items-center space-x-space-8">
                  <span className="p-space-8 bg-primary-container text-on-primary rounded">
                    <span className="material-symbols-outlined text-mono-lg">key</span>
                  </span>
                  <div>
                    <h3 className="font-headline-md text-headline-md text-primary">
                      Mandatory Hardware Token / Passkey Binding
                    </h3>
                    <p className="font-body-sm text-body-sm text-on-surface-variant">
                      Zero-trust policy requires a hardware authenticator for warehouse control
                      terminals.
                    </p>
                  </div>
                </div>
                <span className="bg-secondary-fixed text-on-secondary-fixed px-space-8 py-space-2 rounded font-label-caps text-label-caps font-bold">
                  REQUIRED
                </span>
              </div>
              <div
                className={`${
                  keyState === "bound" ? "bg-tertiary-fixed" : "bg-surface-container"
                } p-space-16 rounded flex flex-col sm:flex-row items-center justify-between gap-space-12 transition-colors`}
              >
                <div className="flex items-center space-x-space-12">
                  <div className="w-12 h-12 bg-surface-container-highest rounded-full flex items-center justify-center text-primary flex-shrink-0 animate-pulse">
                    <span className="material-symbols-outlined text-mono-xl">fingerprint</span>
                  </div>
                  <div>
                    <div className="font-mono-md text-mono-md text-on-surface font-semibold">
                      {keyState === "bound"
                        ? "YubiKey 5C NFC Verified (FIPS Mode)"
                        : "Physical YubiKey or Platform Biometrics"}
                    </div>
                    <div className="font-mono-sm text-mono-sm text-on-surface-variant">
                      {keyState === "idle" &&
                        "Waiting for user interaction... Tap below to initialize challenge."}
                      {keyState === "probing" &&
                        "Please touch the gold contact on your security key or present biometric scan."}
                      {keyState === "bound" &&
                        "Attestation certificate bound to UUID // FIDO2-9844-APEX-OK"}
                    </div>
                  </div>
                </div>
                <button
                  className="w-full sm:w-auto px-space-16 py-space-8 bg-surface-container-lowest text-primary hover:bg-surface-container-highest font-mono-md text-mono-md font-bold rounded shadow-sm flex items-center justify-center space-x-space-4 disabled:opacity-70"
                  type="button"
                  disabled={keyState !== "idle"}
                  onClick={enrollKey}
                >
                  {keyState === "bound" ? (
                    <>
                      <span className="material-symbols-outlined text-mono-md text-tertiary-container">
                        check_circle
                      </span>
                      <span>Bound</span>
                    </>
                  ) : keyState === "probing" ? (
                    <span>Probing...</span>
                  ) : (
                    <>
                      <span className="material-symbols-outlined text-mono-md">usb</span>
                      <span>Register Key</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>

          {/* Right: Operational Policy Sidebar */}
          <div className="lg:col-span-4 flex flex-col space-y-space-12">
            <div className="relative bg-primary-container rounded-lg overflow-hidden h-36 flex flex-col justify-end p-space-12 text-on-primary">
              <div className="absolute inset-0 bg-gradient-to-br from-primary via-primary-container to-primary/80"></div>
              <div className="absolute -right-8 -bottom-8 w-32 h-32 rounded-full bg-secondary/20 blur-2xl pointer-events-none"></div>
              <div className="relative z-10">
                <span className="font-label-caps text-label-caps uppercase tracking-wider text-secondary-fixed">
                  FACILITY PROTOCOL // ZONE-4
                </span>
                <div className="font-mono-md text-mono-md font-bold">
                  Industrial Operations Gateway
                </div>
              </div>
            </div>

            <div className="bg-surface-container p-space-16 rounded-lg flex flex-col space-y-space-12">
              <div className="flex items-center space-x-space-8">
                <span className="material-symbols-outlined text-primary text-mono-lg">policy</span>
                <h4 className="font-headline-md text-headline-md text-on-surface">
                  Security Constraints
                </h4>
              </div>
              <ul className="space-y-space-8 font-body-sm text-body-sm text-on-surface-variant">
                {POLICY_RULES.map((rule) => (
                  <li key={rule.strong} className="flex items-start space-x-space-8">
                    <span className="material-symbols-outlined text-mono-sm text-primary mt-space-2">
                      {rule.icon}
                    </span>
                    <span>
                      <strong>{rule.strong}</strong>
                      {rule.text}
                    </span>
                  </li>
                ))}
              </ul>
              <div className="bg-surface-container-high p-space-8 rounded flex items-center justify-between text-on-surface-variant font-mono-sm text-mono-sm">
                <span>COMPLIANCE:</span>
                <span className="font-bold text-on-surface">SOC2 TYPE-II / ISO 27001</span>
              </div>
            </div>

            <div className="bg-surface-container-low p-space-12 rounded-lg flex flex-col space-y-space-4">
              <span className="font-label-caps text-label-caps text-on-surface-variant uppercase">
                Invitation Discrepancy?
              </span>
              <p className="font-body-sm text-body-sm text-on-surface-variant">
                If this token does not correspond to your assigned terminal station, notify the dock
                supervisor.
              </p>
              <a
                className="font-mono-sm text-mono-sm text-primary underline font-semibold flex items-center space-x-space-2 pt-space-2"
                href="#security-ticket"
              >
                <span>Open Security Ticket</span>
                <span className="material-symbols-outlined text-mono-sm">arrow_forward</span>
              </a>
            </div>
          </div>
        </div>

        {/* Bottom Actions Footer */}
        <div className="pt-space-16 flex flex-col-reverse sm:flex-row items-center justify-between gap-space-12 bg-surface-container-lowest">
          <button
            className="w-full sm:w-auto px-space-20 py-space-12 bg-surface-container text-on-surface hover:bg-surface-container-high font-headline-md text-headline-md font-semibold rounded flex items-center justify-center space-x-space-8"
            type="button"
          >
            <span className="material-symbols-outlined text-mono-lg">restart_alt</span>
            <span>Request Token Re-issuance</span>
          </button>
          <Link
            className="w-full sm:w-auto px-space-24 py-space-12 bg-primary text-on-primary hover:bg-primary-container font-headline-md text-headline-md font-semibold rounded shadow-md flex items-center justify-center space-x-space-8"
            to="/auth/login"
          >
            <span className="material-symbols-outlined text-mono-lg">enhanced_encryption</span>
            <span>Confirm Password &amp; Enroll Key</span>
          </Link>
        </div>
      </div>
    </div>
  );
}
