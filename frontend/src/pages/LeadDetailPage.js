import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import API from '@/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { ArrowLeft, Phone, Mail, MapPin, ChevronRight, Star as StarIcon, Pause, PlayCircle, FileText, Heart, Upload, Trash2, Send, Copy, ExternalLink, Lock } from 'lucide-react';
import { toast } from 'sonner';
import InterviewFormDialog from '@/components/InterviewFormDialog';
import { StarRating } from '@/components/StarRating';

const STAGE_LABELS = {
  new_lead: 'New',
  qualified: 'Qualified',
  hr_interview: 'HR',
  manager_interview: 'Manager',
  selected: 'Selected',
  three_months: '3 Months',
  hold: 'Hold',
  joined: 'Joined',
  rejected: 'Rejected',
  move_ahead: 'Selected',
  dead: 'Rejected',
};

const STAGE_COLORS = {
  new_lead: 'bg-blue-100 text-blue-700',
  qualified: 'bg-emerald-100 text-emerald-700',
  hr_interview: 'bg-amber-100 text-amber-700',
  manager_interview: 'bg-violet-100 text-violet-700',
  selected: 'bg-teal-100 text-teal-700',
  three_months: 'bg-indigo-100 text-indigo-700',
  hold: 'bg-orange-100 text-orange-700',
  joined: 'bg-green-100 text-green-700',
  rejected: 'bg-rose-100 text-rose-700',
  move_ahead: 'bg-teal-100 text-teal-700',
  dead: 'bg-rose-100 text-rose-700',
};

const REJECTION_REASONS = ['not_interested', 'salary_mismatch', 'location_issue', 'no_response', 'hired_elsewhere', 'failed_interview', 'other'];
const HOLD_REASONS = ['awaiting_response', 'salary_negotiation', 'reference_check', 'candidate_request', 'internal_review', 'other'];
const INTERVIEW_MODES = ['in_person', 'video', 'phone'];

const HO_LINEAR = ['new_lead', 'qualified', 'hr_interview', 'manager_interview', 'selected', 'three_months', 'joined'];
const TECH_LINEAR = ['new_lead', 'qualified', 'hr_interview', 'selected', 'three_months', 'joined'];

