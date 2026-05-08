import { useState, useEffect } from 'react';
import API from '@/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Briefcase, Plus, MapPin, DollarSign } from 'lucide-react';
import { toast } from 'sonner';

const JOB_ROLES = ['Technician', 'Service Advisor', 'Branch Manager', 'HR Executive', 'Marketing Coordinator', 'Graphic Designer', 'Franchise Executive', 'Operations Manager', 'Sales Manager'];
const STATUS_COLORS = { open: 'text-emerald-600 border-emerald-200', closed: 'text-slate-500 border-slate-300', on_hold: 'text-amber-600 border-amber-200' };

export default function JobsPage() {
  const [jobs, setJobs] = useState([]);
  const [branches, setBranches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState({ role: '', type: 'branch', branch_id: '', location: '', salary_range_min: '', salary_range_max: '', description: '', deadline: '' });

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const [jobsRes, branchesRes] = await Promise.all([API.get('/jobs'), API.get('/branches')]);
      setJobs(jobsRes.data);
      setBranches(branchesRes.data);
    } catch { toast.error('Failed to load data'); }
    finally { setLoading(false); }
  };

  const handleCreate = async () => {
    try {
      const payload = { ...form };
      payload.salary_range_min = payload.salary_range_min ? parseFloat(payload.salary_range_min) : null;
      payload.salary_range_max = payload.salary_range_max ? parseFloat(payload.salary_range_max) : null;
      if (payload.type === 'HO') payload.branch_id = null;
      if (!payload.branch_id) payload.branch_id = null;
      if (!payload.description) payload.description = null;
      if (!payload.deadline) payload.deadline = null;
      await API.post('/jobs', payload);
      toast.success('Job created! Auto tasks generated.');
      setDialogOpen(false);
      setForm({ role: '', type: 'branch', branch_id: '', location: '', salary_range_min: '', salary_range_max: '', description: '', deadline: '' });
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create job');
    }
  };

  if (loading) return <div className="flex items-center justify-center h-64 text-slate-500">Loading...</div>;

  return (
    <div className="space-y-4" data-testid="jobs-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl md:text-2xl font-heading font-semibold text-slate-900">Jobs</h1>
          <p className="text-sm text-slate-500">{jobs.length} openings</p>
        </div>
        <Button onClick={() => setDialogOpen(true)} className="bg-blue-700 hover:bg-blue-800 active:scale-[0.98]" data-testid="create-job-button">
          <Plus className="w-4 h-4 mr-1" /> Create Job
        </Button>
      </div>

      {jobs.length === 0 ? (
        <div className="text-center py-12 text-slate-500">No jobs yet. Create your first job opening.</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {jobs.map((job) => (
            <Card key={job.id} className="border-slate-200 shadow-none hover:-translate-y-0.5 hover:shadow-md transition-all duration-200">
              <CardContent className="p-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center flex-shrink-0">
                      <Briefcase className="w-5 h-5 text-blue-700" />
                    </div>
                    <div>
                      <p className="font-medium text-slate-900">{job.role}</p>
                      <div className="flex items-center gap-1 mt-1 text-sm text-slate-500">
                        <MapPin className="w-3 h-3" /> {job.location}
                      </div>
                      {(job.salary_range_min || job.salary_range_max) && (
                        <div className="flex items-center gap-1 mt-1 text-xs text-slate-400">
                          <DollarSign className="w-3 h-3" />
                          {job.salary_range_min && `${job.salary_range_min}`}{job.salary_range_min && job.salary_range_max && ' - '}{job.salary_range_max && `${job.salary_range_max}`}
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    <Badge variant="outline" className={`text-xs ${STATUS_COLORS[job.status] || ''}`}>{job.status}</Badge>
                    <Badge variant="secondary" className="text-xs">{job.type}</Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle className="font-heading">Create Job Opening</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div>
              <Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Role</Label>
              <Select value={form.role} onValueChange={v => setForm({...form, role: v})}>
                <SelectTrigger className="mt-1" data-testid="job-role-select"><SelectValue placeholder="Select role" /></SelectTrigger>
                <SelectContent>{JOB_ROLES.map(r => <SelectItem key={r} value={r}>{r}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Type</Label>
              <Select value={form.type} onValueChange={v => setForm({...form, type: v})}>
                <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="branch">Branch Hiring</SelectItem>
                  <SelectItem value="HO">Head Office</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {form.type === 'branch' && (
              <div>
                <Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Branch</Label>
                <Select value={form.branch_id} onValueChange={v => setForm({...form, branch_id: v})}>
                  <SelectTrigger className="mt-1"><SelectValue placeholder="Select branch" /></SelectTrigger>
                  <SelectContent>{branches.map(b => <SelectItem key={b.id} value={b.id}>{b.name}</SelectItem>)}</SelectContent>
                </Select>
              </div>
            )}
            <div><Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Location</Label><Input value={form.location} onChange={e => setForm({...form, location: e.target.value})} placeholder="City, Area" className="mt-1" /></div>
            <div className="grid grid-cols-2 gap-3">
              <div><Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Min Salary</Label><Input type="number" value={form.salary_range_min} onChange={e => setForm({...form, salary_range_min: e.target.value})} className="mt-1" /></div>
              <div><Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Max Salary</Label><Input type="number" value={form.salary_range_max} onChange={e => setForm({...form, salary_range_max: e.target.value})} className="mt-1" /></div>
            </div>
            <div><Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Description</Label><Textarea value={form.description} onChange={e => setForm({...form, description: e.target.value})} className="mt-1" rows={3} /></div>
            <div><Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Deadline</Label><Input type="date" value={form.deadline} onChange={e => setForm({...form, deadline: e.target.value})} className="mt-1" /></div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleCreate} className="bg-blue-700 hover:bg-blue-800" data-testid="save-job-button">Create Job</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
