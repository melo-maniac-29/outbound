import type { ReactNode } from "react";
import Link from "next/link";
import WorkspaceNav from "./workspace-nav";

export default function WorkspaceLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <div className="workspace-frame">
      <header className="workspace-topbar">
        <Link href="/" className="brand-lockup">
          <span>Outbound Nexus</span>
          <small>Review-first operator console</small>
        </Link>
        <WorkspaceNav />
      </header>
      <div className="workspace-body">{children}</div>
    </div>
  );
}
