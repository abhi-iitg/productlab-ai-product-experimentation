"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

export function ProjectNav({ projectId }: { projectId: number }) {
  const pathname = usePathname();
  const base = `/projects/${projectId}`;

  const tabs = [
    { href: base, label: "Overview", exact: true },
    { href: `${base}/evidence`, label: "Evidence" },
    { href: `${base}/personas`, label: "Personas" },
    { href: `${base}/experiments`, label: "Experiments" },
  ];

  return (
    <nav
      className="-mb-px flex gap-4 overflow-x-auto border-b border-border"
      aria-label="Project sections"
    >
      {tabs.map((tab) => {
        const active = tab.exact ? pathname === tab.href : pathname.startsWith(tab.href);
        return (
          <Link
            key={tab.href}
            href={tab.href}
            aria-current={active ? "page" : undefined}
            className={cn(
              "whitespace-nowrap border-b-2 px-1 py-2.5 text-sm font-medium transition-colors",
              active
                ? "border-primary text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground"
            )}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
