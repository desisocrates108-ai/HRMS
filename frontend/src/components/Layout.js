import { useState, useEffect } from 'react';
import { Link, useLocation, Outlet } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import API from '@/api';
import { Sheet, SheetContent, SheetTrigger, SheetTitle } from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  LayoutDashboard, Building2, Briefcase, Users, CheckSquare,
  UserCheck, Star, UserCog, LogOut, Menu, ChevronRight, ScrollText,
  MessageSquare, Bell, Image, BarChart3, MessageCircleHeart, Database,
  Wrench, Building
} from 'lucide-react';

const CEO_HR = ["CEO", "HR"];

function getNavItems(role) {
  const isCeoHr = CEO_HR.includes(role);
  const isManager = ["Marketing Manager","Operations Manager","Sales Manager","Accounts Manager"].includes(role);
  const isSrJrHR = ["Sr HR","Jr HR"].includes(role);
  const isFDE = role === "Franchise Executive";
  const isDesigner = role === "Graphic Designer";

  const items = [];
  items.push({ path: '/', label: 'Dashboard', icon: LayoutDashboard });
  items.push({ path: '/chat', label: 'Chat', icon: MessageSquare });

  // Branches: visible to ALL roles
  items.push({ path: '/branches', label: 'Branches', icon: Building2 });
  if (isCeoHr || isManager) items.push({ path: '/jobs', label: 'Jobs', icon: Briefcase });

  // Split leads menu (only to those who can see leads)
  if (isCeoHr || isSrJrHR || isManager) items.push({ path: '/leads/head-office', label: 'Head Office Leads', icon: Building });
  if (isCeoHr || isSrJrHR || isFDE || isManager) items.push({ path: '/leads/franchise', label: 'Franchise Leads', icon: Wrench });

  if (isCeoHr || isSrJrHR || isDesigner) items.push({ path: '/posts', label: 'Post Panel', icon: Image });

  items.push({ path: '/tasks', label: 'Task Manager', icon: CheckSquare });

  // Database (Employee history): CEO/HR/Managers
  if (isCeoHr || isManager) items.push({ path: '/database', label: 'Database', icon: Database });

  if (isCeoHr || isManager) items.push({ path: '/performance', label: 'Performance', icon: Star });
  if (isCeoHr || isManager) items.push({ path: '/analytics', label: 'Analytics', icon: BarChart3 });
  if (isCeoHr) items.push({ path: '/feedback-submissions', label: 'Feedback', icon: MessageCircleHeart });
  if (isCeoHr) items.push({ path: '/users', label: 'Users', icon: UserCog });
  if (isCeoHr) items.push({ path: '/audit', label: 'Audit Logs', icon: ScrollText });

  return items;
}

