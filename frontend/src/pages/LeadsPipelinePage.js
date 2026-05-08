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
import { Plus, Phone, ChevronRight, Search, Building2, Wrench, Eye } from 'lucide-react';
import { toast } from 'sonner';

const HO_STAGES = [
  { value: 'new_lead', label: 'New', color: 'bg-blue-700' },
  { value: 'qualified', label: 'Qualified', color: 'bg-emerald-600' },
  { value: 'hr_interview', label: 'HR', color: 'bg-amber-600' },
  { value: 'manager_interview', label: 'Manager', color: 'bg-violet-600' },
  { value: 'selected', label: 'Selected', color: 'bg-teal-600' },
  { value: 'joined', label: 'Joined', color: 'bg-green-700' },
  { value: 'hold', label: 'Hold', color: 'bg-orange-500' },
  { value: 'rejected', label: 'Rejected', color: 'bg-rose-600' },
];

const TECH_STAGES = [
  { value: 'new_lead', label: 'New', color: 'bg-blue-700' },
  { value: 'qualified', label: 'Qualified', color: 'bg-emerald-600' },
  { value: 'hr_interview', label: 'HR', color: 'bg-amber-600' },
  { value: 'selected', label: 'Selected', color: 'bg-teal-600' },
  { value: 'joined', label: 'Joined', color: 'bg-green-700' },
  { value: 'hold', label: 'Hold', color: 'bg-orange-500' },
  { value: 'rejected', label: 'Rejected', color: 'bg-rose-600' },
];

const SOURCE_OPTIONS = ['manual', 'job_portal', 'meta_ads'];

