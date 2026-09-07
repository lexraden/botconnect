"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useActionState, type ReactNode } from "react";
import { useFormStatus } from "react-dom";
import type { ActionState } from "@/app/dashboard/actions";

export function Card({ title, children, className = "", action }: { title?: ReactNode; children: ReactNode; className?: string; action?: ReactNode }) {
  return (
    <section className={`rounded-2xl border border-slate-200 bg-white p-5 shadow-sm ${className}`}>
      {(title || action) && (
        <div className="mb-4 flex items-center justify-between gap-3">
          {title && <h2 className="text-base font-semibold text-slate-900">{title}</h2>}
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-slate-900">{value}</p>
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </div>
  );
}

export function Badge({ children, tone = "slate" }: { children: ReactNode; tone?: "slate" | "green" | "red" | "amber" | "blue" }) {
  const tones = {
    slate: "bg-slate-100 text-slate-700",
    green: "bg-emerald-100 text-emerald-700",
    red: "bg-rose-100 text-rose-700",
    amber: "bg-amber-100 text-amber-800",
    blue: "bg-sky-100 text-sky-700",
  };
  return <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${tones[tone]}`}>{children}</span>;
}

export const inputCls =
  "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100";
export const labelCls = "mb-1 block text-xs font-medium text-slate-600";

export function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: string }) {
  return (
    <label className="block">
      <span className={labelCls}>{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-slate-500">{hint}</span>}
    </label>
  );
}

export function SubmitButton({ children, variant = "primary", className = "" }: { children: ReactNode; variant?: "primary" | "danger" | "ghost"; className?: string }) {
  const { pending } = useFormStatus();
  const variants = {
    primary: "bg-sky-600 text-white hover:bg-sky-700 disabled:bg-sky-300",
    danger: "bg-rose-600 text-white hover:bg-rose-700 disabled:bg-rose-300",
    ghost: "border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 disabled:text-slate-400",
  };
  return (
    <button type="submit" disabled={pending} className={`inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-medium transition ${variants[variant]} ${className}`}>
      {pending ? "…" : children}
    </button>
  );
}

export function FormMessage({ state }: { state: ActionState }) {
  if (!state) return null;
  if (state.error) return <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">{state.error}</p>;
  if (state.message) return <p className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{state.message}</p>;
  return null;
}

/** Generic form wrapper around useActionState for server actions returning ActionState. */
export function ActionForm({
  action,
  children,
  className = "",
}: {
  action: (prev: ActionState, fd: FormData) => Promise<ActionState>;
  children: ReactNode;
  className?: string;
}) {
  const [state, formAction] = useActionState(action, undefined);
  return (
    <form action={formAction} className={`space-y-3 ${className}`}>
      {children}
      <FormMessage state={state} />
    </form>
  );
}

export function BotTabs({ botId }: { botId: number }) {
  const pathname = usePathname();
  const base = `/dashboard/bots/${botId}`;
  const tabs = [
    { href: base, label: "Обзор" },
    { href: `${base}/buttons`, label: "Меню" },
    { href: `${base}/mailings`, label: "Рассылки" },
    { href: `${base}/users`, label: "Пользователи" },
    { href: `${base}/channels`, label: "Каналы" },
    { href: `${base}/subscription`, label: "Подписка" },
  ];
  return (
    <nav className="flex flex-wrap gap-1 rounded-xl bg-slate-100 p-1">
      {tabs.map((t) => {
        const active = pathname === t.href;
        return (
          <Link key={t.href} href={t.href} className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${active ? "bg-white text-slate-900 shadow-sm" : "text-slate-600 hover:text-slate-900"}`}>
            {t.label}
          </Link>
        );
      })}
    </nav>
  );
}

export function ConfirmButton({ children, message, variant = "danger" }: { children: ReactNode; message: string; variant?: "danger" | "ghost" }) {
  const { pending } = useFormStatus();
  return (
    <button
      type="submit"
      disabled={pending}
      onClick={(e) => {
        if (!confirm(message)) e.preventDefault();
      }}
      className={`rounded-lg px-3 py-1.5 text-xs font-medium ${variant === "danger" ? "text-rose-600 hover:bg-rose-50" : "text-slate-600 hover:bg-slate-100"}`}
    >
      {children}
    </button>
  );
}
