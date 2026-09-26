import { FixtureSwitcher } from "../components/today/FixtureSwitcher";
import { TodayPage } from "../components/today/TodayPage";
import { FIXTURE_STATES, loadToday } from "../lib/today/load";

const showSwitcher = process.env.NODE_ENV !== "production";

export default async function Home({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const requested = (await searchParams).state;
  const state = showSwitcher && typeof requested === "string" ? requested : "ready";
  return (
    <TodayPage
      result={loadToday(state)}
      switcher={showSwitcher ? <FixtureSwitcher states={FIXTURE_STATES} current={state} /> : undefined}
    />
  );
}