export default function LeadsPipelinePage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const stageParam = searchParams.get('stage');
  const isTechParam = searchParams.get('is_technician');
  const sourceParam = searchParams.get('source');
  const [leads, setLeads] = useState([]);
  const [users, setUsers] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [pipelineType, setPipelineType] = useState(isTechParam === 'true' ? 'technician' : 'head_office'); // 'head_office' | 'technician'
  const [activeStage, setActiveStage] = useState(stageParam || 'new_lead');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [form, setForm] = useState({
    name: '', phone: '', email: '', location_city: '', location_area: '',
    source: 'manual', assigned_to: '', is_technician: false, job_id: '',
  });

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const [leadsRes, usersRes, jobsRes] = await Promise.all([
        API.get('/leads'), API.get('/users'), API.get('/jobs'),
      ]);
      setLeads(leadsRes.data);
      setUsers(usersRes.data);
      setJobs(jobsRes.data);
    } catch { toast.error('Failed to load data'); }
    finally { setLoading(false); }
  };

  const handleCreate = async () => {
    try {
      const payload = { ...form };
      if (!payload.email) payload.email = null;
      if (!payload.assigned_to) payload.assigned_to = null;
      if (!payload.job_id) payload.job_id = null;
      if (!payload.location_city) payload.location_city = null;
      if (!payload.location_area) payload.location_area = null;
      await API.post('/leads', payload);
      toast.success('Lead created');
      setDialogOpen(false);
      setForm({ name: '', phone: '', email: '', location_city: '', location_area: '', source: 'manual', assigned_to: '', is_technician: false, job_id: '' });
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create lead');
    }
  };

  const stages = pipelineType === 'technician' ? TECH_STAGES : HO_STAGES;
  const pipelineLeads = leads.filter((l) =>
    pipelineType === 'technician' ? l.is_technician : !l.is_technician
  );

  const filteredLeads = pipelineLeads.filter((l) => {
    const matchStage = l.current_stage === activeStage;
    const matchSearch = !searchQuery || l.name?.toLowerCase().includes(searchQuery.toLowerCase()) || l.phone?.includes(searchQuery);
    const matchSource = !sourceParam || l.source === sourceParam;
    return matchStage && matchSearch && matchSource;
  });

  const stageCounts = {};
  stages.forEach((s) => {
    stageCounts[s.value] = pipelineLeads.filter((l) => l.current_stage === s.value).length;
  });

  if (loading) return <div className="flex items-center justify-center h-64 text-slate-500">Loading...</div>;

  return (
    <div className="space-y-4" data-testid="leads-pipeline-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl md:text-2xl font-heading font-semibold text-slate-900">Leads Pipeline</h1>
          <p className="text-sm text-slate-500">
            {pipelineLeads.length} {pipelineType === 'technician' ? 'technician' : 'head-office'} leads
            {sourceParam && <span className="ml-1">· Source: <strong>{sourceParam.replace('_', ' ')}</strong></span>}
          </p>
        </div>
        <Button onClick={() => setDialogOpen(true)} className="bg-blue-700 hover:bg-blue-800 active:scale-[0.98]" data-testid="create-lead-button">
          <Plus className="w-4 h-4 mr-1" /> Add Lead
        </Button>
      </div>

      {/* Pipeline type switcher */}
      <div className="flex gap-2">
        <button
          onClick={() => { setPipelineType('head_office'); setActiveStage('new_lead'); }}
          className={`flex-1 md:flex-none px-4 py-2 rounded-md text-sm font-medium border transition-all flex items-center justify-center gap-2 ${
            pipelineType === 'head_office'
              ? 'bg-blue-700 text-white border-blue-700 shadow-sm'
              : 'bg-white text-slate-700 border-slate-200 hover:border-slate-300'
          }`}
          data-testid="pipeline-ho-button"
        >
          <Building2 className="w-4 h-4" /> Head Office
        </button>
        <button
          onClick={() => { setPipelineType('technician'); setActiveStage('new_lead'); }}
          className={`flex-1 md:flex-none px-4 py-2 rounded-md text-sm font-medium border transition-all flex items-center justify-center gap-2 ${
            pipelineType === 'technician'
              ? 'bg-blue-700 text-white border-blue-700 shadow-sm'
              : 'bg-white text-slate-700 border-slate-200 hover:border-slate-300'
          }`}
          data-testid="pipeline-tech-button"
        >
          <Wrench className="w-4 h-4" /> Technician / Branch
        </button>
      </div>

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

      <Tabs value={activeStage} onValueChange={setActiveStage}>
        <TabsList className={`w-full grid h-auto p-1 ${pipelineType === 'technician' ? 'grid-cols-4 md:grid-cols-7' : 'grid-cols-4 md:grid-cols-8'}`}>
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
                    className="border-slate-200 shadow-none cursor-pointer hover:-translate-y-0.5 hover:shadow-md hover:border-slate-300 transition-all duration-200"
                    onClick={() => navigate(`/leads/${lead.id}`)}
                    data-testid={`lead-card-${lead.id}`}
                  >
                    <CardContent className="p-3 md:p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3 min-w-0">
                          <div className={`w-2 h-8 rounded-full ${s.color} flex-shrink-0`} />
                          <div className="min-w-0">
                            <p className="font-medium text-slate-900 truncate">{lead.name}</p>
                            <div className="flex items-center gap-2 mt-0.5">
                              <span className="text-xs text-slate-500 flex items-center gap-1"><Phone className="w-3 h-3" />{lead.phone}</span>
                              {lead.is_technician && <Badge variant="outline" className="text-xs px-1.5 py-0 text-blue-700 border-blue-200">Tech</Badge>}
                              {lead.hold_reason && s.value === 'hold' && (
                                <Badge variant="outline" className="text-xs px-1.5 py-0 text-orange-700 border-orange-200">{lead.hold_reason.slice(0, 20)}</Badge>
                              )}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2 flex-shrink-0">
                          <Badge variant="secondary" className="text-xs">{lead.source}</Badge>
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

      {/* Create Lead Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle className="font-heading">Add New Lead</DialogTitle></DialogHeader>
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
            <div className="flex items-center gap-2">
              <Switch checked={form.is_technician} onCheckedChange={(v) => setForm({ ...form, is_technician: v })} data-testid="is-technician-switch" />
              <Label className="text-sm text-slate-700">Is Technician (Branch pipeline)</Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleCreate} className="bg-blue-700 hover:bg-blue-800" data-testid="save-lead-button">Add Lead</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
