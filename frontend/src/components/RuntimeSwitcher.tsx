import type {
  RuntimeProfile,
  RuntimeState,
  ScenarioPack,
} from "../types";

interface RuntimeSwitcherProps {
  runtime: RuntimeState | null;
  busy: boolean;
  onSelect: (scenarioPack: ScenarioPack, runtimeProfile: RuntimeProfile) => void;
}

export function RuntimeSwitcher({
  runtime,
  busy,
  onSelect,
}: RuntimeSwitcherProps) {
  if (!runtime) {
    return null;
  }

  const selectPack = (pack: ScenarioPack) => {
    const preferred =
      pack === "learning"
        ? runtime.runtime_profiles.find(
            (item) =>
              item.id === "fabric_live" &&
              item.available &&
              item.supported_packs.includes(pack),
          )
        : undefined;
    const fallback = runtime.runtime_profiles.find(
      (item) => item.available && item.supported_packs.includes(pack),
    );
    const profile = preferred?.id ?? fallback?.id ?? "local";
    onSelect(pack, profile);
  };

  return (
    <section className="runtime-switcher" aria-label="Demo runtime controls">
      <div className="runtime-control">
        <span>System</span>
        <div className="segmented-control">
          {runtime.scenario_packs.map((pack) => (
            <button
              key={pack.id}
              type="button"
              className={runtime.scenario_pack === pack.id ? "is-active" : ""}
              aria-pressed={runtime.scenario_pack === pack.id}
              disabled={busy || !runtime.switching_enabled || !pack.enabled}
              title={pack.detail}
              onClick={() => selectPack(pack.id)}
            >
              {pack.label}
              {!pack.enabled && <small> disabled</small>}
            </button>
          ))}
        </div>
      </div>

      <div className="runtime-control runtime-profile-control">
        <span>Proof runtime</span>
        <div className="runtime-profile-list">
          {runtime.runtime_profiles.map((profile) => (
            <button
              key={profile.id}
              type="button"
              className={runtime.runtime_profile === profile.id ? "is-active" : ""}
              aria-pressed={runtime.runtime_profile === profile.id}
              disabled={
                busy ||
                !runtime.switching_enabled ||
                !profile.available ||
                !profile.supported_packs.includes(runtime.scenario_pack)
              }
              title={profile.detail}
              onClick={() =>
                onSelect(runtime.scenario_pack, profile.id)
              }
            >
              <strong>{profile.label}</strong>
              <small>{profile.cloud ? "cloud" : "no cloud"}</small>
            </button>
          ))}
        </div>
      </div>

      <p>{runtime.runtime_profiles.find((item) => item.id === runtime.runtime_profile)?.detail}</p>
    </section>
  );
}
