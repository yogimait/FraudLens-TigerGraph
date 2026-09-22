"use client";

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LayoutDashboard, Target, Network, Database, LineChart, FileText, CheckSquare, Settings, ChevronLeft, ChevronRight } from 'lucide-react';
import { useEffect, useState } from 'react';
import axios from 'axios';
import { cn } from '@/lib/utils';

const navItems = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Investigations', href: '/cases', icon: Target },
  { name: 'Case Memory', href: '/memory', icon: Database },
  { name: 'Graph Explorer', href: '/graph', icon: Network },
  { name: 'Analytics', href: '/analytics', icon: LineChart },
  { name: 'Reports', href: '/reports', icon: FileText },
  { name: 'Approvals', href: '/approvals', icon: CheckSquare, badgeKey: 'awaiting_approval', alert: true },
];

export function Sidebar() {
  const pathname = usePathname();
  const [stats, setStats] = useState<any>({});
  const [isCollapsed, setIsCollapsed] = useState(false);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await axios.get(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001'}/cases/stats`);
        setStats(res.data);
      } catch (e) {
        console.error("Failed to fetch sidebar stats", e);
      }
    };
    
    fetchStats();
    const interval = setInterval(fetchStats, 10000); // refresh every 10s
    return () => clearInterval(interval);
  }, []);

  return (
    <div className={`flex flex-col h-screen bg-sidebar text-sidebar-foreground border-r border-sidebar-border shrink-0 sticky top-0 transition-all duration-300 z-50 ${isCollapsed ? 'w-20' : 'w-64'}`}>
      <div className={`p-6 flex items-center border-b border-sidebar-border/50 relative ${isCollapsed ? 'justify-center' : 'space-x-3'}`}>
        <div className="w-8 h-8 rounded bg-gradient-to-br from-primary to-emerald-600 flex items-center justify-center text-primary-foreground font-serif font-bold text-lg shadow-[0_0_15px_rgba(16,185,129,0.3)] shrink-0">F</div>
        {!isCollapsed && (
          <div className="overflow-hidden">
            <h1 className="text-white font-serif font-bold text-2xl tracking-tight leading-none whitespace-nowrap">FraudLens</h1>
            <p className="text-[10px] text-muted-foreground uppercase tracking-widest mt-1 whitespace-nowrap">Ops Intelligence v2.5</p>
          </div>
        )}
        <button 
          onClick={() => setIsCollapsed(!isCollapsed)}
          className={`absolute ${isCollapsed ? '-right-3' : 'right-4'} top-8 bg-sidebar-accent text-sidebar-foreground p-1 rounded-full border border-sidebar-border hover:bg-primary/20 hover:text-primary transition-colors`}
        >
          {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>
      
      <div className="flex-1 py-6 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const isActive = pathname === item.href || (item.href !== '/' && pathname?.startsWith(item.href));
          const badgeValue = item.badgeKey ? stats[item.badgeKey] : null;
          
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "flex items-center px-6 py-3 transition-colors group relative",
                isActive 
                  ? "bg-sidebar-accent text-sidebar-primary-foreground border-r-2 border-primary" 
                  : "text-sidebar-muted-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
              )}
              title={isCollapsed ? item.name : undefined}
            >
              <item.icon className={cn(
                "h-5 w-5 shrink-0 transition-colors",
                isActive ? "text-primary" : "text-sidebar-muted-foreground group-hover:text-sidebar-foreground",
                isCollapsed ? "mx-auto" : "mr-4"
              )} />
              {!isCollapsed && <span className="font-medium whitespace-nowrap">{item.name}</span>}
              
              {!isCollapsed && badgeValue > 0 && (
                <span className={cn(
                  "ml-auto text-xs font-bold px-2 py-0.5 rounded-full",
                  item.alert 
                    ? "bg-destructive/20 text-destructive-foreground border border-destructive/30"
                    : "bg-primary/20 text-primary border border-primary/30"
                )}>
                  {badgeValue}
                </span>
              )}
              {isCollapsed && badgeValue > 0 && (
                <span className="absolute top-2 right-2 w-2 h-2 rounded-full bg-destructive" />
              )}
            </Link>
          );
        })}
      </div>

      <div className="p-4 border-t border-sidebar-border/50 bg-sidebar/80 space-y-4">
        <Link 
          href="/settings" 
          className={cn(
            "flex items-center px-4 py-2 text-sm font-medium rounded-md transition-colors",
            "text-sidebar-muted-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-foreground",
            isCollapsed && "justify-center"
          )}
          title={isCollapsed ? "Settings" : undefined}
        >
          <Settings className={cn("h-5 w-5 shrink-0", isCollapsed ? "mx-auto" : "mr-3")} />
          {!isCollapsed && <span>Settings</span>}
        </Link>

        <div className={cn("flex items-center px-4 py-2", isCollapsed ? "justify-center" : "space-x-3")}>
          <div className="w-9 h-9 rounded-full bg-sidebar-accent flex items-center justify-center text-sidebar-foreground font-medium shrink-0 border border-sidebar-border relative">
            ER
            <span className="absolute bottom-0 right-0 w-2.5 h-2.5 bg-primary border-2 border-sidebar rounded-full shadow-[0_0_8px_rgba(16,185,129,0.5)]"></span>
          </div>
          {!isCollapsed && (
            <div className="overflow-hidden">
              <p className="text-sm font-bold text-foreground truncate">Elena Rostova</p>
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground truncate">Lead Investigator</p>
            </div>
          )}
        </div>
        {!isCollapsed && (
          <div className="pt-4 border-t border-sidebar-border/50">
            <p className="text-xs italic text-muted-foreground/70 font-serif leading-relaxed">
              "Smarter investigations<br/>for a safer financial world."
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
