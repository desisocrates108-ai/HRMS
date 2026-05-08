import { useState, useEffect, useCallback } from 'react';
import API from '@/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, LineChart, Line, CartesianGrid } from 'recharts';
import { TrendingUp, AlertTriangle, Award, Users, Target, Clock, Star } from 'lucide-react';
import { toast } from 'sonner';

const STAGE_LABELS = {
  new_lead: 'New',
  qualified: 'Qualified',
  hr_interview: 'HR',
  manager_interview: 'Manager',
  move_ahead: 'Move Ahead',
  joined: 'Joined',
};

const COLORS = ['#1D4ED8', '#059669', '#D97706', '#7C3AED', '#0D9488', '#15803D'];

export default function AnalyticsPage() {
  const [pipelineType, setPipelineType] = useState('all');
  const [days, setDays] = useState(90);
  const [summary, setSummary] = useState(null);
  const [intel, setIntel] = useState(null);
  const [feedbackSummary, setFeedbackSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const pt = pipelineType === 'all' ? '' : `&pipeline_type=${pipelineType}`;
      const [s, i, f] = await Promise.all([
        API.get(`/analytics/summary?days=${days}${pt}`),
        API.get(`/analytics/intelligence?days=${days}`),
        API.get('/feedback/submissions/summary').catch(() => ({ data: null })),
      ]);
      setSummary(s.data);
      setIntel(i.data);
      setFeedbackSummary(f.data);
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Failed to load analytics');
    } finally {
      setLoading(false);
    }
  }, [pipelineType, days]);

  useEffect(() => { load(); }, [load]);

  if (loading || !summary) return <div className="flex items-center justify-center h-64 text-slate-500">Loading analytics...</div>;

  const funnelData = summary.funnel.map((f) => ({
    stage: STAGE_LABELS[f.stage] || f.stage,
    count: f.count,
    conversion: summary.conversions_pct[f.stage] || 0,
  }));

  return (
    <div className="space-y-5" data-testid="analytics-page">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl md:text-2xl font-heading font-semibold text-slate-900">Analytics & Intelligence</h1>
          <p className="text-sm text-slate-500">Hiring funnel, conversion rates, and insights</p>
        </div>
        <div className="flex items-center gap-2">
          <Tabs value={pipelineType} onValueChange={setPipelineType}>
            <TabsList>
              <TabsTrigger value="all" data-testid="filter-all">All</TabsTrigger>
              <TabsTrigger value="head_office" data-testid="filter-ho">Head Office</TabsTrigger>
              <TabsTrigger value="technician" data-testid="filter-tech">Technician</TabsTrigger>
            </TabsList>
          </Tabs>
          <Tabs value={String(days)} onValueChange={(v) => setDays(Number(v))}>
            <TabsList>
              <TabsTrigger value="30">30d</TabsTrigger>
              <TabsTrigger value="90">90d</TabsTrigger>
              <TabsTrigger value="365">1y</TabsTrigger>
            </TabsList>
          </Tabs>
        </div>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <KPI icon={<Users />} label="Total Leads" value={summary.total_leads} color="bg-blue-50 text-blue-700" />
        <KPI icon={<Target />} label="Hires" value={summary.hires} color="bg-emerald-50 text-emerald-700" />
        <KPI icon={<Clock />} label="Avg Time-to-Hire" value={`${summary.avg_time_to_hire_days}d`} color="bg-violet-50 text-violet-700" />
        <KPI icon={<Star />} label="Avg HR Score" value={`${summary.avg_hr_score}/5`} color="bg-amber-50 text-amber-700" />
        <KPI icon={<Star />} label="Avg Mgr Score" value={`${summary.avg_manager_score}/5`} color="bg-teal-50 text-teal-700" />
      </div>

      {/* Intelligence insights */}
      {intel?.insights?.length > 0 && (
        <Card className="border-slate-200 shadow-none">
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-medium flex items-center gap-2"><TrendingUp className="w-4 h-4 text-emerald-600" /> System Insights</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {intel.insights.map((ins, idx) => (
              <div key={idx} className={`p-3 rounded-md border text-sm ${
                ins.type === 'best_interviewer' ? 'bg-emerald-50 border-emerald-200 text-emerald-800' :
                ins.type === 'weak_stage' ? 'bg-rose-50 border-rose-200 text-rose-800' :
                'bg-amber-50 border-amber-200 text-amber-800'
              }`} data-testid={`insight-${ins.type}`}>
                {ins.message}
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Funnel chart */}
      <Card className="border-slate-200 shadow-none">
        <CardHeader className="pb-2"><CardTitle className="text-base font-medium">Hiring Funnel</CardTitle></CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={funnelData} margin={{ top: 10, right: 10, bottom: 0, left: -10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="stage" tick={{ fontSize: 12, fill: '#64748b' }} />
              <YAxis tick={{ fontSize: 12, fill: '#64748b' }} />
              <Tooltip />
              <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                {funnelData.map((entry, idx) => <Cell key={idx} fill={COLORS[idx % COLORS.length]} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <div className="grid grid-cols-3 md:grid-cols-6 gap-2 mt-3 text-xs">
            {funnelData.map((f, idx) => (
              <div key={idx} className="text-center">
                <p className="text-slate-500">{f.stage}</p>
                <p className="font-semibold text-slate-900">{f.count}</p>
                <p className="text-[10px] text-slate-400">{f.conversion}%</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Grid: Best interviewer + Weak stages */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="border-slate-200 shadow-none">
          <CardHeader className="pb-2"><CardTitle className="text-base font-medium flex items-center gap-2"><Award className="w-4 h-4 text-amber-500" /> Interviewer Leaderboard</CardTitle></CardHeader>
          <CardContent>
            {intel?.all_interviewers?.length > 0 ? (
              <div className="space-y-2">
                {intel.all_interviewers.slice(0, 5).map((iv, idx) => (
                  <div key={iv.user_id} className={`flex items-center justify-between p-2 rounded border ${idx === 0 ? 'border-amber-200 bg-amber-50' : 'border-slate-100'}`}>
                    <div>
                      <p className="text-sm font-medium text-slate-900">#{idx + 1} {iv.name}</p>
                      <p className="text-xs text-slate-500">{iv.interviews_conducted} interviews · avg {iv.avg_rating_given}/5</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-semibold text-emerald-700">{iv.hit_rate_pct}%</p>
                      <p className="text-[10px] text-slate-400">hit rate</p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-500">Need ≥3 interviews to rank (collect more data).</p>
            )}
          </CardContent>
        </Card>

        <Card className="border-slate-200 shadow-none">
          <CardHeader className="pb-2"><CardTitle className="text-base font-medium flex items-center gap-2"><AlertTriangle className="w-4 h-4 text-rose-500" /> Weak Stage Detector</CardTitle></CardHeader>
          <CardContent>
            {intel?.weak_stages?.length > 0 ? (
              <div className="space-y-2">
                {intel.weak_stages.slice(0, 4).map((ws, idx) => (
                  <div key={idx} className="p-2 rounded border border-slate-100">
                    <div className="flex items-center justify-between">
                      <p className="text-sm text-slate-900">{STAGE_LABELS[ws.from_stage]} → {STAGE_LABELS[ws.to_stage]}</p>
                      <Badge className={`${ws.drop_pct >= 50 ? 'bg-rose-100 text-rose-700' : 'bg-slate-100 text-slate-700'} border-0`}>
                        -{ws.drop_pct}%
                      </Badge>
                    </div>
                    <p className="text-xs text-slate-500 mt-0.5">{ws.from_count} → {ws.to_count} candidates</p>
                  </div>
                ))}
              </div>
            ) : <p className="text-sm text-slate-500">No data yet</p>}
          </CardContent>
        </Card>
      </div>

      {/* Hold / Dead Reasons */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <ReasonCard title="Hold Reasons" data={summary.hold_reasons} emptyText="No active holds" testId="hold-reasons" />
        <ReasonCard title="Rejection Reasons" data={summary.dead_reasons} emptyText="No rejections in window" testId="dead-reasons" />
      </div>

      {/* Feedback summary */}
      {feedbackSummary && (
        <Card className="border-slate-200 shadow-none">
          <CardHeader className="pb-2"><CardTitle className="text-base font-medium">Feedback Collected</CardTitle></CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-3">
              <KPI icon={<Users />} label="Rejection" value={feedbackSummary.rejection_count} color="bg-rose-50 text-rose-700" />
              <KPI icon={<Users />} label="Exit" value={feedbackSummary.exit_count} color="bg-violet-50 text-violet-700" />
              <KPI icon={<Clock />} label="Pending" value={feedbackSummary.pending_invitations} color="bg-amber-50 text-amber-700" />
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function KPI({ icon, label, value, color }) {
  return (
    <div className={`flex items-center gap-2 px-3 py-3 rounded-md ${color}`}>
      <div className="opacity-70">{icon}</div>
      <div className="min-w-0">
        <p className="text-xs truncate opacity-80">{label}</p>
        <p className="text-lg font-semibold">{value}</p>
      </div>
    </div>
  );
}

function ReasonCard({ title, data, emptyText, testId }) {
  return (
    <Card className="border-slate-200 shadow-none" data-testid={testId}>
      <CardHeader className="pb-2"><CardTitle className="text-base font-medium">{title}</CardTitle></CardHeader>
      <CardContent>
        {!data || data.length === 0 ? (
          <p className="text-sm text-slate-500">{emptyText}</p>
        ) : (
          <div className="space-y-2">
            {data.map((r) => (
              <div key={r.reason} className="flex items-center justify-between text-sm">
                <span className="text-slate-700 capitalize">{r.reason.replace(/_/g, ' ')}</span>
                <Badge variant="outline">{r.count}</Badge>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
