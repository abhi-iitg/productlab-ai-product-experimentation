"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { FlaskConical, Menu } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetClose,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";

const NAV_LINKS = [{ href: "/projects", label: "Projects" }];

export function Header() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/95 backdrop-blur supports-backdrop-filter:bg-background/80">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
        <Link href="/projects" className="flex items-center gap-2 font-semibold">
          <FlaskConical className="size-5 text-primary" aria-hidden="true" />
          <span className="text-sm sm:text-base">ProductLab-AI Product Experimentation</span>
        </Link>

        <nav className="hidden items-center gap-1 sm:flex" aria-label="Primary">
          {NAV_LINKS.map((link) => {
            const active = pathname.startsWith(link.href);
            return (
              <Button
                key={link.href}
                nativeButton={false}
                render={<Link href={link.href} />}
                variant={active ? "secondary" : "ghost"}
                size="sm"
              >
                {link.label}
              </Button>
            );
          })}
        </nav>

        <Sheet>
          <SheetTrigger
            render={
              <Button variant="ghost" size="icon" className="sm:hidden" aria-label="Open menu" />
            }
          >
            <Menu className="size-5" />
          </SheetTrigger>
          <SheetContent side="right">
            <SheetHeader>
              <SheetTitle>Menu</SheetTitle>
            </SheetHeader>
            <nav className="flex flex-col gap-1 px-4" aria-label="Mobile">
              {NAV_LINKS.map((link) => (
                <SheetClose
                  key={link.href}
                  nativeButton={false}
                  render={
                    <Button
                      nativeButton={false}
                      render={<Link href={link.href} />}
                      variant="ghost"
                      className="justify-start"
                    />
                  }
                >
                  {link.label}
                </SheetClose>
              ))}
            </nav>
          </SheetContent>
        </Sheet>
      </div>
    </header>
  );
}
