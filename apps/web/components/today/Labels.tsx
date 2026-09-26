import type { EvidenceStatus } from "../../lib/today/types";

export function WarningIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 16 16" className="inline-block size-4 shrink-0 align-[-3px]" fill="currentColor">
      <path d="M8 1.5 15 14H1L8 1.5Zm-.75 4.75v4h1.5v-4h-1.5Zm0 5.25v1.5h1.5v-1.5h-1.5Z" />
    </svg>
  );
}

type Kind = "fact" | "calculation" | "interpretation";
const KIND_TEXT: Record<Kind, string> = { fact: "Fact", calculation: "Calculation", interpretation: "Interpretation" };
const KIND_STYLE: Record<Kind, string> = {
  fact: "border-ink text-ink",
  calculation: "border-accent text-accent",
  interpretation: "border-muted border-dashed text-muted",
};

/** Text label that says what kind of statement follows; never color alone. */
export function KindLabel({ kind }: { kind: Kind }) {
  return (
    <span className={`mr-2 inline-block rounded-sm border px-1.5 text-[0.7rem] font-semibold uppercase leading-5 tracking-wide ${KIND_STYLE[kind]}`}>
      {KIND_TEXT[kind]}
    </span>
  );
}

const EVIDENCE_TEXT: Record<EvidenceStatus, string> = {
  supported: "Supported",
  partial: "Partial",
  contested: "Contested — sources disagree",
  insufficient: "Insufficient",
};

export function EvidenceStatusLabel({ status }: { status: EvidenceStatus }) {
  const warn = status === "contested" || status === "insufficient";
  return (
    <p className={`inline-flex items-center gap-1 rounded-sm px-2 py-0.5 text-sm ${warn ? "bg-warn-soft text-warn" : "bg-accent-soft text-ink"}`}>
      {warn && <WarningIcon />}
      <span>Evidence: {EVIDENCE_TEXT[status]}</span>
    </p>
  );
}
