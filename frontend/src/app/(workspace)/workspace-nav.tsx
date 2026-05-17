"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Settings, Activity, Users } from "lucide-react";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/runs", label: "Runs", icon: Activity },
  { href: "/leads", label: "Leads", icon: Users },
  { href: "/settings", label: "Settings", icon: Settings },
];

export default function WorkspaceNav() {
  const pathname = usePathname();

  return (
    <nav className="workspace-nav" aria-label="Workspace navigation">
      {navItems.map((item) => {
        const Icon = item.icon;
        const isActive =
          item.href === "/dashboard"
            ? pathname === "/dashboard"
            : pathname.startsWith(item.href);

        return (
          <Link key={item.href} href={item.href} className={`workspace-nav-link${isActive ? " is-active" : ""}`}>
            <Icon size={16} />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
