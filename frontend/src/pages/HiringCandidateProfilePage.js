import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import API from '@/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import {
  ArrowLeft, User, Briefcase, IndianRupee, FileText, Download, Activity,
  Phone, Mail, MapPin, Calendar, UserCheck, CheckCircle2, Circle, ChevronRight, Trash2,
} from 'lucide-react';
import { toast } from 'sonner';

const STAGE_LABELS = {
  new_lead: 'New',
  qualified: 'Qualified',
  hr_interview: 'Interview Scheduled',
  manager_interview: 'Interview Completed',
  hold: 'Hold',
  selected: 'Selected',
  joined: 'Joined',
  three_months: 'Joined',
  rejected: 'Rejected',
};
const STAGE_COLORS = {
  new_lead: 'bg-slate-100 text-slate-700',
  qualified: 'bg-sky-100 text-sky-700',
  hr_interview: 'bg-amber-100 text-amber-700',
  manager_interview: 'bg-indigo-100 text-indigo-700',
  hold: 'bg-rose-100 text-rose-700',
  selected: 'bg-emerald-100 text-emerald-700',
  joined: 'bg-emerald-200 text-emerald-800',
  three_months: 'bg-emerald-200 text-emerald-800',
  rejected: 'bg-slate-200 text-slate-600',
};

