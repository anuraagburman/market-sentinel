import Link from "next/link";

export default function Investigate() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      <h1 className="text-3xl font-semibold tracking-tight">Investigate</h1>
      <p className="mt-4">Placeholder: stock detail and the evidence trail aren&apos;t built yet.</p>
      <p className="mt-4"><Link href="/" className="text-accent underline underline-offset-2">Back to Today</Link></p>
    </main>
  );
}
