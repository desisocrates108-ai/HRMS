import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import API from '@/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import { Plus, Phone, ChevronRight, Search, Building, Wrench, Eye, Trash2, Send } from 'lucide-react';
import { toast } from 'sonner';

const HO_STAGES = [
  { value: 'new_lead', label: 'New', color: 'bg-blue-700' },
  { value: 'qualified', label: 'Qualified', color: 'bg-emerald-600' },
  { value: 'hr_interview', label: 'HR', color: 'bg-amber-600' },
  { value: 'manager_interview', label: 'Manager', color: 'bg-violet-600' },
  { value: 'selected', label: 'Selected', color: 'bg-teal-600' },
  { value: 'three_months', label: '3 Months', color: 'bg-indigo-600' },
  { value: 'joined', label: 'Joined', color: 'bg-green-700' },
  { value: 'hold', label: 'Hold', color: 'bg-orange-500' },
  { value: 'rejected', label: 'Rejected', color: 'bg-rose-600' },
];

const TECH_STAGES = [
  { value: 'new_lead', label: 'New', color: 'bg-blue-700' },
  { value: 'qualified', label: 'Qualified', color: 'bg-emerald-600' },
  { value: 'hr_interview', label: 'HR', color: 'bg-amber-600' },
  { value: 'selected', label: 'Selected', color: 'bg-teal-600' },
  { value: 'three_months', label: '3 Months', color: 'bg-indigo-600' },
  { value: 'joined', label: 'Joined', color: 'bg-green-700' },
  { value: 'hold', label: 'Hold', color: 'bg-orange-500' },
  { value: 'rejected', label: 'Rejected', color: 'bg-rose-600' },
];

const SOURCE_OPTIONS = ['manual', 'job_portal', 'meta_ads'];

