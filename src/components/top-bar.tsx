"use client";

import { Bell, ChevronDown, Command, Radio, RotateCcw } from "lucide-react";
import { useEffect, useState } from "react";

import type { WorkflowRun } from "@/lib/workflow/schemas";

interface TopBarProps {
  run: WorkflowRun | null;
  onReset: () => void;
}

export function TopBar({ run, onReset }: TopBarProps) {
  const [clock, setClock] = useState("--:--:--");

  useEffect(() => {
    const update = () =>
      setClock(
        new Intl.DateTimeFormat("en-GB", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          hour12: false,
          timeZone: "UTC",
        }).format(new Date()),
      );
    update();
    const interval = window.setInterval(update, 1_000);
    return () => window.clearInterval(interval);
  }, []);

  return (
    <header className="sticky top-0 z-40 border-b border-white/[0.07] bg-[#07100e]/90 backdrop-blur-xl">
      <div className="mx-auto flex h-16 w-full max-w-[1680px] items-center gap-5 px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-3">
          <div className="relative grid size-9 place-items-center overflow-hidden rounded-xl border border-emerald-300/25 bg-emerald-300/10 text-emerald-200 shadow-[0_0_30px_rgba(110,231,183,0.08)]">
            <Command className="size-[18px]" strokeWidth={2} />
            <div className="absolute inset-x-1 bottom-0 h-px bg-gradient-to-r from-transparent via-emerald-300/70 to-transparent" />
          </div>
          <div>
            <div className="flex items-baseline gap-1.5">
              <span className="text-sm font-semibold tracking-tight text-white">Twemp</span>
              <span className="rounded bg-white/[0.07] px-1 py-0.5 font-mono text-[8px] text-white/45">
                LAB
              </span>
            </div>
            <p className="text-[9px] uppercase tracking-[0.19em] text-white/35">
              Agent command system
            </p>
          </div>
        </div>

        <div className="hidden h-7 w-px bg-white/[0.08] sm:block" />

        <button className="hidden items-center gap-2 text-xs text-white/50 transition hover:text-white/80 md:flex">
          <span>Global operations</span>
          <ChevronDown className="size-3.5" />
        </button>

        <div className="ml-auto flex items-center gap-2 sm:gap-3">
          <div className="hidden items-center gap-2 rounded-full border border-white/[0.08] bg-white/[0.03] px-3 py-1.5 lg:flex">
            <Radio className="size-3 text-emerald-300" />
            <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/45">
              {run?.mode === "openai" ? "OpenAI live" : "Deterministic demo"}
            </span>
          </div>
          <div className="hidden font-mono text-[10px] tabular-nums text-white/35 sm:block">
            {clock} UTC
          </div>
          {run && (
            <button
              type="button"
              onClick={onReset}
              className="grid size-8 place-items-center rounded-lg border border-white/[0.08] text-white/45 transition hover:border-white/15 hover:bg-white/[0.06] hover:text-white"
              aria-label="Start a new incident"
              title="New incident"
            >
              <RotateCcw className="size-3.5" />
            </button>
          )}
          <button
            type="button"
            className="relative grid size-8 place-items-center rounded-lg border border-white/[0.08] text-white/45 transition hover:border-white/15 hover:bg-white/[0.06] hover:text-white"
            aria-label="Notifications"
          >
            <Bell className="size-3.5" />
            <span className="absolute right-1.5 top-1.5 size-1.5 rounded-full bg-rose-400 ring-2 ring-[#07100e]" />
          </button>
          <div className="grid size-8 place-items-center rounded-full border border-emerald-300/20 bg-gradient-to-br from-emerald-300/20 to-cyan-300/10 text-[10px] font-semibold text-emerald-100">
            OL
          </div>
        </div>
      </div>
    </header>
  );
}