const fmtDate = (iso) => {
  if (!iso) return '—';
  try { return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' }); }
  catch { return iso; }
};
const fmtDateTime = (iso) => {
  if (!iso) return '—';
  try { return new Date(iso).toLocaleString(undefined, { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }); }
  catch { return iso; }
};
const fmtMoney = (v) => {
  if (v === null || v === undefined || v === '') return '—';
  try { return `₹${Number(v).toLocaleString('en-IN')}`; } catch { return v; }
};

const InfoRow = ({ icon: Icon, label, value, testId }) => (
  <div className="flex items-start gap-2 py-1.5" data-testid={testId}>
    {Icon ? <Icon className="w-3.5 h-3.5 mt-0.5 text-slate-400 shrink-0" /> : <span className="w-3.5" />}
    <div className="min-w-0 flex-1">
      <p className="text-[10px] uppercase tracking-wider text-slate-400">{label}</p>
      <p className="text-sm text-slate-900 mt-0.5 break-words">{value || '—'}</p>
    </div>
  </div>
);

export default function HiringCandidateProfilePage() {
  const { candidateId, segment, designationId } = useParams();
  const nav = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await API.get(`/hirings/candidates/${candidateId}`);
      setData(data);
    } catch {
      toast.error('Failed to load candidate profile');
    } finally {
      setLoading(false);
    }
  }, [candidateId]);

  useEffect(() => { fetchData(); }, [fetchData]);

  if (loading) return <div className="flex items-center justify-center h-64 text-slate-500">Loading...</div>;
  if (!data) return <div className="p-6 text-slate-500">Candidate not found.</div>;

  const c = data.candidate || {};
  const d = data.designation;
  const stages = data.stages || [];
  const officeType = d?.office_type;
  const currentStageInternal = c.current_stage;
  const currentDisplay = data.current_stage_display;

  const backTarget = designationId
    ? `/hirings/${segment || (c.is_technician ? 'franchise' : 'head_office')}/designations/${designationId}`
    : '/hirings';

  const handleConfirmDelete = async () => {
    setDeleting(true);
    try {
      await API.delete(`/hirings/candidates/${c.id}`);
      toast.success('Lead deleted');
      setDeleteOpen(false);
      nav(backTarget);
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Failed to delete lead');
    } finally {
      setDeleting(false);
    }
  };

  // Resume URL
  const resumeUrl = c.resume_url || c.resume_path || c.resume;
  const apiBase = process.env.REACT_APP_BACKEND_URL || '';
  const fullResumeUrl = resumeUrl
    ? (resumeUrl.startsWith('http') ? resumeUrl : `${apiBase}${resumeUrl.startsWith('/') ? '' : '/'}${resumeUrl}`)
    : null;

  return (
    <div className="space-y-5" data-testid="hiring-candidate-profile-page">
      <button
        type="button"
        onClick={() => nav(backTarget)}
        className="inline-flex items-center text-sm text-slate-600 hover:text-blue-700"
        data-testid="back-to-candidates"
      >
        <ArrowLeft className="w-4 h-4 mr-1" /> Back
      </button>

      {/* Header */}
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-2xl font-heading font-semibold text-slate-900">{c.name}</h1>
          <div className="flex items-center gap-2 mt-2 flex-wrap">
            {d?.name && (
              <Badge className="bg-blue-700 text-white border-0 text-xs px-2.5 py-0.5">{d.name}</Badge>
            )}
            {officeType && (
              <Badge className={`text-[10px] border-0 ${officeType === 'franchise' ? 'bg-violet-100 text-violet-700' : 'bg-blue-100 text-blue-700'}`}>
                {officeType === 'franchise' ? 'Franchise' : 'Head Office'}
              </Badge>
            )}
            <Badge
              className={`text-[10px] border-0 ${STAGE_COLORS[currentStageInternal] || 'bg-slate-100 text-slate-700'}`}
              data-testid="current-stage-badge"
            >
              {STAGE_LABELS[currentStageInternal] || currentDisplay}
            </Badge>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={() => setDeleteOpen(true)}
            className="text-rose-600 border-rose-200 hover:bg-rose-50 hover:text-rose-700"
            data-testid="delete-lead-btn"
          >
            <Trash2 className="w-4 h-4 mr-1" /> Delete Lead
          </Button>
          <Button
            variant="outline"
            onClick={() => nav(`/leads/${c.id}`)}
            data-testid="open-full-pipeline"
          >
            Manage in Pipeline <ChevronRight className="w-4 h-4 ml-1" />
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Left column: Personal + Hiring + Salary + Description + Resume */}
        <div className="lg:col-span-2 space-y-4">
          {/* Personal Information */}
          <Card className="border-slate-200 shadow-none" data-testid="card-personal">
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2"><User className="w-4 h-4 text-blue-700" /> Personal Information</CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-x-4 gap-y-1">
              <InfoRow icon={User} label="Name" value={c.name} testId="info-name" />
              <InfoRow icon={Phone} label="Mobile Number" value={c.phone} testId="info-phone" />
              <InfoRow icon={Mail} label="Email" value={c.email} testId="info-email" />
              <InfoRow icon={MapPin} label="City" value={c.location_city} testId="info-city" />
              <InfoRow icon={MapPin} label="Area" value={c.location_area} testId="info-area" />
            </CardContent>
          </Card>

          {/* Hiring Information */}
          <Card className="border-slate-200 shadow-none" data-testid="card-hiring">
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2"><Briefcase className="w-4 h-4 text-blue-700" /> Hiring Information</CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-x-4 gap-y-1">
              <InfoRow icon={Briefcase} label="Designation" value={d?.name || c.job_role} testId="info-designation" />
              <InfoRow icon={Briefcase} label="Office Type" value={officeType === 'franchise' ? 'Franchise' : (officeType === 'head_office' ? 'Head Office' : '—')} testId="info-office-type" />
              <InfoRow icon={Activity} label="Source" value={c.source} testId="info-source" />
              <InfoRow icon={UserCheck} label="Assigned To" value={data.assigned_to_user?.name} testId="info-assigned-to" />
              <InfoRow icon={Calendar} label="Applied Date" value={fmtDate(c.created_at)} testId="info-applied-date" />
              <InfoRow icon={Activity} label="Current Stage" value={STAGE_LABELS[currentStageInternal] || currentDisplay} testId="info-current-stage" />
            </CardContent>
          </Card>

          {/* Salary Information */}
          <Card className="border-slate-200 shadow-none" data-testid="card-salary">
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2"><IndianRupee className="w-4 h-4 text-blue-700" /> Salary Information</CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-x-4 gap-y-1">
              <InfoRow icon={IndianRupee} label="Min Salary" value={fmtMoney(c.min_salary)} testId="info-min-salary" />
              <InfoRow icon={IndianRupee} label="Max Salary" value={fmtMoney(c.max_salary)} testId="info-max-salary" />
            </CardContent>
          </Card>

          {/* Description */}
          <Card className="border-slate-200 shadow-none" data-testid="card-description">
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2"><FileText className="w-4 h-4 text-blue-700" /> Description</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-slate-700 whitespace-pre-wrap min-h-[40px]" data-testid="info-description">
                {c.description || <span className="text-slate-400 italic">No description provided.</span>}
              </p>
            </CardContent>
          </Card>

          {/* Resume */}
          <Card className="border-slate-200 shadow-none" data-testid="card-resume">
            <CardHeader className="pb-2 flex flex-row items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2"><FileText className="w-4 h-4 text-blue-700" /> Resume</CardTitle>
              {fullResumeUrl && (
                <Button asChild variant="outline" size="sm" data-testid="resume-download-btn">
                  <a href={fullResumeUrl} target="_blank" rel="noreferrer noopener" download>
                    <Download className="w-3.5 h-3.5 mr-1.5" /> Download
                  </a>
                </Button>
              )}
            </CardHeader>
            <CardContent>
              {fullResumeUrl ? (
                <div className="border border-slate-200 rounded overflow-hidden" style={{ height: 400 }}>
                  <iframe
                    src={fullResumeUrl}
                    title="Resume preview"
                    className="w-full h-full"
                    data-testid="resume-preview-iframe"
                  />
                </div>
              ) : (
                <p className="text-sm text-slate-400 italic" data-testid="resume-empty">No resume uploaded.</p>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right column: Lead Stage indicator + Timeline */}
        <div className="space-y-4">
          {/* Stage Indicator */}
          <Card className="border-slate-200 shadow-none" data-testid="card-lead-stage">
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2"><Activity className="w-4 h-4 text-blue-700" /> Lead Information</CardTitle>
            </CardHeader>
            <CardContent>
              <ol className="space-y-2" data-testid="stage-indicator-list">
                {stages.map((s) => {
                  const isCurrent = (currentStageInternal === s.key)
                    || (s.key === 'joined' && currentStageInternal === 'three_months');
                  const sequence = stages.map(x => x.key);
                  const curIdxStage = currentStageInternal === 'three_months' ? 'joined' : currentStageInternal;
                  const curIdx = sequence.indexOf(curIdxStage);
                  const myIdx = sequence.indexOf(s.key);
                  const isPast = myIdx >= 0 && curIdx >= 0 && myIdx < curIdx && curIdxStage !== 'rejected';
                  return (
                    <li
                      key={s.key}
                      className={`flex items-center gap-2 px-2 py-1.5 rounded ${isCurrent ? 'bg-blue-50 border border-blue-200' : ''}`}
                      data-testid={`stage-step-${s.key}`}
                    >
                      {isCurrent ? (
                        <CheckCircle2 className="w-4 h-4 text-blue-700 shrink-0" />
                      ) : isPast ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                      ) : (
                        <Circle className="w-4 h-4 text-slate-300 shrink-0" />
                      )}
                      <span className={`text-sm ${isCurrent ? 'font-semibold text-blue-800' : isPast ? 'text-slate-700' : 'text-slate-400'}`}>
                        {s.label}
                      </span>
                    </li>
                  );
                })}
              </ol>
            </CardContent>
          </Card>

          {/* Activity Timeline */}
          <Card className="border-slate-200 shadow-none" data-testid="card-timeline">
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2"><Activity className="w-4 h-4 text-blue-700" /> Activity Timeline</CardTitle>
            </CardHeader>
            <CardContent>
              {(!data.timeline || data.timeline.length === 0) ? (
                <p className="text-xs text-slate-400 italic">No activity yet.</p>
              ) : (
                <ol className="space-y-3 max-h-[480px] overflow-y-auto pr-1" data-testid="timeline-list">
                  {data.timeline.map((e, idx) => (
                    <li key={idx} className="relative pl-5">
                      <span className={`absolute left-0 top-1 w-2 h-2 rounded-full ${e.kind === 'created' ? 'bg-emerald-500' : e.kind === 'call' ? 'bg-amber-500' : 'bg-blue-500'}`} />
                      <p className="text-xs font-medium text-slate-800">{e.title}</p>
                      {e.notes && <p className="text-xs text-slate-600 mt-0.5">{e.notes}</p>}
                      <p className="text-[10px] text-slate-400 mt-0.5">
                        {e.actor ? `${e.actor} · ` : ''}{fmtDateTime(e.timestamp)}
                      </p>
                    </li>
                  ))}
                </ol>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Delete Lead Confirmation Dialog */}
      <AlertDialog open={deleteOpen} onOpenChange={(v) => { if (!deleting) setDeleteOpen(v); }}>
        <AlertDialogContent data-testid="delete-lead-dialog">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-rose-600">Delete Lead</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to permanently delete{c?.name ? ` ${c.name}` : ' this lead'}?
              <br />
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleting} data-testid="cancel-delete-lead-btn">Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={(e) => { e.preventDefault(); handleConfirmDelete(); }}
              disabled={deleting}
              className="bg-rose-600 hover:bg-rose-700 focus:ring-rose-600"
              data-testid="confirm-delete-lead-btn"
            >
              {deleting ? 'Deleting…' : 'Delete'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
