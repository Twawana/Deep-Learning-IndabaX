import { useEffect, useId, useState } from "react";

const PREMIUM_PRICE = "N$89";
const PREMIUM_PERIOD = "per month";

function onlyDigits(value) {
  return String(value || "").replace(/\D/g, "");
}

function formatCardNumber(value) {
  const digits = onlyDigits(value).slice(0, 16);
  return digits.replace(/(\d{4})(?=\d)/g, "$1 ").trim();
}

function formatExpiry(value) {
  const digits = onlyDigits(value).slice(0, 4);
  if (digits.length <= 2) return digits;
  return `${digits.slice(0, 2)}/${digits.slice(2)}`;
}

function detectBrand(digits) {
  if (/^4/.test(digits)) return "Visa";
  if (/^5[1-5]/.test(digits) || /^2[2-7]/.test(digits)) return "Mastercard";
  if (/^3[47]/.test(digits)) return "Amex";
  return "Card";
}

/** Basic Luhn check so the checkout feels real (demo only). */
function luhnOk(digits) {
  if (digits.length < 13 || digits.length > 19) return false;
  let sum = 0;
  let alt = false;
  for (let i = digits.length - 1; i >= 0; i -= 1) {
    let n = Number(digits[i]);
    if (alt) {
      n *= 2;
      if (n > 9) n -= 9;
    }
    sum += n;
    alt = !alt;
  }
  return sum % 10 === 0;
}

function expiryOk(mmYy) {
  const m = mmYy.match(/^(\d{2})\/(\d{2})$/);
  if (!m) return false;
  const month = Number(m[1]);
  const year = 2000 + Number(m[2]);
  if (month < 1 || month > 12) return false;
  const now = new Date();
  const exp = new Date(year, month, 0, 23, 59, 59);
  return exp >= now;
}

