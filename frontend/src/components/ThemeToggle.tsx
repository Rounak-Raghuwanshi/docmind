import { Monitor, Moon, Sun } from "lucide-react";
import { useUi } from "@/stores/ui";

const next = { light: "dark", dark: "system", system: "light" } as const;
const icons = { light: Sun, dark: Moon, system: Monitor };

export function ThemeToggle() {
  const { theme, setTheme } = useUi();
  const Icon = icons[theme];
  return (
    <button
      type="button"
      onClick={() => setTheme(next[theme])}
      className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-800 dark:hover:bg-slate-800 dark:hover:text-slate-100"
      aria-label={`Theme: ${theme}. Switch to ${next[theme]}`}
      title={`Theme: ${theme}`}
    >
      <Icon className="size-5" aria-hidden />
    </button>
  );
}
