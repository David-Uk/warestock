import { useState } from "react";
import { Link } from "react-router-dom";

export default function RecoverPassword() {
  const [submitted, setSubmitted] = useState(false);

  return (
    <div className="flex flex-col w-full max-w-5xl mx-auto py-space-12">
      {/* Gate Status Bar */}
      <div className="flex items-center justify-between px-space-8 mb-space-16">
        <div className="flex items-center gap-space-8">
          <span className="font-mono-sm text-mono-sm text-outline tracking-wider uppercase">
            GATE_SEC // 002
          </span>
          <span className="font-mono-sm text-mono-sm text-outline/50">/</span>
          <span className="font-label-caps text-label-caps text-primary uppercase tracking-widest bg-surface-container-high px-space-8 py-space-2 rounded">
            Credential Recovery
          </span>
        </div>
        <div className="hidden sm:flex items-center gap-space-12 font-mono-sm text-mono-sm text-outline">
          <span className="flex items-center gap-space-4">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-secondary"></span>
            ENCR_LVL: RSA-4096
          </span>
          <span>|</span>
          <span>NODE: US-EAST-DOCK-04</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-space-24">
        {/* Left: Recovery Card */}
        <div className="lg:col-span-7 flex flex-col gap-space-16">
          <div className="bg-surface-container-lowest rounded-xl shadow-md p-space-32 flex flex-col gap-space-24 relative overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-1.5 bg-primary-container"></div>

            <div className="flex items-start gap-space-16">
              <div className="w-14 h-14 rounded-lg bg-surface-container-high flex items-center justify-center shrink-0">
                <span className="material-symbols-outlined text-primary text-[32px]">
                  lock_reset
                </span>
              </div>
              <div className="flex flex-col gap-space-4">
                <span className="font-mono-sm text-mono-sm text-secondary tracking-widest uppercase font-semibold">
                  AUTH PROTOCOL REC-81
                </span>
                <h1 className="font-headline-lg text-headline-lg text-primary">
                  Reset Your Account Password
                </h1>
                <p className="font-body-md text-body-md text-on-surface-variant leading-relaxed">
                  Enter your registered corporate email address or tenant-assigned identity. We will
                  dispatch an encrypted reset link or terminal re-activation token.
                </p>
              </div>
            </div>

            <form
              className="flex flex-col gap-space-20"
              id="recoveryForm"
              onSubmit={(e) => {
                e.preventDefault();
                setSubmitted(true);
              }}
            >
              {/* Read-only Tenant Realm */}
              <div className="flex flex-col gap-space-4">
                <label
                  className="font-label-caps text-label-caps text-on-surface-variant uppercase tracking-wider"
                  htmlFor="tenantDomain"
                >
                  Organization Gateway Realm
                </label>
                <div className="flex items-center bg-surface-container-low rounded-lg px-space-12 py-space-8">
                  <span className="material-symbols-outlined text-outline text-[18px] mr-space-8">
                    dns
                  </span>
                  <input
                    className="w-full bg-transparent font-mono-md text-mono-md text-on-surface focus:outline-none cursor-default selection:bg-transparent"
                    id="tenantDomain"
                    readOnly
                    type="text"
                    defaultValue="apexlogistics.warestock.cloud"
                  />
                  <span className="font-mono-sm text-mono-sm text-outline uppercase bg-surface-container px-space-4 py-space-2 rounded shrink-0">
                    VERIFIED DOMAIN
                  </span>
                </div>
              </div>

              {/* Credential Field */}
              <div className="flex flex-col gap-space-4">
                <div className="flex items-center justify-between">
                  <label
                    className="font-label-caps text-label-caps text-primary uppercase tracking-wider"
                    htmlFor="userCredential"
                  >
                    Corporate Email or Directory Username
                  </label>
                  <span className="font-mono-sm text-mono-sm text-outline">UPN / RFID_UID</span>
                </div>
                <div className="relative flex items-center">
                  <span className="material-symbols-outlined absolute left-space-12 text-outline text-[20px] pointer-events-none">
                    badge
                  </span>
                  <input
                    className="w-full h-12 pl-space-48 pr-space-12 rounded-lg bg-surface-container-low font-mono-md text-mono-md text-on-surface placeholder:text-outline/70 focus:bg-surface-container-lowest focus:shadow-sm focus:outline-none transition-colors"
                    id="userCredential"
                    placeholder="e.g. j.doe@apexlogistics.com or WMS-8831"
                    required
                    type="text"
                  />
                </div>
                <p className="font-body-sm text-body-sm text-outline">
                  Directory federation via Okta, Entra ID, or Local Terminal Vault.
                </p>
              </div>

              {/* Actions */}
              <div className="flex flex-col gap-space-12 pt-space-8">
                <button
                  className="w-full min-h-touch-target-min bg-primary-container text-on-primary hover:bg-primary font-headline-md text-headline-md rounded-lg flex items-center justify-center gap-space-8 shadow-sm transition-colors active:translate-y-[1px]"
                  type="submit"
                >
                  <span className="material-symbols-outlined text-[20px]">send_time_extension</span>
                  <span>Send Secure Reset Instructions</span>
                </button>
                <button
                  className="w-full min-h-touch-target-min bg-surface-container-low hover:bg-surface-container text-primary font-body-md text-body-md font-semibold rounded-lg flex items-center justify-center gap-space-8 transition-colors"
                  type="button"
                >
                  <span className="material-symbols-outlined text-[20px] text-secondary">
                    supervisor_account
                  </span>
                  <span>Request Shift Supervisor Hardware PIN Override</span>
                </button>
              </div>
            </form>

            {/* Dispatch Confirmation Notice */}
            {submitted && (
              <div className="p-space-16 rounded-lg bg-tertiary-container text-on-tertiary flex items-start gap-space-12">
                <span className="material-symbols-outlined text-tertiary-fixed text-[24px]">
                  mark_email_read
                </span>
                <div className="flex flex-col gap-space-2">
                  <span className="font-mono-sm text-mono-sm text-tertiary-fixed font-bold uppercase tracking-wider">
                    DISPATCH_CONFIRMED // TOKEN_GENERATED
                  </span>
                  <p className="font-body-sm text-body-sm text-on-tertiary/90">
                    An encrypted one-time recovery token has been transmitted to the authorized
                    secure gateway endpoint. Session expires in 15 minutes.
                  </p>
                </div>
              </div>
            )}

            {/* Return Footer */}
            <div className="pt-space-16 flex items-center justify-between">
              <Link
                className="inline-flex items-center gap-space-8 font-body-md text-body-md font-semibold text-primary hover:text-secondary transition-colors"
                to="/auth/login"
              >
                <span className="material-symbols-outlined text-[18px]">arrow_back</span>
                <span>Return to Login</span>
              </Link>
              <span className="font-mono-sm text-mono-sm text-outline">SYS_REV: v4.19.2</span>
            </div>
          </div>
        </div>

        {/* Right: Compliance & Dispatch Panels */}
        <div className="lg:col-span-5 flex flex-col gap-space-16">
          <div className="bg-surface-container rounded-xl p-space-24 shadow-sm flex flex-col gap-space-16">
            <div className="flex items-center gap-space-8">
              <span className="material-symbols-outlined text-secondary text-[22px]">policy</span>
              <h2 className="font-headline-md text-headline-md text-primary">
                Compliance Directives
              </h2>
            </div>

            <div className="bg-surface-container-high rounded-lg p-space-16 flex flex-col gap-space-8">
              <div className="flex items-center gap-space-8">
                <span className="material-symbols-outlined text-secondary text-[18px]">
                  warning
                </span>
                <span className="font-label-caps text-label-caps text-primary tracking-wider uppercase">
                  Elevated Privilege Tier Notice
                </span>
              </div>
              <p className="font-body-sm text-body-sm text-on-surface-variant leading-relaxed">
                Security Notice: Superadmin and System Admin password resets require multi-factor
                attestation or hardware security key (FIDO2) re-enrollment. Self-service email reset
                is prohibited for Tier-3 Clearance.
              </p>
            </div>

            <div className="flex flex-col gap-space-12 pt-space-8">
              <span className="font-mono-sm text-mono-sm text-outline tracking-wider uppercase">
                OPERATIONAL OVERVIEW
              </span>
              <div className="flex items-center justify-between p-space-12 bg-surface-container-lowest rounded-lg">
                <div className="flex items-center gap-space-8">
                  <span className="material-symbols-outlined text-outline text-[20px]">timer</span>
                  <span className="font-body-sm text-body-sm text-on-surface">
                    Token Expiration Window
                  </span>
                </div>
                <span className="font-mono-sm text-mono-sm font-semibold text-primary">
                  900 SECONDS
                </span>
              </div>
              <div className="flex items-center justify-between p-space-12 bg-surface-container-lowest rounded-lg">
                <div className="flex items-center gap-space-8">
                  <span className="material-symbols-outlined text-outline text-[20px]">
                    encrypted
                  </span>
                  <span className="font-body-sm text-body-sm text-on-surface">
                    Terminal Re-activation
                  </span>
                </div>
                <span className="font-mono-sm text-mono-sm font-semibold text-primary">
                  BARCODE_PDF417
                </span>
              </div>
              <div className="flex items-center justify-between p-space-12 bg-surface-container-lowest rounded-lg">
                <div className="flex items-center gap-space-8">
                  <span className="material-symbols-outlined text-outline text-[20px]">hub</span>
                  <span className="font-body-sm text-body-sm text-on-surface">
                    Active Session Purge
                  </span>
                </div>
                <span className="font-mono-sm text-mono-sm font-semibold text-secondary">
                  MANDATORY
                </span>
              </div>
            </div>
          </div>

          <div className="bg-surface-container-lowest rounded-xl p-space-20 shadow-sm flex flex-col gap-space-12">
            <div className="flex items-center justify-between">
              <span className="font-label-caps text-label-caps text-outline uppercase tracking-wider">
                Terminal Dispatch State
              </span>
              <span className="font-mono-sm text-mono-sm text-tertiary-container bg-tertiary-fixed px-space-8 py-space-2 rounded font-bold">
                READY
              </span>
            </div>
            <div className="flex items-center gap-space-16">
              <div className="w-16 h-16 bg-surface-container-low rounded-lg flex items-center justify-center shrink-0">
                <span className="material-symbols-outlined text-primary text-[36px]">
                  qr_code_2
                </span>
              </div>
              <div className="flex flex-col gap-space-2">
                <span className="font-mono-md text-mono-md font-semibold text-primary">
                  Floor Scanner Recovery
                </span>
                <p className="font-body-sm text-body-sm text-outline">
                  VMTs &amp; Handhelds can pair via supervisor authorization token at Dock Charging
                  Station #12.
                </p>
              </div>
            </div>
          </div>

          <div className="px-space-8 flex items-center justify-between text-outline font-mono-sm text-mono-sm">
            <span>SECURITY ENCLAVE 09</span>
            <span>CRC32: 0x8FA47B10</span>
          </div>
        </div>
      </div>
    </div>
  );
}
