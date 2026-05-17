"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, ShieldCheck, FileText,
  Settings, HelpCircle, Cpu, ChevronRight,
} from "lucide-react";

const NAV = [
  { label: "Dashboard", href: "/", icon: LayoutDashboard },
  { label: "Reports", href: "/reports", icon: FileText },
];

const SYSTEM_NAV = [
  { label: "Settings", href: "/settings", icon: Settings },
  { label: "Help", href: "/help", icon: HelpCircle },
];

export default function SidebarNav() {
  const pathname = usePathname();

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  };

  const navLink = (item: { label: string; href: string; icon: React.ElementType }) => {
    const { label, href, icon: Icon } = item;
    const active = isActive(href);
    return (
      <Link
        key={label}
        href={href}
        className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all ${
          active
            ? "bg-white/15 text-white font-medium"
            : "text-slate-400 hover:text-white hover:bg-white/10"
        }`}
      >
        <Icon className="w-4 h-4 shrink-0" />
        {label}
        {active && <div className="ml-auto w-1.5 h-1.5 rounded-full bg-blue-400" />}
      </Link>
    );
  };

  return (
    <aside className="w-[220px] min-h-screen bg-[#0f172a] flex flex-col shrink-0 sticky top-0 z-30">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-white/10">
        <Link href="/" className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-blue-500 flex items-center justify-center shrink-0">
            <ShieldCheck className="w-4 h-4 text-white" />
          </div>
          <div>
            <p className="text-white font-bold text-sm leading-tight">ProcureShield</p>
            <p className="text-blue-400 text-[10px] leading-tight">AI Procurement</p>
          </div>
        </Link>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 flex flex-col gap-1">
        <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest px-2 mb-2">Platform</p>
        {NAV.map(navLink)}

        <div className="mt-4 border-t border-white/10 pt-4">
          <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest px-2 mb-2">System</p>
          {SYSTEM_NAV.map(navLink)}
        </div>
      </nav>

      {/* Footer */}
      <div className="px-4 py-4 border-t border-white/10">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-full bg-blue-500/20 border border-blue-500/30 flex items-center justify-center">
            <Cpu className="w-3.5 h-3.5 text-blue-400" />
          </div>
          <div>
            <p className="text-[11px] text-slate-300 font-medium">AI for Bharat</p>
            <p className="text-[10px] text-slate-500">Gov Procurement</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