function FormStatusBadge({ status }) {
  const map = {
    not_sent: { label: 'Form Not Sent', cls: 'bg-slate-100 text-slate-600 border-slate-200' },
    sent: { label: 'Form Sent', cls: 'bg-amber-50 text-amber-700 border-amber-200' },
    completed: { label: 'Form Completed', cls: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  };
  const s = map[status] || map.not_sent;
  return (
    <Badge variant="outline" className={`text-[10px] ${s.cls}`} data-testid={`form-status-badge-${status}`}>
      {s.label}
    </Badge>
  );
}

function getNextStage(current, isTech) {
  const order = isTech ? TECH_LINEAR : HO_LINEAR;
  // Treat legacy `move_ahead` as `selected`
  if (current === 'move_ahead') current = 'selected';
  if (current === 'dead') current = 'rejected';
  if (current === 'hold' || current === 'rejected') return null;
  const idx = order.indexOf(current);
  if (idx >= 0 && idx < order.length - 1) return order[idx + 1];
  return null;
}

function ScheduleRow({ title, d }) {
  return (
    <div className="p-2 rounded border border-slate-100 text-sm">
      <p className="font-medium text-slate-900">{title}</p>
      <p className="text-xs text-slate-500">
        {d.interview_date} {d.interview_time && `at ${d.interview_time}`} · {d.mode?.replace('_', ' ')}
        {d.interview_city && ` · ${d.interview_city}`}
        {d.interview_place && ` · ${d.interview_place}`}
      </p>
    </div>
  );
}

export default function LeadDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user: currentUser } = useAuth();
  const [lead, setLead] = useState(null);
  const [history, setHistory] = useState([]);
  const [calls, setCalls] = useState([]);
  const [interviews, setInterviews] = useState({ hr: null, manager: null });
  const [managers, setManagers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [transitionOpen, setTransitionOpen] = useState(false);
  const [targetStage, setTargetStage] = useState('');
  const [formData, setFormData] = useState({});
  const [callNote, setCallNote] = useState('');
  const [callDialogOpen, setCallDialogOpen] = useState(false);
  const [converting, setConverting] = useState(false);
  const [convertForm, setConvertForm] = useState({ joining_date: '', role: '', branch_id: '', department: '', category: '', employment_type: '' });
  const [convertOpen, setConvertOpen] = useState(false);
  const [interviewDialog, setInterviewDialog] = useState({ open: false, round: 'hr' });
  const [deleteConfirm, setDeleteConfirm] = useState(false);
  const [sendFormOpen, setSendFormOpen] = useState(false);
  const [formStatus, setFormStatus] = useState({ status: 'not_sent' });
  const [sendingForm, setSendingForm] = useState(false);
  const [sendFormResult, setSendFormResult] = useState(null);
  // Role / Job assignment
  const [roleDialogOpen, setRoleDialogOpen] = useState(false);
  const [jobs, setJobs] = useState([]);
  const [selectedJobId, setSelectedJobId] = useState('');
  const [savingRole, setSavingRole] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [leadRes, historyRes, callsRes, ivRes, usersRes, formRes] = await Promise.all([
        API.get(`/leads/${id}`),
        API.get(`/leads/${id}/history`),
        API.get(`/leads/${id}/calls`),
        API.get(`/interviews/${id}`),
        API.get('/users'),
        API.get(`/candidate-forms/${id}`).catch(() => ({ data: { status: 'not_sent' } })),
      ]);
      setLead(leadRes.data);
      setHistory(historyRes.data);
      setCalls(callsRes.data);
      setInterviews(ivRes.data);
      setFormStatus(formRes.data);
      const mgrRoles = ['Marketing Manager', 'Operations Manager', 'Sales Manager', 'Accounts Manager'];
      setManagers((usersRes.data || []).filter(u => mgrRoles.includes(u.role)));
    } catch { toast.error('Failed to load lead details'); }
    finally { setLoading(false); }
  }, [id]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const openRoleDialog = async () => {
    setSelectedJobId(lead?.job_id || '');
    setRoleDialogOpen(true);
    if (jobs.length === 0) {
      try {
        const { data } = await API.get('/jobs');
        // Filter by the appropriate segment (technician = franchise/branch)
        const isTech = !!lead?.is_technician;
        const filtered = (data || []).filter(j => {
          const isFranchise = j.type === 'branch' || !!j.branch_id;
          return isTech ? isFranchise : !isFranchise;
        });
        setJobs(filtered);
      } catch {
        toast.error('Could not load jobs');
      }
    }
  };

  const saveRole = async () => {
    setSavingRole(true);
    try {
      const payload = { job_id: selectedJobId || '' };
      const { data } = await API.put(`/leads/${id}`, payload);
      setLead(data);
      toast.success(selectedJobId ? 'Role updated' : 'Role removed');
      setRoleDialogOpen(false);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update role');
    } finally {
      setSavingRole(false);
    }
  };

  const handleResumeUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const formDataUpload = new FormData();
    formDataUpload.append('file', file);
    try {
      await API.post(`/leads/${id}/resume`, formDataUpload, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      toast.success('Resume uploaded');
      fetchData();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Upload failed');
    } finally {
      e.target.value = '';
    }
  };

  const [medicalOpen, setMedicalOpen] = useState(false);
  const [medicalForm, setMedicalForm] = useState({});
  const openMedical = () => {
    setMedicalForm(lead?.medical_info || {});
    setMedicalOpen(true);
  };
  const handleSaveMedical = async () => {
    try {
      await API.put(`/leads/${id}/medical`, medicalForm);
      toast.success('Medical info updated');
      setMedicalOpen(false);
      fetchData();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Failed to save');
    }
  };

  const openTransition = (stage) => {
    setTargetStage(stage);
    setFormData({});
    setTransitionOpen(true);
  };

  const handleTransition = async () => {
    try {
      await API.post(`/leads/${id}/transition`, { to_stage: targetStage, form_data: formData });
      toast.success(`Moved to ${STAGE_LABELS[targetStage]}`);
      setTransitionOpen(false);
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Transition failed');
    }
  };

  const handleAddCall = async () => {
    try {
      await API.post(`/leads/${id}/calls`, { notes: callNote });
      toast.success('Call logged');
      setCallNote('');
      setCallDialogOpen(false);
      fetchData();
    } catch { toast.error('Failed to log call'); }
  };

  const handleConvert = async () => {
    setConverting(true);
    try {
      const payload = { ...convertForm };
      if (!payload.branch_id) payload.branch_id = null;
      if (!payload.department) payload.department = null;
      if (!payload.category) delete payload.category;
      if (!payload.employment_type) delete payload.employment_type;
      await API.post(`/employees/convert/${id}`, payload);
      toast.success('Lead converted to employee!');
      setConvertOpen(false);
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Conversion failed');
    } finally { setConverting(false); }
  };

  if (loading) return <div className="flex items-center justify-center h-64 text-slate-500">Loading...</div>;
  if (!lead) return <div className="text-center py-12 text-slate-500">Lead not found</div>;

  const isTech = !!lead.is_technician;
  const nextStage = getNextStage(lead.current_stage, isTech);
  const canResumeFromHold = lead.current_stage === 'hold' && lead.previous_stage;

  // Determine if a gate (interview) is required before clicking "Move to Next"
  const nextGateRound = (() => {
    if (nextStage === 'manager_interview') return interviews.hr ? null : 'hr';
    if (nextStage === 'selected') {
      return isTech ? (interviews.hr ? null : 'hr') : (interviews.manager ? null : 'manager');
    }
    return null;
  })();

  return (
    <div className="space-y-4 max-w-2xl" data-testid="lead-detail-page">
      <Button variant="ghost" onClick={() => navigate(lead.is_technician ? '/leads/franchise' : '/leads/head-office')} className="text-slate-500 -ml-2" data-testid="back-to-leads">
        <ArrowLeft className="w-4 h-4 mr-1" /> Back to Pipeline
      </Button>

      {/* Lead Info */}
      <Card className="border-slate-200 shadow-none">
        <CardContent className="p-4">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-xl font-heading font-semibold text-slate-900">{lead.name}</h2>
              <div className="mt-1.5">
                {lead.job_role ? (
                  <button
                    type="button"
                    onClick={openRoleDialog}
                    className="inline-flex items-center gap-1.5 group focus:outline-none"
                    data-testid="lead-job-role-edit-btn"
                  >
                    <Badge
                      className="bg-blue-700 text-white border-0 text-sm font-medium px-3 py-1 group-hover:bg-blue-800 transition-colors"
                      data-testid="lead-job-role-badge"
                    >
                      {lead.job_role}
                    </Badge>
                    <span className="text-xs text-blue-700 underline-offset-2 group-hover:underline">Change</span>
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={openRoleDialog}
                    className="inline-flex items-center gap-1.5 group focus:outline-none"
                    data-testid="lead-job-role-edit-btn"
                  >
                    <Badge
                      variant="outline"
                      className="bg-slate-50 text-slate-400 italic border-slate-200 text-sm px-3 py-1 group-hover:border-blue-400 group-hover:text-blue-600 transition-colors"
                      data-testid="lead-job-role-badge"
                    >
                      Role not specified
                    </Badge>
                    <span className="text-xs text-blue-700 underline-offset-2 group-hover:underline">Assign role</span>
                  </button>
                )}
              </div>
              <div className="flex flex-wrap items-center gap-3 mt-2 text-sm text-slate-500">
                {lead.phone && <span className="flex items-center gap-1"><Phone className="w-3 h-3" />{lead.phone}</span>}
                {lead.email && <span className="flex items-center gap-1"><Mail className="w-3 h-3" />{lead.email}</span>}
                {(lead.location_city || lead.location_area) && (
                  <span className="flex items-center gap-1"><MapPin className="w-3 h-3" />{lead.location_city}{lead.location_area && `, ${lead.location_area}`}</span>
                )}
              </div>
            </div>
            <div className="flex flex-col items-end gap-1">
              <Badge className={`${STAGE_COLORS[lead.current_stage] || 'bg-slate-100 text-slate-700'} border-0`}>{STAGE_LABELS[lead.current_stage] || lead.current_stage}</Badge>
              {isTech ? (
                <Badge variant="outline" className="text-xs text-blue-700 border-blue-200">Technician</Badge>
              ) : (
                <Badge variant="outline" className="text-xs text-slate-600 border-slate-200">Head Office</Badge>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2 mt-3 text-xs text-slate-400 flex-wrap">
            <span>Source: {lead.source}</span>
            <span>Calls: {lead.total_calls}</span>
            {lead.last_call_date && <span>Last call: {new Date(lead.last_call_date).toLocaleDateString()}</span>}
            {lead.hold_reason && <span className="text-orange-600">Hold: {lead.hold_reason}</span>}
            {(lead.rejection_reason || lead.dead_reason) && <span className="text-rose-600">Reason: {lead.rejection_reason || lead.dead_reason}</span>}
            <FormStatusBadge status={formStatus.status} />
          </div>
        </CardContent>
      </Card>

      {/* Candidate Form Submission Card */}
      {formStatus.status === 'completed' && formStatus.submission && (
        <Card className="border-slate-200 shadow-none" data-testid="candidate-form-card">
          <CardHeader className="pb-2 flex flex-row items-center justify-between">
            <CardTitle className="text-base font-medium flex items-center gap-2">
              <FileText className="w-4 h-4 text-emerald-600" /> Candidate Information Form
            </CardTitle>
            <Badge className="bg-emerald-100 text-emerald-700 border-0 text-xs">Submitted {new Date(formStatus.completed_at).toLocaleDateString()}</Badge>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
              {Object.entries(formStatus.submission.answers || {}).slice(0, 12).map(([k, v]) => (
                v ? <div key={k}><span className="text-slate-400 capitalize">{k.replace(/_/g, ' ')}:</span> <span className="text-slate-700">{String(v)}</span></div> : null
              ))}
            </div>
            {Object.keys(formStatus.submission.documents || {}).length > 0 && (
              <div className="border-t border-slate-100 pt-2">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Documents</p>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(formStatus.submission.documents).map(([field, doc]) => (
                    <Button
                      key={field}
                      variant="outline"
                      size="sm"
                      className="h-7 text-xs"
                      data-testid={`download-doc-${field}`}
                      onClick={async () => {
                        try {
                          const res = await API.get(`/candidate-forms/${id}/document/${field}`, { responseType: 'blob' });
                          const url = window.URL.createObjectURL(new Blob([res.data]));
                          const a = document.createElement('a'); a.href = url; a.download = doc.filename || field;
                          document.body.appendChild(a); a.click(); a.remove();
                        } catch { toast.error(`Failed to download ${field}`); }
                      }}
                    >
                      <FileText className="w-3 h-3 mr-1" /> {field.toUpperCase()}
                    </Button>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Interview Summary */}
      {(lead.hr_interview_details || lead.manager_interview_details) && (
        <Card className="border-slate-200 shadow-none">
          <CardHeader className="pb-2"><CardTitle className="text-base font-medium">Interview Schedule</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {lead.hr_interview_details && <ScheduleRow title="HR Round" d={lead.hr_interview_details} />}
            {lead.manager_interview_details && <ScheduleRow title="Manager Round" d={lead.manager_interview_details} />}
          </CardContent>
        </Card>
      )}

      {/* Interview Summary */}
      {(interviews.hr || interviews.manager) && (
        <Card className="border-slate-200 shadow-none">
          <CardHeader className="pb-2"><CardTitle className="text-base font-medium">Interview Scores</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {interviews.hr && (
              <div className="flex items-center justify-between p-2 rounded border border-slate-100">
                <div>
                  <p className="text-sm font-medium text-slate-900">HR Round {interviews.hr.locked && '🔒'}</p>
                  <p className="text-xs text-slate-500">By {interviews.hr.submitted_by_name}</p>
                </div>
                <div className="flex items-center gap-2">
                  <StarRating value={Math.round(interviews.hr.avg_rating)} readOnly size={16} />
                  <Badge className="bg-amber-100 text-amber-700 border-0">{interviews.hr.avg_rating}/5</Badge>
                  <Button variant="ghost" size="sm" onClick={() => setInterviewDialog({ open: true, round: 'hr' })} data-testid="view-hr-interview">View</Button>
                </div>
              </div>
            )}
            {interviews.manager && (
              <div className="flex items-center justify-between p-2 rounded border border-slate-100">
                <div>
                  <p className="text-sm font-medium text-slate-900">Manager Round {interviews.manager.locked && '🔒'}</p>
                  <p className="text-xs text-slate-500">By {interviews.manager.submitted_by_name}</p>
                </div>
                <div className="flex items-center gap-2">
                  <StarRating value={Math.round(interviews.manager.avg_rating)} readOnly size={16} />
                  <Badge className="bg-violet-100 text-violet-700 border-0">{interviews.manager.avg_rating}/5</Badge>
                  <Button variant="ghost" size="sm" onClick={() => setInterviewDialog({ open: true, round: 'manager' })} data-testid="view-manager-interview">View</Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Action Buttons */}
      <div className="flex flex-wrap gap-2">
        {/* HR Round form: available when in HR Interview stage (or past it for edits) */}
        {['hr_interview', 'manager_interview', 'selected', 'three_months', 'move_ahead'].includes(lead.current_stage) && (
          <Button
            onClick={() => setInterviewDialog({ open: true, round: 'hr' })}
            className="bg-amber-600 hover:bg-amber-700"
            data-testid="open-hr-interview-button"
          >
            <StarIcon className="w-4 h-4 mr-1" /> HR Round Form {interviews.hr && '✓'}
          </Button>
        )}
        {/* Manager Round form (HO only). HR is BLOCKED. Only assigned Manager or CEO may submit. */}
        {!isTech && ['manager_interview', 'selected', 'three_months', 'move_ahead'].includes(lead.current_stage) && (() => {
          const role = (currentUser?.role || '').toLowerCase();
          const isHr = role === 'hr' || role.startsWith('sr hr') || role.startsWith('jr hr') || role.includes('hr');
          const isAssignedManager = lead.assigned_manager_id && lead.assigned_manager_id === currentUser?.id;
          const isCeo = role === 'ceo' || role === 'super admin';
          const canFill = (isAssignedManager || isCeo) && !isHr; // HR strictly cannot fill
          // HR can VIEW once a submission exists, but cannot fill.
          const canView = isHr || interviews.manager;
          return (
            <Button
              onClick={() => setInterviewDialog({ open: true, round: 'manager' })}
              className="bg-violet-600 hover:bg-violet-700 disabled:opacity-50"
              disabled={!canFill && !canView}
              title={!canFill ? (isHr ? 'HR cannot submit Manager evaluation — only the assigned Manager (or CEO) can.' : 'Only the assigned Manager (or CEO override) can fill this form') : ''}
              data-testid="open-manager-interview-button"
            >
              {!canFill && canView ? <Lock className="w-4 h-4 mr-1" /> : <StarIcon className="w-4 h-4 mr-1" />}
              Manager Round {interviews.manager ? '· View' : (canFill ? 'Form' : '· View Only')} {interviews.manager && '✓'}
            </Button>
          );
        })()}

        {nextStage && !['hold', 'rejected', 'dead', 'joined'].includes(lead.current_stage) && (
          <Button
            onClick={() => openTransition(nextStage)}
            className="bg-blue-700 hover:bg-blue-800 active:scale-[0.98]"
            disabled={!!nextGateRound}
            title={nextGateRound ? `Submit ${nextGateRound.toUpperCase()} interview first` : ''}
            data-testid="move-next-stage-button"
          >
            Move to {STAGE_LABELS[nextStage]} <ChevronRight className="w-4 h-4 ml-1" />
          </Button>
        )}

        {canResumeFromHold && (
          <Button
            onClick={() => openTransition(lead.previous_stage)}
            className="bg-teal-600 hover:bg-teal-700"
            data-testid="resume-from-hold-button"
          >
            <PlayCircle className="w-4 h-4 mr-1" /> Resume to {STAGE_LABELS[lead.previous_stage]}
          </Button>
        )}

        {!['hold', 'rejected', 'dead', 'joined'].includes(lead.current_stage) && (
          <Button variant="outline" onClick={() => openTransition('hold')} data-testid="move-hold-button" className="text-orange-600 hover:text-orange-700">
            <Pause className="w-4 h-4 mr-1" /> Hold
          </Button>
        )}
        {!['rejected', 'dead', 'joined'].includes(lead.current_stage) && (
          <Button variant="outline" className="text-rose-600 hover:text-rose-700" onClick={() => openTransition('rejected')} data-testid="move-rejected-button">Mark Rejected</Button>
        )}
        <Button variant="outline" onClick={() => setCallDialogOpen(true)} data-testid="add-call-button">
          <Phone className="w-4 h-4 mr-1" /> Log Call
        </Button>
        <Button
          variant="outline"
          className="text-blue-700 hover:text-blue-800"
          onClick={() => setSendFormOpen(true)}
          data-testid="send-candidate-form-button"
        >
          <Send className="w-4 h-4 mr-1" /> Send Candidate Form
        </Button>
        {(() => {
          const role = (currentUser?.role || '').toLowerCase();
          const isCeoHr = role === 'ceo' || role.includes('hr');
          const isOwner = currentUser?.id === lead.assigned_to || currentUser?.id === lead.created_by;
          if (!isCeoHr && !isOwner) return null;
          return (
            <Button
              variant="outline"
              className="text-rose-600 hover:text-rose-700"
              onClick={() => setDeleteConfirm(true)}
              data-testid="delete-lead-button"
            >
              <Trash2 className="w-4 h-4 mr-1" /> Delete Lead
            </Button>
          );
        })()}
        {(lead.current_stage === 'selected' || lead.current_stage === 'three_months' || lead.current_stage === 'move_ahead' || lead.current_stage === 'joined' || lead.current_stage === 'interview_cleared') && (
          <Button variant="outline" className="text-emerald-600" onClick={() => setConvertOpen(true)} data-testid="convert-employee-button">Convert to Employee</Button>
        )}
      </div>

      {nextGateRound && !['hold', 'rejected', 'dead', 'joined'].includes(lead.current_stage) && (
        <div className="p-3 rounded-md bg-amber-50 border border-amber-200 text-xs text-amber-800">
          ⚠ Submit the <strong>{nextGateRound.toUpperCase()} round questionnaire</strong> before moving to {STAGE_LABELS[nextStage]}.
        </div>
      )}

      {/* Resume + Medical Info */}
      <Card className="border-slate-200 shadow-none">
        <CardHeader className="pb-2"><CardTitle className="text-base font-medium">Documents & Medical</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between p-3 rounded border border-slate-100">
            <div className="flex items-center gap-2 min-w-0">
              <FileText className="w-4 h-4 text-slate-500 flex-shrink-0" />
              <div className="min-w-0">
                <p className="text-sm font-medium text-slate-900 truncate">
                  {lead.resume_filename || 'No resume uploaded'}
                </p>
                {lead.resume_uploaded_at && (
                  <p className="text-xs text-slate-500">Uploaded {new Date(lead.resume_uploaded_at).toLocaleDateString()}</p>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              {lead.resume_url && (
                <Button variant="ghost" size="sm" onClick={() => window.open(`${process.env.REACT_APP_BACKEND_URL}${lead.resume_url}`, '_blank')} data-testid="view-resume-button">
                  View
                </Button>
              )}
              <label className="cursor-pointer">
                <input type="file" className="hidden" accept=".pdf,.doc,.docx,.jpg,.jpeg,.png" onChange={handleResumeUpload} data-testid="resume-upload-input" />
                <Button asChild variant="outline" size="sm">
                  <span className="flex items-center gap-1"><Upload className="w-3 h-3" /> {lead.resume_url ? 'Replace' : 'Upload'}</span>
                </Button>
              </label>
            </div>
          </div>

          <div className="flex items-center justify-between p-3 rounded border border-slate-100">
            <div className="flex items-center gap-2 min-w-0">
              <Heart className="w-4 h-4 text-rose-500 flex-shrink-0" />
              <div className="min-w-0">
                <p className="text-sm font-medium text-slate-900">Medical Info</p>
                <p className="text-xs text-slate-500">
                  {lead.medical_info?.blood_group ? `Blood ${lead.medical_info.blood_group}` : 'Not provided'}
                  {lead.medical_info?.emergency_contact_name && ` · Emergency: ${lead.medical_info.emergency_contact_name}`}
                </p>
              </div>
            </div>
            <Button variant="outline" size="sm" onClick={openMedical} data-testid="medical-edit-button">
              {lead.medical_info ? 'Edit' : 'Add'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Stage History */}
      <Card className="border-slate-200 shadow-none">
        <CardHeader className="pb-2"><CardTitle className="text-base font-medium">Stage History</CardTitle></CardHeader>
        <CardContent>
          {history.length === 0 ? <p className="text-sm text-slate-500">No history yet</p> : (
            <div className="space-y-3">
              {history.map((log) => (
                <div key={log.id} className="flex items-start gap-3 text-sm">
                  <div className="w-2 h-2 rounded-full bg-blue-700 mt-1.5 flex-shrink-0" />
                  <div>
                    <p className="text-slate-900">
                      {log.from_stage ? `${STAGE_LABELS[log.from_stage] || log.from_stage} → ` : ''}{STAGE_LABELS[log.to_stage] || log.to_stage}
                    </p>
                    <p className="text-xs text-slate-500">{log.changed_by_name} · {new Date(log.timestamp).toLocaleString()}</p>
                    {log.form_data && Object.keys(log.form_data).length > 0 && (
                      <div className="mt-1 text-xs text-slate-400">
                        {Object.entries(log.form_data).map(([k, v]) => (
                          <span key={k} className="mr-3">{k.replace(/_/g, ' ')}: <strong>{String(v)}</strong></span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Call Logs */}
      <Card className="border-slate-200 shadow-none">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base font-medium">Call Logs</CardTitle>
            <Badge variant="outline">{calls.length} calls</Badge>
          </div>
        </CardHeader>
        <CardContent>
          {calls.length === 0 ? <p className="text-sm text-slate-500">No calls logged yet</p> : (
            <div className="space-y-2">
              {calls.map((call) => (
                <div key={call.id} className="p-2 rounded border border-slate-100 text-sm">
                  <p className="text-slate-700">{call.notes}</p>
                  <p className="text-xs text-slate-400 mt-1">{call.called_by_name} · {new Date(call.call_date).toLocaleString()}</p>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Stage Transition Dialog */}
      <Dialog open={transitionOpen} onOpenChange={setTransitionOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader><DialogTitle className="font-heading">Move to {STAGE_LABELS[targetStage]}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            {targetStage === 'qualified' && (
              <>
                <div><Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Experience (years)</Label><Input type="number" value={formData.experience || ''} onChange={(e) => setFormData({ ...formData, experience: e.target.value })} className="mt-1" data-testid="form-experience" /></div>
                <div className="flex items-center gap-2">
                  <Switch checked={formData.location_confirmation || false} onCheckedChange={(v) => setFormData({ ...formData, location_confirmation: v })} data-testid="form-location-confirmation" />
                  <Label className="text-sm">Location Confirmed</Label>
                </div>
                <div><Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Salary Expectation</Label><Input value={formData.salary_expectation || ''} onChange={(e) => setFormData({ ...formData, salary_expectation: e.target.value })} className="mt-1" data-testid="form-salary-expectation" /></div>
                <div>
                  <Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Relocation Preference</Label>
                  <Select value={formData.relocation_preference || ''} onValueChange={(v) => setFormData({ ...formData, relocation_preference: v })}>
                    <SelectTrigger className="mt-1" data-testid="form-relocation-preference"><SelectValue placeholder="Select" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="yes">Yes, willing to relocate</SelectItem>
                      <SelectItem value="no">No</SelectItem>
                      <SelectItem value="maybe">Maybe</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </>
            )}
            {(targetStage === 'hr_interview' || targetStage === 'manager_interview') && (
              <>
                <p className="text-xs text-slate-500">Schedule the {targetStage === 'hr_interview' ? 'HR' : 'Manager'} interview.</p>
                {targetStage === 'manager_interview' && (
                  <div>
                    <Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Assign Manager *</Label>
                    <Select value={formData.manager_id || ''} onValueChange={(v) => setFormData({ ...formData, manager_id: v })}>
                      <SelectTrigger className="mt-1" data-testid="form-manager-select"><SelectValue placeholder="Select manager" /></SelectTrigger>
                      <SelectContent>{managers.map(m => <SelectItem key={m.id} value={m.id}>{m.name} ({m.role})</SelectItem>)}</SelectContent>
                    </Select>
                    <p className="text-[10px] text-slate-400 mt-1">Selected manager will be notified and only they can fill the manager review.</p>
                  </div>
                )}
                <div className="grid grid-cols-2 gap-3">
                  <div><Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Date</Label><Input type="date" value={formData.interview_date || ''} onChange={(e) => setFormData({ ...formData, interview_date: e.target.value })} className="mt-1" data-testid="form-interview-date" /></div>
                  <div><Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Time</Label><Input type="time" value={formData.interview_time || ''} onChange={(e) => setFormData({ ...formData, interview_time: e.target.value })} className="mt-1" data-testid="form-interview-time" /></div>
                </div>
                <div>
                  <Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Mode</Label>
                  <Select value={formData.mode || ''} onValueChange={(v) => setFormData({ ...formData, mode: v })}>
                    <SelectTrigger className="mt-1" data-testid="form-interview-mode"><SelectValue placeholder="Select mode" /></SelectTrigger>
                    <SelectContent>{INTERVIEW_MODES.map((m) => <SelectItem key={m} value={m}>{m.replace('_', ' ')}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div><Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">City</Label><Input value={formData.interview_city || ''} onChange={(e) => setFormData({ ...formData, interview_city: e.target.value })} className="mt-1" placeholder="Bangalore" data-testid="form-interview-city" /></div>
                  <div><Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Place / Venue</Label><Input value={formData.interview_place || ''} onChange={(e) => setFormData({ ...formData, interview_place: e.target.value })} className="mt-1" placeholder="Office / Zoom link" data-testid="form-interview-place" /></div>
                </div>
              </>
            )}
            {targetStage === 'selected' && (
              <p className="text-sm text-slate-600">Confirm final recommendation. Prior interview round must be completed.</p>
            )}
            {targetStage === 'three_months' && (
              <p className="text-sm text-indigo-700">Moving to <strong>3-Month tracking</strong>. An offer letter will be sent via WhatsApp and saved in the database. After 90 days, a notification will be generated to convert to Joined.</p>
            )}
            {targetStage === 'joined' && (
              <div><Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Joining Date (optional)</Label><Input type="date" value={formData.joining_date || ''} onChange={(e) => setFormData({ ...formData, joining_date: e.target.value })} className="mt-1" data-testid="form-joining-date" /></div>
            )}
            {targetStage === 'hold' && (
              <>
                <div>
                  <Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Hold Reason</Label>
                  <Select value={formData.hold_reason || ''} onValueChange={(v) => setFormData({ ...formData, hold_reason: v })}>
                    <SelectTrigger className="mt-1" data-testid="form-hold-reason"><SelectValue placeholder="Select reason" /></SelectTrigger>
                    <SelectContent>{HOLD_REASONS.map((r) => <SelectItem key={r} value={r}>{r.replace(/_/g, ' ')}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
                <p className="text-xs text-slate-400">Lead can be resumed to its prior stage later.</p>
              </>
            )}
            {targetStage === 'rejected' && (
              <>
                <div>
                  <Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Reason</Label>
                  <Select value={formData.rejection_reason || ''} onValueChange={(v) => setFormData({ ...formData, rejection_reason: v })}>
                    <SelectTrigger className="mt-1" data-testid="form-rejection-reason"><SelectValue placeholder="Select reason" /></SelectTrigger>
                    <SelectContent>{REJECTION_REASONS.map((r) => <SelectItem key={r} value={r}>{r.replace(/_/g, ' ')}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
                <p className="text-xs text-rose-600">Feedback form will be auto-sent via WhatsApp.</p>
              </>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setTransitionOpen(false)}>Cancel</Button>
            <Button onClick={handleTransition} className="bg-blue-700 hover:bg-blue-800" data-testid="confirm-transition-button">Confirm Move</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Call Log Dialog */}
      <Dialog open={callDialogOpen} onOpenChange={setCallDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader><DialogTitle className="font-heading">Log Call</DialogTitle></DialogHeader>
          <Textarea value={callNote} onChange={(e) => setCallNote(e.target.value)} placeholder="Call notes..." rows={4} data-testid="call-notes-input" />
          <DialogFooter>
            <Button variant="outline" onClick={() => setCallDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleAddCall} className="bg-blue-700 hover:bg-blue-800" data-testid="save-call-button">Save Call</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Convert to Employee Dialog */}
      <Dialog open={convertOpen} onOpenChange={setConvertOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader><DialogTitle className="font-heading">Convert to Employee</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div><Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Joining Date</Label><Input type="date" value={convertForm.joining_date} onChange={(e) => setConvertForm({ ...convertForm, joining_date: e.target.value })} className="mt-1" /></div>
            <div><Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Role / Designation</Label><Input value={convertForm.role} onChange={(e) => setConvertForm({ ...convertForm, role: e.target.value })} className="mt-1" /></div>
            <div><Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Department</Label><Input value={convertForm.department} onChange={(e) => setConvertForm({ ...convertForm, department: e.target.value })} className="mt-1" /></div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Category</Label>
                <Select value={convertForm.category} onValueChange={(v) => setConvertForm({ ...convertForm, category: v })}>
                  <SelectTrigger className="mt-1"><SelectValue placeholder="Auto" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="branch">Branch</SelectItem>
                    <SelectItem value="head_office">Head Office</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Type</Label>
                <Select value={convertForm.employment_type} onValueChange={(v) => setConvertForm({ ...convertForm, employment_type: v })}>
                  <SelectTrigger className="mt-1"><SelectValue placeholder="Auto" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="technician">Technician</SelectItem>
                    <SelectItem value="mid_level">Mid-Level</SelectItem>
                    <SelectItem value="management">Management</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConvertOpen(false)}>Cancel</Button>
            <Button onClick={handleConvert} disabled={converting} className="bg-emerald-600 hover:bg-emerald-700" data-testid="confirm-convert-button">
              {converting ? 'Converting...' : 'Convert'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Interview Questionnaire Dialog */}
      <InterviewFormDialog
        open={interviewDialog.open}
        onOpenChange={(o) => setInterviewDialog({ ...interviewDialog, open: o })}
        leadId={id}
        round={interviewDialog.round}
        onSubmitted={fetchData}
      />

      {/* Medical Info Dialog */}
      <Dialog open={medicalOpen} onOpenChange={setMedicalOpen}>
        <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto" data-testid="medical-dialog">
          <DialogHeader><DialogTitle className="font-heading">Medical Information</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Blood Group</Label>
                <Select value={medicalForm.blood_group || ''} onValueChange={(v) => setMedicalForm({ ...medicalForm, blood_group: v })}>
                  <SelectTrigger className="mt-1" data-testid="medical-blood-group"><SelectValue placeholder="Select" /></SelectTrigger>
                  <SelectContent>
                    {['A+','A-','B+','B-','AB+','AB-','O+','O-'].map(bg => <SelectItem key={bg} value={bg}>{bg}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Emergency Phone</Label>
                <Input value={medicalForm.emergency_contact_phone || ''} onChange={(e) => setMedicalForm({ ...medicalForm, emergency_contact_phone: e.target.value })} className="mt-1" data-testid="medical-emergency-phone" />
              </div>
            </div>
            <div>
              <Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Emergency Contact Name</Label>
              <Input value={medicalForm.emergency_contact_name || ''} onChange={(e) => setMedicalForm({ ...medicalForm, emergency_contact_name: e.target.value })} className="mt-1" data-testid="medical-emergency-name" />
            </div>
            <div>
              <Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Allergies</Label>
              <Textarea value={medicalForm.allergies || ''} onChange={(e) => setMedicalForm({ ...medicalForm, allergies: e.target.value })} rows={2} className="mt-1" data-testid="medical-allergies" />
            </div>
            <div>
              <Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Chronic Conditions</Label>
              <Textarea value={medicalForm.chronic_conditions || ''} onChange={(e) => setMedicalForm({ ...medicalForm, chronic_conditions: e.target.value })} rows={2} className="mt-1" />
            </div>
            <div>
              <Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Notes</Label>
              <Textarea value={medicalForm.medical_notes || ''} onChange={(e) => setMedicalForm({ ...medicalForm, medical_notes: e.target.value })} rows={2} className="mt-1" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setMedicalOpen(false)}>Cancel</Button>
            <Button onClick={handleSaveMedical} className="bg-blue-700 hover:bg-blue-800" data-testid="save-medical-button">Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Assign/Change Role Dialog */}
      <Dialog open={roleDialogOpen} onOpenChange={setRoleDialogOpen}>
        <DialogContent className="max-w-md" data-testid="lead-role-dialog">
          <DialogHeader>
            <DialogTitle className="font-heading">{lead?.job_role ? 'Change Role' : 'Assign Role'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <p className="text-sm text-slate-600">
              Pick the job opening to link this candidate to. The designation will reflect on the lead card and across the dashboard.
            </p>
            <div>
              <Label className="text-xs text-slate-500">Job Opening ({lead?.is_technician ? 'Franchise' : 'Head Office'})</Label>
              <select
                className="mt-1 w-full border border-slate-200 rounded-md px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={selectedJobId}
                onChange={(e) => setSelectedJobId(e.target.value)}
                data-testid="lead-role-job-select"
              >
                <option value="">— No role / Unassign —</option>
                {jobs.map(j => (
                  <option key={j.id} value={j.id}>
                    {j.role}{j.location_city ? ` · ${j.location_city}` : ''}{j.status !== 'open' ? ` (${j.status})` : ''}
                  </option>
                ))}
              </select>
              {jobs.length === 0 && (
                <p className="text-xs text-slate-400 italic mt-1.5">No jobs available for this segment</p>
              )}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRoleDialogOpen(false)} data-testid="lead-role-cancel">Cancel</Button>
            <Button
              className="bg-blue-700 hover:bg-blue-800"
              onClick={saveRole}
              disabled={savingRole}
              data-testid="lead-role-save"
            >
              {savingRole ? 'Saving…' : 'Save'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Lead Confirmation */}
      <Dialog open={deleteConfirm} onOpenChange={setDeleteConfirm}>
        <DialogContent className="max-w-md" data-testid="delete-lead-dialog">
          <DialogHeader><DialogTitle className="font-heading text-rose-600">Delete Lead?</DialogTitle></DialogHeader>
          <p className="text-sm text-slate-600">
            Are you sure you want to delete <strong>{lead?.name}</strong>?
            This will move the lead to <strong>Deleted Leads</strong>. A CEO can restore it later.
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteConfirm(false)} data-testid="cancel-delete-button">Cancel</Button>
            <Button
              className="bg-rose-600 hover:bg-rose-700"
              data-testid="confirm-delete-button"
              onClick={async () => {
                try {
                  await API.post(`/leads/${id}/delete`);
                  toast.success('Lead deleted');
                  setDeleteConfirm(false);
                  navigate(lead.is_technician ? '/leads/franchise' : '/leads/head-office');
                } catch (err) {
                  toast.error(err.response?.data?.detail || 'Failed to delete');
                }
              }}
            >Delete</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Send Candidate Form Dialog */}
      <Dialog open={sendFormOpen} onOpenChange={(v) => { setSendFormOpen(v); if (!v) setSendFormResult(null); }}>
        <DialogContent className="max-w-md" data-testid="send-form-dialog">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2">
              <Send className="w-4 h-4" /> Send Candidate Information Form
            </DialogTitle>
          </DialogHeader>
          {!sendFormResult ? (
            <>
              <p className="text-sm text-slate-600">
                We'll generate a secure form link and try to send it to <strong>{lead?.phone}</strong> via WhatsApp.
                If WhatsApp isn't configured, you'll get a copy-paste link.
              </p>
              {formStatus.status === 'sent' && formStatus.pending_public_url && (
                <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded p-2">
                  A form was already sent. Sending again will reuse the existing link.
                </p>
              )}
              <DialogFooter>
                <Button variant="outline" onClick={() => setSendFormOpen(false)}>Cancel</Button>
                <Button
                  disabled={sendingForm}
                  className="bg-blue-700 hover:bg-blue-800"
                  data-testid="confirm-send-form-button"
                  onClick={async () => {
                    setSendingForm(true);
                    try {
                      const res = await API.post(`/candidate-forms/${id}/send`);
                      setSendFormResult(res.data);
                      toast.success(res.data.whatsapp?.dispatched ? 'WhatsApp sent!' : 'Link generated — share manually');
                      fetchData();
                    } catch (err) {
                      toast.error(err.response?.data?.detail || 'Failed to send');
                    } finally { setSendingForm(false); }
                  }}
                >{sendingForm ? 'Sending...' : 'Send Form'}</Button>
              </DialogFooter>
            </>
          ) : (
            <>
              <div className="space-y-2">
                {sendFormResult.whatsapp?.dispatched ? (
                  <div className="p-2 bg-emerald-50 border border-emerald-200 rounded text-sm text-emerald-800">
                    ✓ WhatsApp message dispatched to {sendFormResult.candidate_phone}.
                  </div>
                ) : (
                  <div className="p-2 bg-amber-50 border border-amber-200 rounded text-xs text-amber-800">
                    WhatsApp not configured. Share this link with the candidate manually.
                  </div>
                )}
                <Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Form Link</Label>
                <Input value={sendFormResult.public_url} readOnly className="font-mono text-xs" data-testid="form-link-input" />
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" className="flex-1" data-testid="copy-link-button" onClick={() => { navigator.clipboard.writeText(sendFormResult.public_url); toast.success('Link copied'); }}>
                    <Copy className="w-3 h-3 mr-1" /> Copy
                  </Button>
                  <Button size="sm" variant="outline" className="flex-1" data-testid="open-whatsapp-button" onClick={() => {
                    const phone = (sendFormResult.candidate_phone || '').replace(/\D/g, '');
                    const text = encodeURIComponent(`Hi ${sendFormResult.candidate_name || 'Candidate'}, please fill out our information form: ${sendFormResult.public_url}`);
                    window.open(`https://wa.me/${phone}?text=${text}`, '_blank');
                  }}>
                    <ExternalLink className="w-3 h-3 mr-1" /> WhatsApp Web
                  </Button>
                </div>
              </div>
              <DialogFooter>
                <Button onClick={() => { setSendFormOpen(false); setSendFormResult(null); }}>Done</Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
