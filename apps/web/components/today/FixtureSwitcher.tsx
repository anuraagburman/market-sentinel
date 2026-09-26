import Link from "next/link";

/** Development and tests only: picks which fixture state Today renders. */
export function FixtureSwitcher({ states, current }: { states: string[]; current: string }) {
  return (
    <nav aria-label="Fixture state (development only)" className="mb-6 rounded border border-dashed border-rule p-2 text-xs">
      <span className="mr-2 font-mono text-muted">fixture:</span>
      <ul className="inline-flex flex-wrap gap-x-3 gap-y-1">
        {states.map((state) => (
          <li key={state}>
            <Link href={`/?state=${state}`} aria-current={state === current ? "page" : undefined}
              className={state === current ? "font-semibold underline" : "text-accent"}>
              {state}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