export default function LeadsPipelinePage({ pipelineMode }) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const stageParam = searchParams.get('stage');
  const sourceParam = searchParams.get('source');
  const isTechnicianMode = pipelineMode === 'technician';
  const stages = isTechnicianMode ? TECH_STAGES : HO_STAGES;

  const [leads, setLeads] = useState([]);
  const [users, setUsers] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeStage, setActiveStage] = useState(stageParam || 'new_lead');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [sourceFilter, setSourceFilter] = useState(sourceParam || 'all');
  const [assigneeFilter, setAssigneeFilter] = useState('all');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [holdDialog, setHoldDialog] = useState({ open: false, lead: null, reason: '' });
  const [deleteDialog, setDeleteDialog] = useState({ open: false, lead: null });
  const [form, setForm] = useState({
    name: '', phone: '', email: '', location_city: '', location_area: '',
    source: 'manual', assigned_to: '', is_technician: isTechnicianMode, job_id: '',
  });

  useEffect(() => { fetchData(); }, [pipelineMode]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [leadsRes, usersRes, jobsRes] = await Promise.all([
        API.get('/leads', { params: { is_technician: isTechnicianMode } }),
        API.get('/users'),
        API.get('/jobs'),
      ]);
      setLeads(leadsRes.data);
      setUsers(usersRes.data);
      setJobs(jobsRes.data);
    } catch { toast.error('Failed to load data'); }
    finally { setLoading(false); }
  };

  const handleCreate = async () => {
    try {
      const payload = { ...form, is_technician: isTechnicianMode };
      if (!payload.email) payload.email = null;
      if (!payload.assigned_to) payload.assigned_to = null;
      if (!payload.job_id) payload.job_id = null;
      if (!payload.location_city) payload.location_city = null;
      if (!payload.location_area) payload.location_area = null;
      await API.post('/leads', payload);
      toast.success('Lead created');
      setDialogOpen(false);
      setForm({ name: '', phone: '', email: '', location_city: '', location_area: '', source: 'manual', assigned_to: '', is_technician: isTechnicianMode, job_id: '' });
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create lead');
    }
  };

  const submitHold = async () => {
    const reason = holdDialog.reason.trim();
    if (!reason) { toast.error('Hold reason is required'); return; }
    try {
      await API.post(`/leads/${holdDialog.lead.id}/transition`, {
        to_stage: 'hold',
        form_data: { hold_reason: reason },
      });
      toast.success('Lead moved to Hold');
      setHoldDialog({ open: false, lead: null, reason: '' });
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update');
    }
  };

  const filteredLeads = leads.filter((l) => {
    const matchStage = l.current_stage === activeStage;
    const matchSearch = !searchQuery || l.name?.toLowerCase().includes(searchQuery.toLowerCase()) || l.phone?.includes(searchQuery);
    const matchSource = sourceFilter === 'all' || l.source === sourceFilter;
    const matchAssignee = assigneeFilter === 'all' || l.assigned_to === assigneeFilter;
    const created = l.created_at || '';
    const matchFrom = !dateFrom || created >= dateFrom;
    const matchTo = !dateTo || created <= dateTo + 'T23:59:59';
    return matchStage && matchSearch && matchSource && matchAssignee && matchFrom && matchTo;
  });

  const stageCounts = {};
  stages.forEach((s) => {
    stageCounts[s.value] = leads.filter((l) => {
      const matchSrc = sourceFilter === 'all' || l.source === sourceFilter;
      const matchAss = assigneeFilter === 'all' || l.assigned_to === assigneeFilter;
      return l.current_stage === s.value && matchSrc && matchAss;
    }).length;
  });

  if (loading) return <div className="flex items-center justify-center h-64 text-slate-500">Loading...</div>;

  const PageIcon = isTechnicianMode ? Wrench : Building;
  const pageTitle = isTechnicianMode ? 'Franchise Leads' : 'Head Office Leads';

  return (
    <div className="space-y-4" data-testid={`leads-page-${isTechnicianMode ? 'franchise' : 'ho'}`}>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl md:text-2xl font-heading font-semibold text-slate-900 flex items-center gap-2">
            <PageIcon className="w-5 h-5" /> {pageTitle}
          </h1>
          <p className="text-sm text-slate-500">{leads.length} total · {filteredLeads.length} in {stages.find(s => s.value === activeStage)?.label}</p>
        </div>
        <Button onClick={() => setDialogOpen(true)} className="bg-blue-700 hover:bg-blue-800 active:scale-[0.98]" data-testid="create-lead-button">
          <Plus className="w-4 h-4 mr-1" /> Add Lead
        </Button>
      </div>

      <Card className="border-slate-200 shadow-none">
        <CardContent className="p-3 space-y-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <Input
              placeholder="Search by name or phone..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 h-10"
              data-testid="lead-search-input"
            />
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            <Select value={sourceFilter} onValueChange={setSourceFilter}>
              <SelectTrigger className="h-9" data-testid="source-filter"><SelectValue placeholder="All sources" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All sources</SelectItem>
                {SOURCE_OPTIONS.map(s => <SelectItem key={s} value={s}>{s.replace('_',' ')}</SelectItem>)}
              </SelectContent>
            </Select>
            <Select value={assigneeFilter} onValueChange={setAssigneeFilter}>
              <SelectTrigger className="h-9" data-testid="assignee-filter"><SelectValue placeholder="All users" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All users</SelectItem>
                {users.map(u => <SelectItem key={u.id} value={u.id}>{u.name}</SelectItem>)}
              </SelectContent>
            </Select>
            <Input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="h-9" data-testid="date-from-filter" />
            <Input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="h-9" data-testid="date-to-filter" />
          </div>
        </CardContent>
      </Card>

      <Tabs value={activeStage} onValueChange={setActiveStage}>
        <TabsList className={`w-full grid h-auto p-1 ${isTechnicianMode ? 'grid-cols-4 md:grid-cols-8' : 'grid-cols-3 md:grid-cols-9'}`}>
          {stages.map((s) => (
            <TabsTrigger key={s.value} value={s.value} className="text-xs md:text-sm px-1 py-2" data-testid={`stage-tab-${s.value}`}>
              <span className="truncate">{s.label}</span>
              <Badge variant="secondary" className="ml-1 text-xs px-1.5 py-0">{stageCounts[s.value]}</Badge>
            </TabsTrigger>
          ))}
        </TabsList>

        {stages.map((s) => (
          <TabsContent key={s.value} value={s.value} className="mt-3">
            {filteredLeads.length === 0 ? (
              <div className="text-center py-8 text-slate-500 text-sm">No leads in this stage</div>
            ) : (
              <div className="space-y-2">
                {filteredLeads.map((lead) => (
                  <Card
                    key={lead.id}
                    className="border-slate-200 shadow-none hover:-translate-y-0.5 hover:shadow-md hover:border-slate-300 transition-all duration-200"
                    data-testid={`lead-card-${lead.id}`}
                  >
                    <CardContent className="p-3 md:p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3 min-w-0 cursor-pointer" onClick={() => navigate(`/leads/${lead.id}`)}>
                          <div className={`w-2 h-8 rounded-full ${s.color} flex-shrink-0`} />
                          <div className="min-w-0">
                            <p className="font-medium text-slate-900 truncate">{lead.name}</p>
                            <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                              <span className="text-xs text-slate-500 flex items-center gap-1"><Phone className="w-3 h-3" />{lead.phone}</span>
                              {lead.is_technician && <Badge variant="outline" className="text-xs px-1.5 py-0 text-blue-700 border-blue-200">Franchise</Badge>}
                              {lead.candidate_form_status === 'completed' && (
                                <Badge variant="outline" className="text-[10px] px-1.5 py-0 text-emerald-700 border-emerald-200" data-testid={`form-completed-${lead.id}`}>Form ✓</Badge>
                              )}
                              {lead.candidate_form_status === 'sent' && (
                                <Badge variant="outline" className="text-[10px] px-1.5 py-0 text-amber-700 border-amber-200" data-testid={`form-sent-${lead.id}`}>Form Sent</Badge>
                              )}
                              {lead.hold_reason && s.value === 'hold' && (
                                <Badge variant="outline" className="text-xs px-1.5 py-0 text-orange-700 border-orange-200">Hold: {lead.hold_reason.slice(0, 30)}</Badge>
                              )}
                              {lead.assigned_manager_name && s.value === 'manager_interview' && (
                                <Badge variant="outline" className="text-xs px-1.5 py-0 text-violet-700 border-violet-200">Mgr: {lead.assigned_manager_name}</Badge>
                              )}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2 flex-shrink-0">
                          <Badge variant="secondary" className="text-xs">{lead.source}</Badge>
                          {s.value !== 'hold' && s.value !== 'rejected' && s.value !== 'joined' && (
                            <button
                              onClick={(e) => { e.stopPropagation(); setHoldDialog({ open: true, lead, reason: '' }); }}
                              className="text-orange-500 hover:text-orange-700 text-xs px-2 py-1 border border-orange-200 rounded transition-colors"
                              title="Move to Hold"
                              data-testid={`hold-lead-${lead.id}`}
                            >
                              Hold
                            </button>
                          )}
                          <button
                            onClick={(e) => { e.stopPropagation(); setDeleteDialog({ open: true, lead }); }}
                            className="text-rose-500 hover:text-rose-700"
                            title="Delete lead"
                            data-testid={`delete-lead-${lead.id}`}
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                          <button
                            onClick={(e) => { e.stopPropagation(); navigate(`/leads/${lead.id}`); }}
                            className="text-slate-400 hover:text-blue-700 transition-colors"
                            title="View details"
                            data-testid={`view-lead-${lead.id}`}
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          <ChevronRight className="w-4 h-4 text-slate-400" />
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>
        ))}
      </Tabs>

      {/* Hold Reason Dialog */}
      <Dialog open={holdDialog.open} onOpenChange={(v) => !v && setHoldDialog({ open: false, lead: null, reason: '' })}>
        <DialogContent className="max-w-md">
          <DialogHeader><DialogTitle className="font-heading">Move to Hold</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <p className="text-sm text-slate-600">
              Provide a reason for moving <strong>{holdDialog.lead?.name}</strong> to Hold. This is required and will be visible in lead history.
            </p>
            <Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Hold Reason *</Label>
            <Textarea
              value={holdDialog.reason}
              onChange={(e) => setHoldDialog({ ...holdDialog, reason: e.target.value })}
              placeholder="e.g., Awaiting documents, candidate requested time, salary discussion pending..."
              rows={4}
              data-testid="hold-reason-textarea"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setHoldDialog({ open: false, lead: null, reason: '' })} data-testid="cancel-hold-button">Cancel</Button>
            <Button onClick={submitHold} className="bg-orange-500 hover:bg-orange-600" data-testid="submit-hold-button">Move to Hold</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Create Lead Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle className="font-heading">Add New {pageTitle.replace(' Leads', '')} Lead</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div><Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Name</Label><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Full name" className="mt-1" data-testid="lead-name-input" /></div>
            <div><Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Phone</Label><Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="Phone number" className="mt-1" data-testid="lead-phone-input" /></div>
            <div><Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Email</Label><Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="Optional" className="mt-1" /></div>
            <div className="grid grid-cols-2 gap-3">
              <div><Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">City</Label><Input value={form.location_city} onChange={(e) => setForm({ ...form, location_city: e.target.value })} className="mt-1" /></div>
              <div><Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Area</Label><Input value={form.location_area} onChange={(e) => setForm({ ...form, location_area: e.target.value })} className="mt-1" /></div>
            </div>
            <div>
              <Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Source</Label>
              <Select value={form.source} onValueChange={(v) => setForm({ ...form, source: v })}>
                <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                <SelectContent>{SOURCE_OPTIONS.map((s) => <SelectItem key={s} value={s}>{s.replace('_', ' ')}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Assign To</Label>
              <Select value={form.assigned_to} onValueChange={(v) => setForm({ ...form, assigned_to: v })}>
                <SelectTrigger className="mt-1"><SelectValue placeholder="Select user" /></SelectTrigger>
                <SelectContent>{users.map((u) => <SelectItem key={u.id} value={u.id}>{u.name} ({u.role})</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Job</Label>
              <Select value={form.job_id} onValueChange={(v) => setForm({ ...form, job_id: v })}>
                <SelectTrigger className="mt-1"><SelectValue placeholder="Link to job (optional)" /></SelectTrigger>
                <SelectContent>{jobs.map((j) => <SelectItem key={j.id} value={j.id}>{j.role} - {j.location}</SelectItem>)}</SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleCreate} className="bg-blue-700 hover:bg-blue-800" data-testid="save-lead-button">Add Lead</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Lead Confirmation */}
      <Dialog open={deleteDialog.open} onOpenChange={(v) => !v && setDeleteDialog({ open: false, lead: null })}>
        <DialogContent className="max-w-md" data-testid="delete-lead-dialog">
          <DialogHeader>
            <DialogTitle className="font-heading text-rose-600">Delete Lead?</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-slate-600">
            Are you sure you want to delete <strong>{deleteDialog.lead?.name}</strong>?
            This will move it to <strong>Deleted Leads</strong>. A CEO/HR can restore it later.
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialog({ open: false, lead: null })} data-testid="cancel-delete-lead-button">Cancel</Button>
            <Button
              className="bg-rose-600 hover:bg-rose-700"
              data-testid="confirm-delete-lead-button"
              onClick={async () => {
                try {
                  await API.post(`/leads/${deleteDialog.lead.id}/delete`);
                  toast.success('Lead deleted');
                  setDeleteDialog({ open: false, lead: null });
                  fetchData();
                } catch (err) {
                  toast.error(err.response?.data?.detail || 'Failed to delete');
                }
              }}
            >Delete</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
