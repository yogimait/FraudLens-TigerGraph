"use client";

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LayoutDashboard, Target, Network, Database, LineChart, FileText, CheckSquare, Settings } from 'lucide-react';
import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

const navItems = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Investigations', href: '/cases', icon: Target, badge: '14' },
  { name: 'Graph Explorer', href: '/graph', icon: Network },
  { name: 'Case Memory', href: '/memory', icon: Database },
  { name: 'Analytics', href: '/analytics', icon: LineChart },
  { name: 'Reports', href: '/reports', icon: FileText },
  { name: 'Approvals', href: '/approvals', icon: CheckSquare, badge: '3', alert: true },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <div className="flex flex-col w-64 h-screen bg-[#090D16] text-slate-300 border-r border-slate-800 shrink-0 sticky top-0">
      <div className="p-6 flex items-center space-x-3 border-b border-slate-800">
        <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white font-bold text-lg">F</div>
        <div>
          <h1 className="text-white font-bold text-xl tracking-tight">FraudLens</h1>
          <p className="text-xs text-slate-500">Ops Intelligence v2.4</p>
        </div>
      </div>
      
      <div className="flex-1 py-6 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const isActive = pathname === item.href || (item.href !== '/' && pathname?.startsWith(item.href));
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "flex items-center justify-between px-6 py-3 text-sm font-medium transition-colors hover:text-white",
                isActive ? "bg-blue-900/20 text-blue-400 border-l-2 border-blue-500" : "border-l-2 border-transparent"
              )}
            >
              <div className="flex items-center space-x-3">
                <item.icon className={cn("w-5 h-5", isActive ? "text-blue-400" : "text-slate-500")} />
                <span>{item.name}</span>
              </div>
              {item.badge && (
                <span className={cn(
                  "px-2 py-0.5 rounded-full text-xs font-bold",
                  item.alert ? "bg-red-500/20 text-red-500" : "bg-slate-800 text-slate-400"
                )}>
                  {item.badge}
                </span>
              )}
            </Link>
          );
        })}
      </div>

      <div className="p-6 border-t border-slate-800">
        <Link href="/settings" className="flex items-center space-x-3 text-sm font-medium text-slate-400 hover:text-white mb-6">
          <Settings className="w-5 h-5" />
          <span>Settings</span>
        </Link>
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-full bg-slate-800 flex items-center justify-center text-white font-medium border border-slate-700 relative">
            ER
            <span className="absolute bottom-0 right-0 w-3 h-3 bg-green-500 border-2 border-[#090D16] rounded-full"></span>
          </div>
          <div className="overflow-hidden">
            <p className="text-sm font-medium text-white truncate">Elena Rostova</p>
            <p className="text-xs text-slate-500 truncate">Lead Investigator</p>
          </div>
        </div>
      </div>
    </div>
  );
}
