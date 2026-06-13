import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import API from '@/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import {
  Briefcase, Users, UserCheck, TrendingUp, Phone, CheckSquare,
  Building2, ChevronRight, Clock, AlertCircle, ChevronDown, ChevronUp,
  Image, Megaphone, Video, ExternalLink, Filter
} from 'lucide-react';

const SC = { new_lead:'#1D4ED8', qualified:'#059669', hr_interview:'#D97706', manager_interview:'#7C3AED', selected:'#0D9488', joined:'#15803D', hold:'#F97316', rejected:'#E11D48' };
const SL = { new_lead:'New', qualified:'Qualified', hr_interview:'HR', manager_interview:'Manager', selected:'Selected', joined:'Joined', hold:'Hold', rejected:'Rejected' };
const STAGES = ['new_lead','qualified','hr_interview','manager_interview','selected','joined','hold','rejected'];

export default function DashboardPage() {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [dateFilter, setDateFilter] = useState('all');

  const fetchStats = useCallback(() => {
    const params = {};
    if (dateFilter === 'today') {
      const t = new Date(); t.setHours(0,0,0,0);
      params.date_from = t.toISOString();
    } else if (dateFilter === 'yesterday') {
      const t = new Date(); t.setHours(0,0,0,0); t.setDate(t.getDate() - 1);
      const e = new Date(t); e.setDate(e.getDate() + 1);
      params.date_from = t.toISOString(); params.date_to = e.toISOString();
    } else if (dateFilter === '7') {
      params.days = 7;
    } else if (dateFilter === '30') {
      params.days = 30;
    } else if (dateFilter === 'month') {
      const t = new Date(); const start = new Date(t.getFullYear(), t.getMonth(), 1);
      params.date_from = start.toISOString();
    }
    setLoading(true);
    API.get('/dashboard/stats', { params }).then(r => setStats(r.data)).catch(() => {}).finally(() => setLoading(false));
  }, [dateFilter]);

  useEffect(() => { fetchStats(); }, [fetchStats]);

  if (loading) return <div className="flex items-center justify-center h-64 text-slate-500">Loading...</div>;
  if (!stats) return <div className="text-center py-12 text-slate-500">Failed to load dashboard</div>;

  const t = stats.type;
  const headerBar = (
    <div className="flex items-center justify-between flex-wrap gap-2 -mb-2">
      <div></div>
      <DateFilterBar value={dateFilter} onChange={setDateFilter} />
    </div>
  );

  if (t === 'ceo') return <><div className="mb-2"><DateFilterBar value={dateFilter} onChange={setDateFilter} /></div><CEODash s={stats} u={user} /></>;
  if (t === 'hr') return <><div className="mb-2"><DateFilterBar value={dateFilter} onChange={setDateFilter} /></div><HRDash s={stats} u={user} /></>;
  if (t === 'manager') return <><div className="mb-2"><DateFilterBar value={dateFilter} onChange={setDateFilter} /></div><ManagerDash s={stats} u={user} /></>;
  if (t === 'sr_jr_hr') return <SrJrHRDash s={stats} u={user} />;
  if (t === 'fde') return <FDEDash s={stats} u={user} />;
  if (t === 'designer') return <DesignerDash s={stats} u={user} />;
  if (t === 'mktg_coord') return <MktgCoordDash s={stats} u={user} />;
  return <GenericExecDash s={stats} u={user} />;
}

function KPI({ icon: Icon, label, value, color, to }) {
  const nav = useNavigate();
  const clickable = !!to;
  return (
    <Card
      onClick={clickable ? () => nav(to) : undefined}
      className={`border-slate-200 shadow-none ${clickable ? 'cursor-pointer hover:-translate-y-0.5 hover:shadow-md hover:border-blue-300 transition-all duration-200 active:scale-[0.98]' : ''}`}
      data-testid={clickable ? `kpi-${label.toLowerCase().replace(/\s+/g, '-')}` : undefined}
    >
      <CardContent className="p-3">
        <div className="flex items-center gap-3">
          <div className={color}><Icon className="w-5 h-5" /></div>
          <div><p className="text-xl font-bold text-slate-900">{value ?? 0}</p><p className="text-xs text-slate-500">{label}</p></div>
        </div>
      </CardContent>
    </Card>
  );
}

function PipelineRow({ pipeline, isTechnician }) {
  const nav = useNavigate();
  const goStage = (stage) => {
    const params = new URLSearchParams({ stage });
    if (isTechnician !== undefined) params.set('is_technician', String(isTechnician));
    nav(`/leads?${params.toString()}`);
  };
  return (
    <div className="grid grid-cols-3 md:grid-cols-6 gap-2">
      {STAGES.map(s => (
        <button
          key={s}
          onClick={() => goStage(s)}
          className="p-2 rounded-lg border border-slate-200 bg-white text-center hover:border-blue-300 hover:shadow-sm transition-all duration-200 active:scale-[0.97]"
          data-testid={`pipeline-stage-${s}`}
        >
          <div className="text-[10px] font-semibold text-slate-500 uppercase">{SL[s]?.split(' ')[0]}</div>
          <div className="text-lg font-bold" style={{ color: SC[s] }}>{pipeline?.[s] || 0}</div>
        </button>
      ))}
    </div>
  );
}

function LeadSplitCards({ split }) {
  const nav = useNavigate();
  if (!split) return null;
  return (
    <Card className="border-slate-200 shadow-none" data-testid="lead-split-cards">
      <CardHeader className="pb-2"><CardTitle className="text-base font-medium">Lead Split (Head Office vs Franchise)</CardTitle></CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
          <button onClick={() => nav('/leads/head-office')} className="flex items-center gap-2 px-3 py-3 rounded-md bg-blue-50 text-blue-700 hover:-translate-y-0.5 hover:shadow-sm transition-all text-left" data-testid="lead-split-ho-total">
            <Building2 className="w-4 h-4 opacity-70" />
            <div><p className="text-xs opacity-80">HO · Total</p><p className="text-lg font-semibold">{split.ho_total||0}</p></div>
          </button>
          <button onClick={() => nav('/leads/head-office')} className="flex items-center gap-2 px-3 py-3 rounded-md bg-blue-50/60 text-blue-700 hover:-translate-y-0.5 hover:shadow-sm transition-all text-left" data-testid="lead-split-ho-today">
            <Clock className="w-4 h-4 opacity-70" />
            <div><p className="text-xs opacity-80">HO · Today</p><p className="text-lg font-semibold">{split.ho_today||0}</p></div>
          </button>
          <button onClick={() => nav('/leads/franchise')} className="flex items-center gap-2 px-3 py-3 rounded-md bg-emerald-50 text-emerald-700 hover:-translate-y-0.5 hover:shadow-sm transition-all text-left" data-testid="lead-split-fr-total">
            <Users className="w-4 h-4 opacity-70" />
            <div><p className="text-xs opacity-80">Franchise · Total</p><p className="text-lg font-semibold">{split.franchise_total||0}</p></div>
          </button>
          <button onClick={() => nav('/leads/franchise')} className="flex items-center gap-2 px-3 py-3 rounded-md bg-emerald-50/60 text-emerald-700 hover:-translate-y-0.5 hover:shadow-sm transition-all text-left" data-testid="lead-split-fr-today">
            <Clock className="w-4 h-4 opacity-70" />
            <div><p className="text-xs opacity-80">Franchise · Today</p><p className="text-lg font-semibold">{split.franchise_today||0}</p></div>
          </button>
          <button onClick={() => nav('/leads/head-office?stage=three_months')} className="flex items-center gap-2 px-3 py-3 rounded-md bg-indigo-50 text-indigo-700 hover:-translate-y-0.5 hover:shadow-sm transition-all text-left" data-testid="lead-split-3mo-due">
            <AlertCircle className="w-4 h-4 opacity-70" />
            <div><p className="text-xs opacity-80">3-Month Due</p><p className="text-lg font-semibold">{split.three_months_due||0}</p></div>
          </button>
        </div>
      </CardContent>
    </Card>
  );
}

