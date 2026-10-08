"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import {
  Compass,
  LayoutGrid,
  FlaskConical,
  Database,
  BookOpen,
  ExternalLink,
  Menu,
  X,
} from "lucide-react";
const nav = [
  { href: "/", label: "Overview", icon: LayoutGrid },
  { href: "/experiments", label: "Experiments", icon: FlaskConical },
  { href: "/data", label: "Data sources", icon: Database },
  { href: "/methodology", label: "Methodology", icon: BookOpen },
];
export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const current =
    nav.find((n) =>
      n.href === "/" ? pathname === "/" : pathname.startsWith(n.href),
    )?.label || "Workspace";
  return (
    <div className="app-shell">
      <a className="skip-link" href="#content">
        Skip to content
      </a>
      <div className="mobile-header">
        <Link href="/" className="brand">
          <Compass size={28} />
          Q-Compass
        </Link>
        <button
          aria-label={open ? "Close navigation" : "Open navigation"}
          aria-expanded={open}
          onClick={() => setOpen(!open)}
          className="icon-button"
        >
          {open ? <X /> : <Menu />}
        </button>
      </div>
      <aside className={`sidebar ${open ? "is-open" : ""}`}>
        <Link href="/" className="brand">
          <Compass size={39} strokeWidth={1.3} />
          <span>Q-Compass</span>
        </Link>
        <nav aria-label="Main navigation">
          {nav.map(({ href, label, icon: Icon }) => (
            <Link
              href={href}
              key={href}
              onClick={() => setOpen(false)}
              aria-current={current === label ? "page" : undefined}
              className={current === label ? "active" : ""}
            >
              <Icon size={21} strokeWidth={1.6} />
              {label}
            </Link>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <a href="http://127.0.0.1:8501" target="_blank" rel="noreferrer">
            <ExternalLink size={18} />
            Open Streamlit
          </a>
          <p>Simulation only</p>
        </div>
      </aside>
      <main id="content" className="main">
        <div className="topbar">
          <div>
            <span>Workspace</span>
            <span className="slash">/</span>
            {current}
          </div>
          <span className="engine-label">Local engine</span>
        </div>
        {children}
      </main>
    </div>
  );
}
