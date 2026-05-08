import { useState, useEffect, useCallback } from 'react';
import API from '@/api';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Users, Briefcase, Star, Phone, TrendingUp, UserCheck, XCircle } from 'lucide-react';
import { toast } from 'sonner';
import DateFilter from '@/components/DateFilter';

const SUPER = ['CEO', 'HR'];
const MGR_ROLES = ['Marketing Manager', 'Operations Manager', 'Sales Manager', 'Accounts Manager'];

export default function PerformancePage() {
  const { user } = useAuth();
  const isSuper = SUPER.includes(user?.role);
  const isManager = MGR_ROLES.includes(user?.role);

  const [tab, setTab] = useState('executives');
  const [dateRange, setDateRange] = useState({ preset: '30d', days: 30 });
  const [execs, setExecs] = useState([]);
  const [mgrs, setMgrs] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (dateRange.date_from) params.set('date_from', dateRange.date_from);
      if (dateRange.date_to) params.set('date_to', dateRange.date_to);
      if (!dateRange.date_from && !dateRange.date_to) params.set('days', '90');
      const qs = params.toString();
      const [e, m, j] = await Promise.all([
        API.get(`/analytics/executives?${qs}`).catch(() => ({ data: { executives: [] } })),
        API.get(`/analytics/managers?${qs}`).catch(() => ({ data: { managers: [] } })),
        API.get(`/analytics/jobs-performance?${qs}`).catch(() => ({ data: { users: [] } })),
      ]);
      setExecs(e.data.executives || []);
      setMgrs(m.data.managers || []);
      setJobs(j.data.users || []);
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Failed to load performance');
    } finally { setLoading(false); }
  }, [dateRange]);

  useEffect(() => { load(); }, [load]);

  if (loading) return <div className="flex items-center justify-center h-64 text-slate-500">Loading...</div>;

  return (
    <div className="space-y-4" data-testid="performance-page">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl md:text-2xl font-heading font-semibold text-slate-900">Performance</h1>
          <p className="text-sm text-slate-500">Executive, manager and job performance metrics</p>
        </div>
        <DateFilter value={dateRange} onChange={setDateRange} testId="perf-date-filter" />
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="grid w-full md:w-auto grid-cols-3 md:inline-grid">
          <TabsTrigger value="executives" data-testid="perf-tab-exec">Executives</TabsTrigger>
          <TabsTrigger value="managers" data-testid="perf-tab-mgr">Manager Interviews</TabsTrigger>
          <TabsTrigger value="jobs" data-testid="perf-tab-jobs">Jobs Performance</TabsTrigger>
        </TabsList>

        <TabsContent value="executives" className="mt-3 space-y-2">
          {execs.length === 0 ? <p className="text-sm text-slate-500 text-center py-8">No executive data</p> :
            execs.map((e) => (
              <Card key={e.user_id} className="border-slate-200 shadow-none" data-testid={`exec-row-${e.user_id}`}>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <div>
                      <p className="font-medium text-slate-900 text-sm">{e.name}</p>
                      <p className="text-xs text-slate-500">{e.role}</p>
                    </div>
                    <div className="flex flex-wrap gap-4 text-xs">
                      <Stat icon={<Users className="w-3 h-3" />} label="Leads" value={e.total_leads} />
                      <Stat icon={<Phone className="w-3 h-3" />} label="Called" value={e.called} />
                      <Stat icon={<UserCheck className="w-3 h-3" />} label="Selected" value={e.selected} color="text-teal-600" />
                      <Stat icon={<TrendingUp className="w-3 h-3" />} label="Joined" value={e.joined} color="text-emerald-700" />
                      <Stat icon={<XCircle className="w-3 h-3" />} label="Rejected" value={e.rejected} color="text-rose-600" />
                      <Stat icon={<Star className="w-3 h-3" />} label="Conv%" value={`${e.conversion_pct}%`} color="text-amber-600" />
                    </div>
                  </div>
                  {(isSuper || isManager) && (
                    <div className="flex gap-4 mt-2 pt-2 border-t border-slate-100 text-xs text-slate-500">
                      <span>Meta: <strong>{e.by_source?.meta_ads || 0}</strong></span>
                      <span>Job Portal: <strong>{e.by_source?.job_portal || 0}</strong></span>
                      <span>Manual: <strong>{e.by_source?.manual || 0}</strong></span>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
        </TabsContent>

        <TabsContent value="managers" className="mt-3 space-y-2">
          {mgrs.length === 0 ? <p className="text-sm text-slate-500 text-center py-8">No manager interview data</p> :
            mgrs.map((m) => (
              <Card key={m.user_id} className="border-slate-200 shadow-none" data-testid={`mgr-row-${m.user_id}`}>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <div>
                      <p className="font-medium text-slate-900 text-sm">{m.name}</p>
                      <p className="text-xs text-slate-500">{m.role}</p>
                    </div>
                    <div className="flex flex-wrap gap-4 text-xs">
                      <Stat label="Interviews" value={m.interviews_completed} />
                      <Stat label="Approved" value={m.approved} color="text-emerald-700" />
                      <Stat label="Rejected" value={m.rejected} color="text-rose-600" />
                      <Stat label="Hold" value={m.hold} color="text-amber-600" />
                      <Stat label="Joined" value={m.joined} color="text-teal-600" />
                      <Stat label="Avg ⭐" value={`${m.avg_rating}/5`} color="text-violet-600" />
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
        </TabsContent>

        <TabsContent value="jobs" className="mt-3 space-y-2">
          {jobs.length === 0 ? <p className="text-sm text-slate-500 text-center py-8">No job performance data</p> :
            jobs.map((j) => (
              <Card key={j.user_id} className="border-slate-200 shadow-none" data-testid={`jobperf-row-${j.user_id}`}>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <div>
                      <p className="font-medium text-slate-900 text-sm">{j.name}</p>
                      <p className="text-xs text-slate-500">{j.role}</p>
                    </div>
                    <div className="flex flex-wrap gap-4 text-xs">
                      <Stat icon={<Briefcase className="w-3 h-3" />} label="Jobs" value={j.jobs_created} />
                      <Stat label="Open" value={j.open_jobs} color="text-emerald-700" />
                      <Stat label="Closed" value={j.closed_jobs} color="text-slate-600" />
                      <Stat label="Leads" value={j.total_leads} />
                      <Stat label="Joined" value={j.joined} color="text-teal-600" />
                      <Stat label="Pending" value={j.pending} color="text-amber-600" />
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
        </TabsContent>
      </Tabs>
    </div>
  );
}

function Stat({ icon, label, value, color = 'text-slate-900' }) {
  return (
    <div className="flex items-center gap-1">
      {icon && <span className="text-slate-400">{icon}</span>}
      <span className="text-slate-500">{label}:</span>
      <span className={`font-semibold ${color}`}>{value}</span>
    </div>
  );
}

function Badge2({ children }) { return <Badge variant="outline" className="text-xs">{children}</Badge>; }