export default function PremiumCheckout({
  open,
  onClose,
  onConfirm,
  busy = false,
  farmerName = "",
}) {
  const titleId = useId();
  const [cardName, setCardName] = useState(farmerName || "");
  const [cardNumber, setCardNumber] = useState("");
  const [expiry, setExpiry] = useState("");
  const [cvc, setCvc] = useState("");
  const [billingEmail, setBillingEmail] = useState("");
  const [country, setCountry] = useState("Namibia");
  const [agree, setAgree] = useState(false);
  const [error, setError] = useState("");
  const [step, setStep] = useState("form"); // form | processing | done

  useEffect(() => {
    if (!open) return;
    setCardName(farmerName || "");
    setCardNumber("");
    setExpiry("");
    setCvc("");
    setBillingEmail("");
    setCountry("Namibia");
    setAgree(false);
    setError("");
    setStep("form");
  }, [open, farmerName]);

  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => {
      if (e.key === "Escape" && step === "form" && !busy) onClose?.();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose, step, busy]);

  if (!open) return null;

  const digits = onlyDigits(cardNumber);
  const brand = detectBrand(digits);

  const validate = () => {
    if (!cardName.trim() || cardName.trim().length < 2) {
      return "Enter the name on the card.";
    }
    if (!luhnOk(digits)) {
      return "Enter a valid card number (try 4242 4242 4242 4242 for demo).";
    }
    if (!expiryOk(expiry)) {
      return "Enter a valid future expiry (MM/YY).";
    }
    if (onlyDigits(cvc).length < 3) {
      return "Enter the 3-digit security code (CVC).";
    }
    if (billingEmail && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(billingEmail.trim())) {
      return "Billing email looks invalid.";
    }
    if (!agree) {
      return "Confirm you agree to the recurring Premium charge.";
    }
    return "";
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const problem = validate();
    if (problem) {
      setError(problem);
      return;
    }
    setError("");
    setStep("processing");

    const payment = {
      cardholder_name: cardName.trim(),
      last4: digits.slice(-4),
      brand,
      exp_month: Number(expiry.slice(0, 2)),
      exp_year: 2000 + Number(expiry.slice(3)),
      billing_email: billingEmail.trim() || undefined,
      billing_country: country,
      amount_label: `${PREMIUM_PRICE} ${PREMIUM_PERIOD}`,
      demo: true,
    };

    // Brief pause so the checkout feels like a real payment hop.
    await new Promise((r) => setTimeout(r, 1400));

    const result = await onConfirm?.(payment);
    if (result?.ok) {
      setStep("done");
      return;
    }
    setStep("form");
    setError(result?.message || "Payment could not be completed. Try again.");
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-veld-950/45 p-3 sm:items-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      onClick={(e) => {
        if (e.target === e.currentTarget && step === "form" && !busy) onClose?.();
      }}
    >
      <div className="max-h-[92vh] w-full max-w-md overflow-y-auto rounded-2xl bg-white shadow-xl ring-1 ring-veld-100">
        <div className="border-b border-veld-100 bg-gradient-to-br from-veld-50 to-sun-100/60 px-4 py-3.5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wide text-veld-600">
                Farmar Premium
              </p>
              <h2 id={titleId} className="font-display text-xl text-ink">
                Complete payment
              </h2>
              <p className="mt-0.5 text-sm text-ink-muted">
                {PREMIUM_PRICE} {PREMIUM_PERIOD} · cancel anytime
              </p>
            </div>
            {step === "form" ? (
              <button
                type="button"
                onClick={onClose}
                className="rounded-lg px-2 py-1 text-sm font-semibold text-ink-muted hover:bg-white/70"
                aria-label="Close checkout"
              >
                Close
              </button>
            ) : null}
          </div>
        </div>

        {step === "processing" ? (
          <div className="flex flex-col items-center gap-3 px-6 py-12 text-center">
            <div className="h-10 w-10 animate-spin rounded-full border-2 border-veld-200 border-t-veld-700" />
            <p className="text-sm font-semibold text-ink">Processing payment…</p>
            <p className="text-xs text-ink-muted">
              Contacting secure checkout. Do not close this window.
            </p>
          </div>
        ) : null}

        {step === "done" ? (
          <div className="space-y-4 px-5 py-8 text-center">
            <p className="font-display text-2xl text-veld-800">You're Premium</p>
            <p className="text-sm text-ink-muted">
              Payment received for card ending ····{digits.slice(-4)}. Detailed Oryx
              grazing advice is unlocked on this account.
            </p>
            <button
              type="button"
              onClick={onClose}
              className="w-full rounded-xl bg-veld-800 py-3 text-sm font-semibold text-white"
            >
              Done
            </button>
          </div>
        ) : null}

        {step === "form" ? (
          <form onSubmit={handleSubmit} className="space-y-3.5 px-4 py-4">
            <div className="rounded-xl border border-sun-100 bg-sun-100/50 px-3 py-2 text-[11px] leading-relaxed text-sun-600">
              Demo checkout for Farmar — no real charge is made. Use test card{" "}
              <span className="font-semibold">4242 4242 4242 4242</span>, any future
              expiry, any 3-digit CVC.
            </div>

            <label className="block">
              <span className="mb-1 block text-xs font-semibold text-ink">
                Name on card
              </span>
              <input
                className="field-input"
                autoComplete="cc-name"
                value={cardName}
                onChange={(e) => setCardName(e.target.value)}
                placeholder="As printed on the card"
                required
              />
            </label>

            <label className="block">
              <span className="mb-1 flex items-center justify-between text-xs font-semibold text-ink">
                Card number
                <span className="font-medium text-ink-muted">{brand}</span>
              </span>
              <input
                className="field-input font-mono tracking-wide"
                inputMode="numeric"
                autoComplete="cc-number"
                value={cardNumber}
                onChange={(e) => setCardNumber(formatCardNumber(e.target.value))}
                placeholder="4242 4242 4242 4242"
                required
              />
            </label>

            <div className="grid grid-cols-2 gap-3">
              <label className="block">
                <span className="mb-1 block text-xs font-semibold text-ink">
                  Expiry
                </span>
                <input
                  className="field-input font-mono"
                  inputMode="numeric"
                  autoComplete="cc-exp"
                  value={expiry}
                  onChange={(e) => setExpiry(formatExpiry(e.target.value))}
                  placeholder="MM/YY"
                  required
                />
              </label>
              <label className="block">
                <span className="mb-1 block text-xs font-semibold text-ink">CVC</span>
                <input
                  className="field-input font-mono"
                  inputMode="numeric"
                  autoComplete="cc-csc"
                  value={cvc}
                  onChange={(e) => setCvc(onlyDigits(e.target.value).slice(0, 4))}
                  placeholder="123"
                  required
                />
              </label>
            </div>

            <label className="block">
              <span className="mb-1 block text-xs font-semibold text-ink">
                Billing email <span className="font-normal text-ink-muted">(optional)</span>
              </span>
              <input
                className="field-input"
                type="email"
                autoComplete="email"
                value={billingEmail}
                onChange={(e) => setBillingEmail(e.target.value)}
                placeholder="you@email.com"
              />
            </label>

            <label className="block">
              <span className="mb-1 block text-xs font-semibold text-ink">Country</span>
              <select
                className="field-input"
                value={country}
                onChange={(e) => setCountry(e.target.value)}
              >
                <option>Namibia</option>
                <option>South Africa</option>
                <option>Botswana</option>
                <option>Other</option>
              </select>
            </label>

            <label className="flex items-start gap-2 rounded-xl border border-veld-100 bg-mist px-3 py-2.5">
              <input
                type="checkbox"
                className="mt-0.5"
                checked={agree}
                onChange={(e) => setAgree(e.target.checked)}
              />
              <span className="text-xs leading-relaxed text-ink-muted">
                I authorise Farmar to charge {PREMIUM_PRICE} {PREMIUM_PERIOD} for Premium
                AI grazing advice until I cancel on Profile.
              </span>
            </label>

            {error ? (
              <p className="rounded-xl bg-red-50 px-3 py-2 text-xs font-medium text-red-800">
                {error}
              </p>
            ) : null}

            <button
              type="submit"
              disabled={busy}
              className="w-full rounded-xl bg-veld-800 py-3 text-sm font-semibold text-white disabled:opacity-60"
            >
              Pay {PREMIUM_PRICE} & unlock Premium
            </button>
            <button
              type="button"
              onClick={onClose}
              className="w-full rounded-xl border border-veld-200 bg-white py-2.5 text-sm font-semibold text-veld-800"
            >
              Cancel
            </button>
          </form>
        ) : null}
      </div>
    </div>
  );
}