function OpenPositionsCard({ data }) {
  const nav = useNavigate();
  const [showAll, setShowAll] = useState(false);
  const [detail, setDetail] = useState(null); // { role, segmentKey, jobs, segmentTitle }
  if (!data) return null;
  const hoRows = data.head_office || [];
  const frRows = data.franchise || [];
  const summary = data.summary || { head_office: { openings: 0, applicants: 0, roles: 0 }, franchise: { openings: 0, applicants: 0, roles: 0 }, total: { openings: 0, applicants: 0, roles: 0 } };
  const isEmpty = hoRows.length === 0 && frRows.length === 0;

  const STAGE_LABELS = {
    new_lead: 'New',
    qualified: 'Qualified',
    hr_interview: 'HR',
    manager_interview: 'Manager',
    hold: 'Hold',
  };
  const STAGE_COLORS = {
    new_lead: 'bg-slate-100 text-slate-700',
    qualified: 'bg-sky-100 text-sky-700',
    hr_interview: 'bg-amber-100 text-amber-700',
    manager_interview: 'bg-violet-100 text-violet-700',
    hold: 'bg-rose-100 text-rose-700',
  };

  const ROW_LIMIT = 5;

  const Section = ({ title, icon: Icon, rows, segmentKey, segSummary }) => {
    const targetPath = segmentKey === 'franchise' ? '/leads/franchise' : '/leads/head-office';
    const goTo = (role, stage) => {
      const params = new URLSearchParams({ job_role: role });
      if (stage) params.set('stage', stage);
      nav(`${targetPath}?${params.toString()}`);
    };
    const visible = showAll ? rows : rows.slice(0, ROW_LIMIT);
    const hiddenCount = Math.max(0, rows.length - visible.length);
    return (
      <div className="flex flex-col gap-2 min-w-0" data-testid={`open-positions-${segmentKey}`}>
        <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-500">
          <Icon className="w-3.5 h-3.5" />
          <span>{title}</span>
          <Badge variant="outline" className="text-[10px] ml-auto">
            {segSummary.openings} openings · {segSummary.applicants} active
          </Badge>
        </div>
        {rows.length === 0 ? (
          <p className="text-xs text-slate-400 italic py-2">No open positions</p>
        ) : (
          <div className="space-y-2">
            {visible.map((r) => {
              const sb = r.stage_breakdown || {};
              const activeStages = Object.entries(sb).filter(([, n]) => n > 0);
              const slug = r.role.replace(/\s+/g, '-').toLowerCase();
              return (
                <div
                  key={`${segmentKey}-${r.role}`}
                  className="p-3 rounded-md border border-slate-200 bg-white hover:border-blue-300 hover:bg-blue-50/30 transition-all"
                  data-testid={`open-position-row-${segmentKey}-${slug}`}
                >
                  <div className="flex items-baseline justify-between gap-2">
                    <button
                      type="button"
                      onClick={() => goTo(r.role)}
                      className="text-left group min-w-0 flex-1"
                      data-testid={`open-position-role-${segmentKey}-${slug}`}
                    >
                      <p className="text-sm font-medium text-slate-900 truncate group-hover:text-blue-700">{r.role}</p>
                    </button>
                    <div className="flex items-center gap-2 shrink-0">
                      <p className="text-xs text-slate-500">
                        <span className="text-blue-700 font-semibold">{r.openings}</span> {r.openings === 1 ? 'opening' : 'openings'}
                        <span className="mx-1 text-slate-300">·</span>
                        <span className="text-emerald-700 font-semibold">{r.applicants}</span> active
                      </p>
                      <button
                        type="button"
                        onClick={() => setDetail({ role: r.role, segmentKey, segmentTitle: title, jobs: r.jobs || [] })}
                        className="text-[11px] text-blue-700 hover:underline whitespace-nowrap"
                        data-testid={`open-position-detail-${segmentKey}-${slug}`}
                      >
                        Details
                      </button>
                    </div>
                  </div>
                  {activeStages.length > 0 ? (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {activeStages.map(([stg, n]) => (
                        <button
                          type="button"
                          key={stg}
                          onClick={(e) => { e.stopPropagation(); goTo(r.role, stg); }}
                          className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${STAGE_COLORS[stg] || 'bg-slate-100 text-slate-700'} hover:ring-1 hover:ring-blue-400 transition`}
                          data-testid={`stage-pill-${segmentKey}-${slug}-${stg}`}
                          title={`See ${r.role} candidates in ${STAGE_LABELS[stg] || stg}`}
                        >
                          {STAGE_LABELS[stg] || stg}: {n}
                        </button>
                      ))}
                    </div>
                  ) : (
                    <p className="text-[11px] text-slate-400 italic mt-1.5">No active applicants yet</p>
                  )}
                </div>
              );
            })}
            {hiddenCount > 0 && (
              <button
                type="button"
                onClick={() => setShowAll(true)}
                className="w-full text-xs text-blue-700 hover:underline py-1.5"
                data-testid={`open-positions-show-all-${segmentKey}`}
              >
                Show {hiddenCount} more {hiddenCount === 1 ? 'role' : 'roles'}
              </button>
            )}
          </div>
        )}
      </div>
    );
  };

  const totalRoles = summary.total.roles;

  return (
    <>
      <Card className="border-slate-200 shadow-none" data-testid="open-positions-card">
        <CardHeader className="pb-2">
          <div className="flex items-start justify-between gap-3 flex-wrap">
            <CardTitle className="text-base font-medium flex items-center gap-2">
              <Briefcase className="w-4 h-4 text-blue-700" />
              Open Positions
            </CardTitle>
            <div className="flex items-center gap-2 flex-wrap" data-testid="open-positions-summary">
              <Badge className="bg-blue-50 text-blue-700 border-0 text-xs">
                <span className="font-bold mr-1">{summary.total.openings}</span> openings
              </Badge>
              <Badge className="bg-emerald-50 text-emerald-700 border-0 text-xs">
                <span className="font-bold mr-1">{summary.total.applicants}</span> active candidates
              </Badge>
              <Badge variant="outline" className="text-xs text-slate-600">
                {totalRoles} {totalRoles === 1 ? 'role' : 'roles'}
              </Badge>
              {(hoRows.length + frRows.length) > ROW_LIMIT * 2 && (
                <button
                  type="button"
                  onClick={() => setShowAll((v) => !v)}
                  className="text-xs text-blue-700 hover:underline"
                  data-testid="open-positions-toggle-all"
                >
                  {showAll ? 'Collapse' : 'View all'}
                </button>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {isEmpty ? (
            <div className="flex flex-col items-center justify-center py-8 text-center" data-testid="open-positions-empty-state">
              <Briefcase className="w-8 h-8 text-slate-300 mb-2" />
              <p className="text-sm font-medium text-slate-600">No open job positions yet</p>
              <p className="text-xs text-slate-400 mt-1">Create a job opening to start tracking applicants per role.</p>
              <button
                type="button"
                onClick={() => nav('/jobs')}
                className="mt-3 text-xs font-medium text-blue-700 hover:underline"
                data-testid="open-positions-go-to-jobs"
              >
                Go to Jobs →
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Section title="Head Office" icon={Building2} rows={hoRows} segmentKey="head_office" segSummary={summary.head_office} />
              <Section title="Franchise" icon={Users} rows={frRows} segmentKey="franchise" segSummary={summary.franchise} />
            </div>
          )}
        </CardContent>
      </Card>

      <OpenPositionDetailDialog
        open={!!detail}
        onClose={() => setDetail(null)}
        detail={detail}
        nav={nav}
        STAGE_LABELS={STAGE_LABELS}
        STAGE_COLORS={STAGE_COLORS}
      />
    </>
  );
}

function OpenPositionDetailDialog({ open, onClose, detail, nav, STAGE_LABELS, STAGE_COLORS }) {
  if (!detail) return null;
  const targetPath = detail.segmentKey === 'franchise' ? '/leads/franchise' : '/leads/head-office';
  const goTo = (role, stage) => {
    const params = new URLSearchParams({ job_role: role });
    if (stage) params.set('stage', stage);
    nav(`${targetPath}?${params.toString()}`);
    onClose();
  };
  const jobs = detail.jobs || [];
  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) onClose(); }}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto" data-testid="open-positions-detail-dialog">
        <DialogHeader>
          <DialogTitle className="font-heading">
            {detail.role} <span className="text-slate-400 font-normal text-sm">· {detail.segmentTitle}</span>
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-sm text-slate-600">
            <Badge className="bg-blue-50 text-blue-700 border-0">
              {jobs.length} {jobs.length === 1 ? 'opening' : 'openings'}
            </Badge>
            <Badge className="bg-emerald-50 text-emerald-700 border-0">
              {jobs.reduce((sum, j) => sum + (j.applicants || 0), 0)} active candidates
            </Badge>
            <button
              type="button"
              onClick={() => goTo(detail.role)}
              className="ml-auto text-xs text-blue-700 hover:underline"
              data-testid="detail-see-all-candidates"
            >
              See all candidates →
            </button>
          </div>
          <div className="space-y-2">
            {jobs.map((j, idx) => {
              const sb = j.stage_breakdown || {};
              const activeStages = Object.entries(sb).filter(([, n]) => n > 0);
              const locLabel = [j.branch_name, j.location].filter(Boolean).join(' · ') || '—';
              return (
                <div
                  key={j.id}
                  className="p-3 border border-slate-200 rounded-md bg-white"
                  data-testid={`detail-job-row-${idx}`}
                >
                  <div className="flex items-baseline justify-between gap-2 flex-wrap">
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-slate-900">Opening #{idx + 1}</p>
                      <p className="text-xs text-slate-500 mt-0.5">
                        📍 {locLabel}
                        {j.department && <span className="mx-1.5 text-slate-300">·</span>}
                        {j.department && <span>{j.department}</span>}
                      </p>
                    </div>
                    <div className="text-xs text-slate-600 shrink-0">
                      <span className="text-emerald-700 font-semibold">{j.applicants || 0}</span> active
                    </div>
                  </div>
                  {activeStages.length > 0 ? (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {activeStages.map(([stg, n]) => (
                        <button
                          type="button"
                          key={stg}
                          onClick={() => goTo(detail.role, stg)}
                          className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${STAGE_COLORS[stg] || 'bg-slate-100 text-slate-700'} hover:ring-1 hover:ring-blue-400`}
                        >
                          {STAGE_LABELS[stg] || stg}: {n}
                        </button>
                      ))}
                    </div>
                  ) : (
                    <p className="text-[11px] text-slate-400 italic mt-1.5">No active applicants on this opening yet</p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function DateFilterBar({ value, onChange }) {
  const opts = [
    { value: 'all', label: 'All' },
    { value: 'today', label: 'Today' },
    { value: 'yesterday', label: 'Yesterday' },
    { value: '7', label: '7 Days' },
    { value: '30', label: '30 Days' },
    { value: 'month', label: 'This Month' },
  ];
  return (
    <div className="flex gap-1 flex-wrap" data-testid="dashboard-date-filter">
      {opts.map(o => (
        <button
          key={o.value}
          onClick={() => onChange(o.value)}
          className={`px-3 py-1.5 rounded-md text-xs font-medium border transition-all ${value === o.value ? 'bg-blue-700 text-white border-blue-700' : 'bg-white text-slate-700 border-slate-200 hover:border-slate-300'}`}
          data-testid={`date-filter-${o.value}`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

function LeadTable({ leads, showBranch }) {
  const nav = useNavigate();
  if (!leads?.length) return <p className="text-sm text-slate-500 py-4 text-center">No leads</p>;
  return (<div className="space-y-1.5">{leads.slice(0,20).map(l => (
    <div key={l.id} className="p-2.5 rounded-lg border border-slate-200 bg-white hover:border-blue-300 cursor-pointer transition-all" onClick={() => nav(`/leads/${l.id}`)} data-testid={`lead-row-${l.id}`}>
      <div className="flex items-center justify-between"><p className="font-medium text-sm text-slate-900">{l.name}</p><Badge style={{backgroundColor:`${SC[l.current_stage]}15`,color:SC[l.current_stage]}} className="border-0 text-xs">{l.stage_label}</Badge></div>
      <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-slate-500 mt-1">
        {l.experience && <span>Exp: {l.experience}y</span>}{l.job_role && <span>Role: {l.job_role}</span>}{l.salary_expectation && <span>Sal: {l.salary_expectation}</span>}
        <span>By: {l.assigned_to_name}</span>{l.source && <span>Src: {l.source.replace('_',' ')}</span>}{l.interview_date && <span>Int: {l.interview_date}</span>}
        {showBranch && l.branch_name && <span className="flex items-center gap-0.5"><Building2 className="w-3 h-3" />{l.branch_name}</span>}
      </div>
    </div>))}</div>);
}

function HiringSection({ section, showBranch, isTechnician }) {
  if (!section) return null;
  return (<>
    <PipelineRow pipeline={section.pipeline} isTechnician={isTechnician} />
    <Tabs defaultValue="meta_ads"><TabsList className="grid grid-cols-3 w-full md:w-96 h-auto"><TabsTrigger value="meta_ads" className="text-xs py-1.5">Meta Ads ({section.leads_by_source?.meta_ads?.length||0})</TabsTrigger><TabsTrigger value="job_portal" className="text-xs py-1.5">Job Portals ({section.leads_by_source?.job_portal?.length||0})</TabsTrigger><TabsTrigger value="manual" className="text-xs py-1.5">Manual ({section.leads_by_source?.manual?.length||0})</TabsTrigger></TabsList>
    {['meta_ads','job_portal','manual'].map(src => (<TabsContent key={src} value={src} className="mt-2"><LeadTable leads={section.leads_by_source?.[src]} showBranch={showBranch} /></TabsContent>))}</Tabs>
  </>);
}

function LeadSourceCards({ data }) {
  const nav = useNavigate();
  if (!data) return null;
  const sources = [
    { key: 'meta_ads', label: 'Meta Leads', color: 'bg-blue-50 text-blue-700', icon: Users },
    { key: 'job_portal', label: 'Job Portal', color: 'bg-emerald-50 text-emerald-700', icon: Briefcase },
    { key: 'manual', label: 'Manual', color: 'bg-amber-50 text-amber-700', icon: Users },
  ];
  const counts = { meta_ads: 0, job_portal: 0, manual: 0 };
  ['technician_hiring', 'ho_hiring'].forEach((k) => {
    const sec = data[k] || {};
    const by = sec.leads_by_source || {};
    counts.meta_ads += (by.meta_ads || []).length;
    counts.job_portal += (by.job_portal || []).length;
    counts.manual += (by.manual || []).length;
  });
  const total = counts.meta_ads + counts.job_portal + counts.manual;

  return (
    <Card className="border-slate-200 shadow-none" data-testid="source-cards">
      <CardHeader className="pb-2"><CardTitle className="text-base font-medium">Leads by Source</CardTitle></CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          {sources.map((s) => (
            <button
              key={s.key}
              onClick={() => nav(`/leads?source=${s.key}`)}
              className={`flex items-center gap-2 px-3 py-3 rounded-md ${s.color} hover:-translate-y-0.5 hover:shadow-sm transition-all text-left`}
              data-testid={`source-card-${s.key}`}
            >
              <s.icon className="w-4 h-4 opacity-70" />
              <div>
                <p className="text-xs opacity-80">{s.label}</p>
                <p className="text-lg font-semibold">{counts[s.key]}</p>
              </div>
            </button>
          ))}
          <button
            onClick={() => nav('/leads')}
            className="flex items-center gap-2 px-3 py-3 rounded-md bg-violet-50 text-violet-700 hover:-translate-y-0.5 hover:shadow-sm transition-all text-left"
            data-testid="source-card-all"
          >
            <TrendingUp className="w-4 h-4 opacity-70" />
            <div>
              <p className="text-xs opacity-80">All Leads</p>
              <p className="text-lg font-semibold">{total}</p>
            </div>
          </button>
        </div>
      </CardContent>
    </Card>
  );
}

function FranchisesCard({ data }) {
  const nav = useNavigate();
  if (!data) return null;
  const all = [...(data.upcoming || []), ...(data.active || [])];
  if (!all.length) return null;
  return (
    <Card className="border-slate-200 shadow-none" data-testid="franchises-card">
      <CardHeader className="pb-2">
        <CardTitle className="text-base font-medium flex items-center gap-2">
          <Building2 className="w-4 h-4 text-blue-700" />
          <button onClick={() => nav('/branches')} className="hover:underline" data-testid="franchises-title-link">Franchises</button>
          <Badge variant="outline" className="ml-1 text-xs">{data.total_upcoming} upcoming</Badge>
          <Badge variant="outline" className="text-xs text-emerald-700 border-emerald-200">{data.total_active} active</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="upcoming">
          <TabsList className="grid grid-cols-2 w-full md:w-72 h-auto">
            <TabsTrigger value="upcoming" className="text-xs py-1.5" data-testid="franchise-upcoming-tab">Upcoming ({data.total_upcoming})</TabsTrigger>
            <TabsTrigger value="active" className="text-xs py-1.5" data-testid="franchise-active-tab">Active ({data.total_active})</TabsTrigger>
          </TabsList>
          {['upcoming', 'active'].map((kind) => (
            <TabsContent key={kind} value={kind} className="mt-2">
              {(data[kind] || []).length === 0 ? (
                <p className="text-sm text-slate-500 py-3 text-center">No {kind} franchises</p>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {data[kind].map((b) => (
                    <button
                      key={b.id}
                      onClick={() => nav('/branches')}
                      className="p-2.5 rounded-lg border border-slate-200 bg-white text-left hover:border-blue-300 hover:shadow-sm transition-all duration-200 active:scale-[0.99]"
                      data-testid={`dash-franchise-${b.id}`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-sm font-medium text-slate-900 truncate">{b.name}</p>
                        <Badge className={`${kind === 'upcoming' ? 'bg-amber-50 text-amber-700' : 'bg-emerald-50 text-emerald-700'} border-0 text-[10px] flex-shrink-0`}>{kind}</Badge>
                      </div>
                      <p className="text-xs text-slate-500 mt-0.5">{b.city}, {b.area}</p>
                      <div className="flex gap-3 mt-1.5 text-xs">
                        <span className="text-blue-700"><strong>{b.open_jobs}</strong> jobs</span>
                        <span className="text-emerald-700"><strong>{b.employees}</strong> staff</span>
                        {kind === 'upcoming' && b.tentative_opening_date && (
                          <span className="text-slate-500">Opens {b.tentative_opening_date}</span>
                        )}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </TabsContent>
          ))}
        </Tabs>
      </CardContent>
    </Card>
  );
}

function MeetingButtons() {
  const [url, setUrl] = useState('');
  const start = async () => { try { const {data} = await API.post('/meetings/create'); setUrl(data.meeting_url); window.open(data.meeting_url, '_blank'); } catch {} };
  const [meetings, setMeetings] = useState([]);
  useEffect(() => { API.get('/meetings/recent').then(r => setMeetings(r.data)).catch(() => {}); }, []);
  return (<Card className="border-slate-200 shadow-none"><CardHeader className="pb-2"><CardTitle className="text-base font-medium flex items-center gap-2"><Video className="w-4 h-4 text-blue-700" />Meetings</CardTitle></CardHeader><CardContent>
    <div className="flex gap-2 mb-3"><Button size="sm" className="bg-blue-700 hover:bg-blue-800" onClick={start} data-testid="start-meeting-btn"><Video className="w-3 h-3 mr-1" />Start Meeting</Button>
    {meetings.length > 0 && <Button size="sm" variant="outline" onClick={() => window.open(meetings[0].meeting_url, '_blank')} data-testid="join-meeting-btn"><ExternalLink className="w-3 h-3 mr-1" />Join Last Meeting</Button>}</div>
    {meetings.slice(0,3).map(m => (<div key={m.id} className="flex items-center justify-between text-xs py-1 border-b border-slate-50"><span className="text-slate-700">{m.created_by_name}</span><a href={m.meeting_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 underline">{new Date(m.created_at).toLocaleString()}</a></div>))}
  </CardContent></Card>);
}

// ===================== CEO =====================
function CEODash({ s }) {
  const [exp, setExp] = useState(null);
  const [cleanupOpen, setCleanupOpen] = useState(false);
  const [cleaning, setCleaning] = useState(false);
  const [preview, setPreview] = useState(null);
  const tm = s.top_metrics||{};
  const openCleanup = async () => {
    try { const { data } = await API.get('/admin/cleanup-preview'); setPreview(data.counts); setCleanupOpen(true); }
    catch { /* noop */ }
  };
  const runCleanup = async () => {
    setCleaning(true);
    try { await API.post('/admin/cleanup'); window.location.reload(); }
    catch { setCleaning(false); }
  };
  return (<div className="space-y-5" data-testid="ceo-dashboard">
    <h1 className="text-2xl font-heading font-semibold text-slate-900">CEO Dashboard</h1>
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3"><KPI icon={Users} label="Total Leads" value={tm.total_leads} color="text-blue-700" to="/leads" /><KPI icon={TrendingUp} label="Hirings" value={tm.total_hirings} color="text-emerald-600" to="/employees" /><KPI icon={UserCheck} label="Employees" value={tm.total_employees} color="text-violet-600" to="/employees" /><KPI icon={Phone} label="Calls Done" value={tm.calls_done} color="text-amber-600" to="/leads" /></div>
    <LeadSplitCards split={s.lead_split} />
    <OpenPositionsCard data={s.open_positions} />
    {s.overdue_jobs?.length > 0 && <Card className="border-red-200 bg-red-50/50 shadow-none cursor-pointer hover:bg-red-50 transition-colors" onClick={() => window.location.href = '/jobs'}><CardContent className="p-3"><div className="flex items-center gap-2 mb-2"><AlertCircle className="w-4 h-4 text-red-600" /><span className="text-sm font-semibold text-red-800">Overdue Jobs ({s.overdue_jobs.length})</span></div>{s.overdue_jobs.map(j => <p key={j.id} className="text-xs text-red-700">{j.role} - {j.location} (deadline: {j.deadline})</p>)}</CardContent></Card>}
    <LeadSourceCards data={s} />
    <Tabs defaultValue="technician"><TabsList className="grid grid-cols-2 w-full md:w-96"><TabsTrigger value="technician" data-testid="tab-technician">Franchise (FDE)</TabsTrigger><TabsTrigger value="ho" data-testid="tab-ho">Head Office (HR)</TabsTrigger></TabsList>
      <TabsContent value="technician" className="mt-3 space-y-3"><h3 className="text-sm font-semibold text-slate-700">Jobs ({s.technician_hiring?.jobs?.length||0})</h3>{s.technician_hiring?.jobs?.slice(0,4).map(j => <Badge key={j.id} variant="outline" className="mr-1 mb-1 cursor-pointer hover:border-blue-400 hover:bg-blue-50" onClick={() => window.location.href='/jobs'} data-testid={`job-badge-${j.id}`}>{j.role} - {j.location}</Badge>)}<HiringSection section={s.technician_hiring} showBranch isTechnician={true} /></TabsContent>
      <TabsContent value="ho" className="mt-3 space-y-3"><h3 className="text-sm font-semibold text-slate-700">Jobs ({s.ho_hiring?.jobs?.length||0})</h3>{s.ho_hiring?.jobs?.slice(0,4).map(j => <Badge key={j.id} variant="outline" className="mr-1 mb-1 cursor-pointer hover:border-blue-400 hover:bg-blue-50" onClick={() => window.location.href='/jobs'} data-testid={`job-badge-${j.id}`}>{j.role} - {j.location}</Badge>)}<HiringSection section={s.ho_hiring} isTechnician={false} /></TabsContent>
    </Tabs>
    <Card className="border-slate-200 shadow-none"><CardHeader className="pb-2"><CardTitle className="text-base font-medium flex items-center gap-2"><Phone className="w-4 h-4 text-blue-700" />Call Tracking</CardTitle></CardHeader><CardContent>{!s.call_tracking?.length ? <p className="text-sm text-slate-500">No calls</p> : <div className="space-y-2">{s.call_tracking.map(e => (
      <div key={e.id} className="border border-slate-200 rounded-lg overflow-hidden"><div className="flex items-center justify-between p-2 cursor-pointer hover:bg-slate-50" onClick={() => setExp(exp===e.id?null:e.id)} data-testid={`exec-calls-${e.id}`}><div><p className="text-sm font-medium text-slate-900">{e.name}</p><p className="text-xs text-slate-500">{e.role}</p></div><div className="flex items-center gap-2"><Badge variant="outline" className="text-xs">{e.total_calls} calls</Badge>{exp===e.id?<ChevronUp className="w-3 h-3" />:<ChevronDown className="w-3 h-3" />}</div></div>
      {exp===e.id && <div className="border-t bg-slate-50 p-2 space-y-1">{e.leads_called?.map((lc,i) => <div key={i} className="flex justify-between text-xs px-1"><span className="text-slate-700">{lc.lead_name}</span><span className="flex gap-2"><Badge variant="secondary" className="text-[10px]">{lc.source?.replace('_',' ')}</Badge><span className="text-slate-500">{lc.call_count}x</span></span></div>)}</div>}
    </div>))}</div>}</CardContent></Card>
    <FranchisesCard data={s.franchises} />
    <MeetingButtons />

    {/* Admin Tools — CEO only */}
    <Card className="border-rose-200 shadow-none bg-rose-50/30" data-testid="admin-tools-card">
      <CardHeader className="pb-2"><CardTitle className="text-base font-medium text-rose-700">Admin Tools</CardTitle></CardHeader>
      <CardContent className="space-y-2">
        <p className="text-xs text-rose-600">Use these tools carefully. Logins, audit logs, and role configurations are preserved.</p>
        <Button variant="outline" className="text-rose-700 border-rose-200 hover:bg-rose-100" onClick={openCleanup} data-testid="open-cleanup-button">
          Reset / Clear All Business Data
        </Button>
      </CardContent>
    </Card>

    <Dialog open={cleanupOpen} onOpenChange={setCleanupOpen}>
      <DialogContent className="max-w-md">
        <DialogHeader><DialogTitle>Clear Demo / Live Data</DialogTitle></DialogHeader>
        <div className="space-y-2 text-sm">
          <p className="text-rose-700 font-medium">This will permanently remove:</p>
          <div className="max-h-60 overflow-y-auto bg-slate-50 p-2 rounded text-xs space-y-0.5">
            {preview && Object.entries(preview).map(([k, v]) => (
              <div key={k} className="flex justify-between"><span className="text-slate-700">{k}</span><span className="font-mono text-slate-900">{v}</span></div>
            ))}
          </div>
          <p className="text-emerald-700 text-xs">Preserved: user logins, audit logs, role/permission setup, WhatsApp env.</p>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setCleanupOpen(false)}>Cancel</Button>
          <Button onClick={runCleanup} className="bg-rose-600 hover:bg-rose-700" disabled={cleaning} data-testid="confirm-cleanup-button">
            {cleaning ? 'Clearing...' : 'Yes, Clear All Data'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>);
}

// ===================== HR =====================
function HRDash({ s }) {
  const nav = useNavigate();
  const tm = s.top_metrics||{};
  return (<div className="space-y-5" data-testid="hr-dashboard">
    <h1 className="text-2xl font-heading font-semibold text-slate-900">HR Dashboard</h1>
    <div className="grid grid-cols-2 md:grid-cols-5 gap-3"><KPI icon={Users} label="Total Leads" value={tm.total_leads} color="text-blue-700" to="/leads" /><KPI icon={TrendingUp} label="Hirings" value={tm.total_hirings} color="text-emerald-600" to="/employees" /><KPI icon={UserCheck} label="Employees" value={tm.total_employees} color="text-violet-600" to="/employees" /><KPI icon={Phone} label="Calls Done" value={tm.calls_done} color="text-amber-600" to="/leads" /><KPI icon={Phone} label="Today Calls" value={tm.calls_today} color="text-blue-600" to="/leads" /></div>
    <LeadSplitCards split={s.lead_split} />
    <OpenPositionsCard data={s.open_positions} />
    <div className="flex gap-3 flex-wrap"><Button size="sm" variant="outline" onClick={() => nav('/posts')} data-testid="go-post-panel"><Image className="w-3 h-3 mr-1" />Post Panel ({s.pending_reviews||0} to review)</Button><Button size="sm" variant="outline" onClick={() => nav('/leads')}>All Leads</Button><Button size="sm" variant="outline" onClick={() => nav('/jobs')}>All Jobs ({s.all_jobs?.length||0})</Button></div>
    {s.overdue_jobs?.length > 0 && <Card className="border-red-200 bg-red-50/50 shadow-none cursor-pointer hover:bg-red-50 transition-colors" onClick={() => nav('/jobs')}><CardContent className="p-3"><AlertCircle className="w-4 h-4 text-red-600 inline mr-1" /><span className="text-sm font-semibold text-red-800">Overdue: </span>{s.overdue_jobs.map(j => <Badge key={j.id} variant="destructive" className="text-xs mr-1">{j.role}</Badge>)}</CardContent></Card>}
    <PipelineRow pipeline={s.overall_pipeline} />
    <LeadSourceCards data={s} />
    <Tabs defaultValue="technician"><TabsList className="grid grid-cols-2 w-full md:w-72"><TabsTrigger value="technician">Franchise Leads ({s.technician_hiring?.total_leads||0})</TabsTrigger><TabsTrigger value="ho">HO Leads ({s.ho_hiring?.total_leads||0})</TabsTrigger></TabsList>
      <TabsContent value="technician" className="mt-2"><HiringSection section={s.technician_hiring} showBranch isTechnician={true} /></TabsContent>
      <TabsContent value="ho" className="mt-2"><HiringSection section={s.ho_hiring} isTechnician={false} /></TabsContent>
    </Tabs>
    <FranchisesCard data={s.franchises} />
    <MeetingButtons />
  </div>);
}

// ===================== MANAGER =====================
function ManagerDash({ s }) {
  const nav = useNavigate();
  const tm = s.top_metrics||{};
  return (<div className="space-y-5" data-testid="manager-dashboard">
    <h1 className="text-2xl font-heading font-semibold text-slate-900">{s.department} Manager</h1>
    <div className="grid grid-cols-2 md:grid-cols-5 gap-3"><KPI icon={Briefcase} label="Jobs Created" value={tm.jobs_created} color="text-blue-700" to="/jobs" /><KPI icon={TrendingUp} label="Active Hirings" value={tm.active_hirings} color="text-emerald-600" to="/jobs" /><KPI icon={Users} label="Total Leads" value={tm.total_leads} color="text-violet-600" to="/leads" /><KPI icon={Users} label="New Leads" value={tm.new_leads} color="text-amber-600" to="/leads?stage=new_lead" /><KPI icon={UserCheck} label="Hires" value={tm.total_hires} color="text-indigo-600" to="/employees" /></div>
    <LeadSplitCards split={s.lead_split} />
    {s.alerts?.length > 0 && <Card className="border-amber-200 bg-amber-50/50 shadow-none"><CardContent className="p-3">{s.alerts.map((a,i) => <div key={i} className="flex items-center gap-2 text-sm py-0.5"><AlertCircle className={`w-3 h-3 ${a.type==='overdue'?'text-red-600':'text-amber-600'}`} /><span className={a.type==='overdue'?'text-red-700':'text-amber-700'}>{a.message}</span></div>)}</CardContent></Card>}
    <Card className="border-slate-200 shadow-none"><CardHeader className="pb-2"><div className="flex items-center justify-between"><CardTitle className="text-base font-medium">My Job Openings</CardTitle><Button size="sm" className="bg-blue-700 hover:bg-blue-800" onClick={() => nav('/jobs')}>Create Job</Button></div></CardHeader><CardContent>
      {!s.jobs?.length ? <p className="text-sm text-slate-500">No jobs created yet</p> : <div className="space-y-2">{s.jobs.map(j => (
        <div key={j.id} onClick={() => nav('/jobs')} className="flex items-center justify-between p-2 rounded border border-slate-200 cursor-pointer hover:border-blue-300 hover:bg-blue-50/30 transition-all" data-testid={`mgr-job-${j.id}`}><div><p className="text-sm font-medium text-slate-900">{j.role}</p><p className="text-xs text-slate-500">{j.location} | {j.department||j.type}</p></div><div className="flex items-center gap-2"><Badge variant={j.status==='open'?'default':'secondary'} className={j.status==='open'?'bg-emerald-100 text-emerald-700 border-0':''}>{j.status}</Badge><span className="text-xs text-slate-500">{j.leads_count} leads</span><span className="text-xs text-slate-400">{j.assigned_hr}</span></div></div>
      ))}</div>}</CardContent></Card>
    <PipelineRow pipeline={s.pipeline} />
    <Card className="border-slate-200 shadow-none"><CardHeader className="pb-2"><CardTitle className="text-base font-medium">Lead Insights</CardTitle></CardHeader><CardContent><div className="grid grid-cols-4 gap-3 text-center">{[['New',s.lead_insights?.new,'text-blue-700','new_lead'],['Qualified',s.lead_insights?.qualified,'text-emerald-600','qualified'],['Interviewed',s.lead_insights?.interviewed,'text-amber-600','hr_interview'],['Hired',s.lead_insights?.hired,'text-violet-600','joined']].map(([l,v,c,stage]) => <button key={l} onClick={() => nav(`/leads?stage=${stage}`)} className="rounded p-1 hover:bg-slate-50 transition-colors" data-testid={`insight-${l.toLowerCase()}`}><p className={`text-xl font-bold ${c}`}>{v||0}</p><p className="text-xs text-slate-500">{l}</p></button>)}</div></CardContent></Card>
    {s.ownership && Object.keys(s.ownership).length > 0 && <Card className="border-slate-200 shadow-none"><CardHeader className="pb-2"><CardTitle className="text-base font-medium">Lead Ownership</CardTitle></CardHeader><CardContent><div className="space-y-1">{Object.entries(s.ownership).map(([name,cnt]) => <div key={name} className="flex justify-between text-sm py-1 border-b border-slate-50"><span className="text-slate-700">{name}</span><Badge variant="outline" className="text-xs">{cnt} leads</Badge></div>)}</div></CardContent></Card>}
    <LeadTable leads={s.leads} />
    <FranchisesCard data={s.franchises} />
    <MeetingButtons />
  </div>);
}

// ===================== SR/JR HR =====================
function SrJrHRDash({ s, u }) {
  const nav = useNavigate();
  return (<div className="space-y-5" data-testid="srhr-dashboard">
    <h1 className="text-2xl font-heading font-semibold text-slate-900">{u?.role} Dashboard</h1>
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3"><KPI icon={Users} label="My Leads" value={s.my_leads_count} color="text-blue-700" to="/leads" /><KPI icon={Phone} label="Calls Today" value={s.calls_today} color="text-emerald-600" to="/leads" /><KPI icon={Phone} label="Total Calls" value={s.total_calls} color="text-amber-600" to="/leads" /><KPI icon={Briefcase} label="Open Jobs" value={s.all_jobs?.length} color="text-violet-600" to="/jobs" /></div>
    <div className="flex gap-2"><Button size="sm" variant="outline" onClick={() => nav('/posts')} data-testid="go-post-panel"><Image className="w-3 h-3 mr-1" />Post Panel</Button><Button size="sm" variant="outline" onClick={() => nav('/leads')}>All Leads</Button></div>
    <PipelineRow pipeline={s.my_pipeline} />
    <Tabs defaultValue="meta_ads"><TabsList className="grid grid-cols-3 w-full md:w-96 h-auto"><TabsTrigger value="meta_ads" className="text-xs">Meta Ads ({s.leads_by_source?.meta_ads?.length||0})</TabsTrigger><TabsTrigger value="job_portal" className="text-xs">Portals ({s.leads_by_source?.job_portal?.length||0})</TabsTrigger><TabsTrigger value="manual" className="text-xs">Manual ({s.leads_by_source?.manual?.length||0})</TabsTrigger></TabsList>
    {['meta_ads','job_portal','manual'].map(src => <TabsContent key={src} value={src} className="mt-2"><LeadTable leads={s.leads_by_source?.[src]} /></TabsContent>)}</Tabs>
    {s.recent_calls?.length > 0 && <Card className="border-slate-200 shadow-none"><CardHeader className="pb-2"><CardTitle className="text-base font-medium">Recent Calls</CardTitle></CardHeader><CardContent><div className="space-y-1">{s.recent_calls.map(c => <div key={c.id} className="p-2 rounded border border-slate-100 text-sm"><p className="text-slate-700">{c.notes}</p><p className="text-xs text-slate-400">{new Date(c.call_date).toLocaleString()}</p></div>)}</div></CardContent></Card>}
    <FranchisesCard data={s.franchises} />
    <MeetingButtons />
  </div>);
}

// ===================== FRANCHISE EXECUTIVE =====================
function FDEDash({ s, u }) {
  const nav = useNavigate();
  return (<div className="space-y-5" data-testid="fde-dashboard">
    <h1 className="text-2xl font-heading font-semibold text-slate-900">Franchise Executive</h1>
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3"><KPI icon={Users} label="My Leads" value={s.my_leads_count} color="text-blue-700" to="/leads" /><KPI icon={Phone} label="Calls Today" value={s.calls_today} color="text-emerald-600" to="/leads" /><KPI icon={Phone} label="Total Calls" value={s.total_calls} color="text-amber-600" to="/leads" /><KPI icon={Briefcase} label="Tech Jobs" value={s.jobs?.length} color="text-violet-600" to="/jobs" /></div>
    {s.jobs?.length > 0 && <div className="flex flex-wrap gap-1">{s.jobs.slice(0,6).map(j => <Badge key={j.id} variant="outline" className="cursor-pointer hover:border-blue-400 hover:bg-blue-50" onClick={() => nav('/jobs')} data-testid={`fde-job-${j.id}`}>{j.role} - {j.location}</Badge>)}</div>}
    <PipelineRow pipeline={s.my_pipeline} />
    <Tabs defaultValue="meta_ads"><TabsList className="grid grid-cols-3 w-full md:w-96 h-auto"><TabsTrigger value="meta_ads" className="text-xs">Meta Ads ({s.leads_by_source?.meta_ads?.length||0})</TabsTrigger><TabsTrigger value="job_portal" className="text-xs">Portals ({s.leads_by_source?.job_portal?.length||0})</TabsTrigger><TabsTrigger value="manual" className="text-xs">Manual ({s.leads_by_source?.manual?.length||0})</TabsTrigger></TabsList>
    {['meta_ads','job_portal','manual'].map(src => <TabsContent key={src} value={src} className="mt-2"><LeadTable leads={s.leads_by_source?.[src]} showBranch /></TabsContent>)}</Tabs>
    {s.recent_calls?.length > 0 && <Card className="border-slate-200 shadow-none"><CardHeader className="pb-2"><CardTitle className="text-base font-medium">Recent Calls</CardTitle></CardHeader><CardContent><div className="space-y-1">{s.recent_calls.map(c => <div key={c.id} className="p-2 rounded border border-slate-100 text-sm"><p className="text-slate-700">{c.notes}</p><p className="text-xs text-slate-400">{new Date(c.call_date).toLocaleString()}</p></div>)}</div></CardContent></Card>}
    <FranchisesCard data={s.franchises} />
    <MeetingButtons />
  </div>);
}

// ===================== GRAPHIC DESIGNER =====================
function DesignerDash({ s }) {
  const nav = useNavigate();
  const [designReqs, setDesignReqs] = useState([]);
  useEffect(() => { API.get('/design-requests').then(r => setDesignReqs(r.data)).catch(() => {}); }, []);
  const pendingCount = designReqs.filter(r => r.status === 'pending').length;
  const updateStatus = async (id, status) => {
    try { await API.put(`/design-requests/${id}`, { status }); setDesignReqs(designReqs.map(d => d.id === id ? { ...d, status } : d)); }
    catch (e) { /* noop */ }
  };
  return (<div className="space-y-5" data-testid="designer-dashboard">
    <h1 className="text-2xl font-heading font-semibold text-slate-900">Design Dashboard</h1>
    <div className="grid grid-cols-3 gap-3"><KPI icon={Image} label="Pending Posts" value={s.total_pending} color="text-amber-600" to="/posts" /><KPI icon={CheckSquare} label="Completed" value={s.total_completed} color="text-emerald-600" to="/posts" /><KPI icon={Image} label="Chat Design Requests" value={pendingCount} color="text-pink-600" /></div>
    <Button className="bg-blue-700 hover:bg-blue-800" onClick={() => nav('/posts')} data-testid="go-post-panel"><Image className="w-4 h-4 mr-1" />Open Post Panel</Button>

    {/* Chat-Origin Design Requests */}
    <Card className="border-slate-200 shadow-none" data-testid="chat-design-requests-card">
      <CardHeader className="pb-2"><CardTitle className="text-base font-medium text-pink-700">Design Requests (from Chat)</CardTitle></CardHeader>
      <CardContent>
        {!designReqs.length ? <p className="text-sm text-slate-500">No design requests yet</p> : (
          <div className="space-y-2">
            {designReqs.map(r => (
              <div key={r.id} className="p-3 rounded-lg border border-slate-200 bg-white" data-testid={`design-req-${r.id}`}>
                <div className="flex items-center justify-between gap-2">
                  <p className="font-medium text-sm text-slate-900 truncate">{r.title}</p>
                  <Badge className={r.priority === 'urgent' ? 'bg-rose-100 text-rose-700 border-0' : r.priority === 'high' ? 'bg-amber-100 text-amber-700 border-0' : 'bg-slate-100 text-slate-700 border-0'}>{r.priority}</Badge>
                </div>
                <p className="text-xs text-slate-500 mt-1">{r.description}</p>
                <p className="text-xs text-slate-400 mt-1">By {r.requested_by_name} ({r.requested_by_role}) · {r.branch_department || '—'} · {r.required_date || 'no date'}</p>
                <div className="flex gap-1 mt-2">
                  {['pending', 'in_progress', 'completed'].map(st => (
                    <button
                      key={st}
                      onClick={() => updateStatus(r.id, st)}
                      className={`px-2 py-0.5 text-xs rounded border transition-all ${r.status === st ? 'bg-blue-700 text-white border-blue-700' : 'bg-white text-slate-600 border-slate-200 hover:border-slate-300'}`}
                      data-testid={`design-status-${r.id}-${st}`}
                    >{st}</button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>

    <Card className="border-slate-200 shadow-none"><CardHeader className="pb-2"><CardTitle className="text-base font-medium text-amber-700">Pending Post Requests ({s.total_pending})</CardTitle></CardHeader><CardContent>{!s.pending_requests?.length ? <p className="text-sm text-slate-500">No pending requests</p> : <div className="space-y-2">{s.pending_requests.map(r => (
      <div key={r.id} onClick={() => nav('/posts')} className="p-3 rounded-lg border border-amber-200 bg-amber-50/30 cursor-pointer hover:bg-amber-50/50 transition-colors" data-testid={`design-pending-${r.id}`}><p className="font-medium text-sm text-slate-900">{r.role} - {r.job_info}</p><p className="text-xs text-slate-500 mt-1">Requested by: {r.requested_by_name}</p><p className="text-xs text-slate-400">{new Date(r.created_at).toLocaleString()}</p></div>
    ))}</div>}</CardContent></Card>
    {s.my_posts?.length > 0 && <Card className="border-slate-200 shadow-none"><CardHeader className="pb-2"><CardTitle className="text-base font-medium">My Uploads</CardTitle></CardHeader><CardContent><div className="space-y-2">{s.my_posts.map(p => (
      <div key={p.id} onClick={() => nav('/posts')} className="flex items-center justify-between p-2 rounded border border-slate-200 cursor-pointer hover:border-blue-300 hover:bg-blue-50/30 transition-all" data-testid={`design-upload-${p.id}`}><div><p className="text-sm font-medium text-slate-900">{p.role}</p><p className="text-xs text-slate-500">{p.file_name}</p></div><Badge className={p.review_status==='approved'?'bg-emerald-100 text-emerald-700 border-0':'bg-amber-100 text-amber-700 border-0'}>{p.review_status}</Badge></div>
    ))}</div></CardContent></Card>}
    <FranchisesCard data={s.franchises} />
    <MeetingButtons />
  </div>);
}

// ===================== MARKETING COORDINATOR =====================
function MktgCoordDash({ s }) {
  const nav = useNavigate();
  return (<div className="space-y-5" data-testid="mktg-coord-dashboard">
    <h1 className="text-2xl font-heading font-semibold text-slate-900">Marketing Dashboard</h1>
    <div className="grid grid-cols-3 gap-3"><KPI icon={Clock} label="Pending" value={s.pending_count} color="text-amber-600" to="/campaigns" /><KPI icon={Megaphone} label="Running" value={s.running_count} color="text-blue-700" to="/campaigns" /><KPI icon={CheckSquare} label="Completed" value={s.completed_count} color="text-emerald-600" to="/campaigns" /></div>
    <Button className="bg-blue-700 hover:bg-blue-800" onClick={() => nav('/campaigns')} data-testid="go-campaigns"><Megaphone className="w-4 h-4 mr-1" />View All Campaigns</Button>
    <Card className="border-slate-200 shadow-none"><CardHeader className="pb-2"><CardTitle className="text-base font-medium">My Campaigns</CardTitle></CardHeader><CardContent>{!s.campaigns?.length ? <p className="text-sm text-slate-500">No campaigns</p> : <div className="space-y-2">{s.campaigns.map(c => (
      <div key={c.id} onClick={() => nav('/campaigns')} className="flex items-center justify-between p-3 rounded border border-slate-200 cursor-pointer hover:border-blue-300 hover:bg-blue-50/30 transition-all" data-testid={`mktg-camp-${c.id}`}><div><p className="text-sm font-medium text-slate-900">{c.role} - {c.location}</p><p className="text-xs text-slate-500">Platform: {c.platform?.replace('_',' ')}</p></div><Badge className={c.status==='running'?'bg-blue-100 text-blue-700 border-0':c.status==='completed'?'bg-emerald-100 text-emerald-700 border-0':'bg-amber-100 text-amber-700 border-0'}>{c.status}</Badge></div>
    ))}</div>}</CardContent></Card>
    <FranchisesCard data={s.franchises} />
    <MeetingButtons />
  </div>);
}

// ===================== GENERIC EXECUTOR =====================
function GenericExecDash({ s, u }) {
  const nav = useNavigate();
  return (<div className="space-y-5" data-testid="executor-dashboard">
    <h1 className="text-2xl font-heading font-semibold text-slate-900">Welcome, {u?.name?.split(' ')[0]}</h1>
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3"><KPI icon={Users} label="My Leads" value={s.my_leads_count} color="text-blue-700" to="/leads" /><KPI icon={Phone} label="Calls Today" value={s.calls_today} color="text-emerald-600" to="/leads" /><KPI icon={CheckSquare} label="Pending Tasks" value={s.pending_tasks_count} color="text-amber-600" to="/tasks" /><KPI icon={Briefcase} label="Pipeline" value={Object.values(s.my_pipeline||{}).reduce((a,b)=>a+b,0)} color="text-violet-600" to="/leads" /></div>
    <PipelineRow pipeline={s.my_pipeline} />
    <LeadTable leads={s.my_leads} />
    <FranchisesCard data={s.franchises} />
    <MeetingButtons />
  </div>);
}