function NavContent({ onClose }) {
  const location = useLocation();
  const { user, logout } = useAuth();
  const navItems = getNavItems(user?.role);
  return (
    <div className="flex flex-col h-full min-h-0" data-testid="sidebar-nav">
      <div className="p-4 pb-2 flex-shrink-0"><h1 className="text-xl font-semibold tracking-tight font-heading text-slate-900">Servall</h1><p className="text-xs text-slate-500 mt-1">Hiring Operating System</p></div>
      <Separator className="flex-shrink-0" />
      <div className="p-3 mx-3 mt-3 rounded-lg bg-slate-50 border border-slate-200 flex-shrink-0"><p className="text-sm font-medium text-slate-900 truncate">{user?.name}</p><Badge variant="outline" className="mt-1 text-xs">{user?.role}</Badge></div>
      <nav className="flex-1 min-h-0 p-3 space-y-1 mt-2 overflow-y-auto">
        {navItems.map(item => {
          const isActive = location.pathname === item.path || (item.path !== '/' && location.pathname.startsWith(item.path));
          return (<Link key={item.path} to={item.path} onClick={onClose} data-testid={`sidebar-nav-${item.label.toLowerCase().replace(/\s+/g, '-')}`}
            className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200 ${isActive ? 'bg-blue-700 text-white font-medium' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'}`}>
            <item.icon className="w-4 h-4 flex-shrink-0" strokeWidth={2} /><span>{item.label}</span>{isActive && <ChevronRight className="w-3 h-3 ml-auto" />}
          </Link>);
        })}
      </nav>
      <div className="p-3 border-t border-slate-200 flex-shrink-0"><Button variant="ghost" className="w-full justify-start text-slate-500 hover:text-red-600" onClick={logout} data-testid="logout-button"><LogOut className="w-4 h-4 mr-2" />Sign Out</Button></div>
    </div>
  );
}

function NotificationBell() {
  const [count, setCount] = useState(0);
  const [notifs, setNotifs] = useState([]);
  const [open, setOpen] = useState(false);
  useEffect(() => { fetchCount(); const i = setInterval(fetchCount, 10000); return () => clearInterval(i); }, []);
  const fetchCount = async () => { try { const { data } = await API.get('/notifications/unread-count'); setCount(data.count); } catch {} };
  const fetchNotifs = async () => { try { const { data } = await API.get('/notifications'); setNotifs(data); } catch {} };
  const markAllRead = async () => { try { await API.put('/notifications/read-all'); setCount(0); setNotifs(prev => prev.map(n => ({...n, read: true}))); } catch {} };
  return (
    <Popover open={open} onOpenChange={v => { setOpen(v); if (v) fetchNotifs(); }}>
      <PopoverTrigger asChild><Button variant="ghost" size="icon" className="relative" data-testid="notification-bell"><Bell className="w-5 h-5 text-slate-600" />{count > 0 && <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-red-600 text-white text-[10px] font-bold rounded-full flex items-center justify-center" data-testid="notification-badge">{count > 9 ? '9+' : count}</span>}</Button></PopoverTrigger>
      <PopoverContent className="w-80 p-0" align="end">
        <div className="p-3 border-b flex items-center justify-between"><p className="text-sm font-semibold">Notifications</p>{count > 0 && <Button size="sm" variant="ghost" className="text-xs h-6" onClick={markAllRead}>Mark all read</Button>}</div>
        <ScrollArea className="max-h-64">{notifs.length === 0 ? <p className="text-sm text-slate-500 p-4 text-center">No notifications</p> : <div className="divide-y">{notifs.slice(0,15).map(n => <div key={n.id} className={`p-3 ${!n.read?'bg-blue-50':''}`}><p className="text-sm font-medium text-slate-900">{n.title}</p><p className="text-xs text-slate-500 mt-0.5">{n.message}</p><p className="text-xs text-slate-400 mt-0.5">{new Date(n.created_at).toLocaleString()}</p></div>)}</div>}</ScrollArea>
      </PopoverContent>
    </Popover>
  );
}

export default function Layout() {
  const [sheetOpen, setSheetOpen] = useState(false);
  return (
    <div className="flex h-screen bg-slate-50">
      <aside className="hidden md:flex w-60 flex-col bg-white border-r border-slate-200 flex-shrink-0"><NavContent onClose={() => {}} /></aside>
      <div className="flex-1 flex flex-col min-w-0">
        <header className="flex items-center justify-between px-4 py-3 bg-white border-b border-slate-200 md:justify-end">
          <div className="flex items-center gap-3 md:hidden">
            <Sheet open={sheetOpen} onOpenChange={setSheetOpen}><SheetTrigger asChild><Button variant="ghost" size="icon" data-testid="mobile-menu-button"><Menu className="w-5 h-5" /></Button></SheetTrigger><SheetContent side="left" className="w-64 p-0"><SheetTitle className="sr-only">Menu</SheetTitle><NavContent onClose={() => setSheetOpen(false)} /></SheetContent></Sheet>
            <h1 className="text-lg font-semibold font-heading text-slate-900">Servall</h1>
          </div>
          <NotificationBell />
        </header>
        <main className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8"><Outlet /></main>
      </div>
    </div>
  );
}
