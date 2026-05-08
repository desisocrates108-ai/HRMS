import { useEffect, useState, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import API from '@/api';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { ArrowLeft, Building2, MapPin, Calendar, Phone, Mail, UserCheck, LogOut, Search, Briefcase } from 'lucide-react';
import { toast } from 'sonner';

const EXIT_TYPES = ['resigned', 'terminated', 'absconding', 'retired'];
const CEO_ROLES = ['CEO', 'HR'];

export default function BranchDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const canExit = CEO_ROLES.includes(user?.role);

  const [branch, setBranch] = useState(null);
  const [employees, setEmployees] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  const [exitOpen, setExitOpen] = useState(false);
  const [exitTarget, setExitTarget] = useState(null);
  const [exitForm, setExitForm] = useState({ exit_date: '', exit_reason: '', exit_type: 'resigned', remarks: '', auto_create_job: true });
  const [exiting, setExiting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [b, e, j] = await Promise.all([
        API.get(`/branches/${id}`),
        API.get(`/employees?branch_id=${id}`),
        API.get(`/jobs?branch_id=${id}`).catch(() => ({ data: [] })),
      ]);
      setBranch(b.data);
      setEmployees(e.data);
      setJobs(j.data);
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Failed to load branch');
    } finally { setLoading(false); }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  const filtered = employees.filter((emp) => {
    if (!search) return true;
    const s = search.toLowerCase();
    return [emp.name, emp.role, emp.department, emp.employment_type, emp.phone, emp.email, emp.location_city]
      .filter(Boolean).some((v) => String(v).toLowerCase().includes(s));
  });

  const handleExit = async () => {
    if (!exitForm.exit_date || !exitForm.exit_reason) {
      toast.error('Exit date and reason are required');
      return;
    }
    setExiting(true);
    try {
      const resp = await API.post(`/employees/${exitTarget.id}/exit`, exitForm);
      if (resp.data.auto_job_id) {
        toast.success('Exit recorded. New job auto-posted & Sr/Jr HR notified.');
      } else {
        toast.success('Exit recorded.');
      }
      setExitOpen(false);
      setExitForm({ exit_date: '', exit_reason: '', exit_type: 'resigned', remarks: '', auto_create_job: true });
      load();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Failed');
    } finally { setExiting(false); }
  };

  if (loading || !branch) return <div className="flex items-center justify-center h-64 text-slate-500">Loading...</div>;

  const openJobs = jobs.filter((j) => j.status === 'open');
  const autoJobs = openJobs.filter((j) => j.auto_created_from_exit);

  return (
    <div className="space-y-4 max-w-4xl" data-testid="branch-detail-page">
      <Button variant="ghost" onClick={() => navigate('/branches')} className="text-slate-500 -ml-2" data-testid="back-to-branches">
        <ArrowLeft className="w-4 h-4 mr-1" /> Back to Branches
      </Button>

      {/* Branch summary */}
      <Card className="border-slate-200 shadow-none">
        <CardContent className="p-4">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-lg bg-blue-50 flex items-center justify-center flex-shrink-0">
              <Building2 className="w-6 h-6 text-blue-700" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2 flex-wrap">
                <h2 className="text-xl font-heading font-semibold text-slate-900">{branch.name}</h2>
                <Badge variant="outline" className={branch.status === 'upcoming' ? 'text-amber-600 border-amber-200' : 'text-emerald-600 border-emerald-200'}>
                  {branch.status}
                </Badge>
              </div>
              <p className="text-sm text-slate-500 flex items-center gap-1 mt-1">
                <MapPin className="w-3 h-3" />{branch.city}, {branch.area}
              </p>
              {(branch.tentative_opening_date || branch.actual_opening_date) && (
                <p className="text-xs text-slate-400 flex items-center gap-1 mt-1">
                  <Calendar className="w-3 h-3" />
                  {branch.actual_opening_date ? `Opened ${branch.actual_opening_date}` : `Tentative ${branch.tentative_opening_date}`}
                </p>
              )}
              <div className="grid grid-cols-3 gap-2 mt-3">
                <Stat label="Employees" value={employees.length} />
                <Stat label="Open Jobs" value={openJobs.length} />
                <Stat label="Auto-posted" value={autoJobs.length} />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Open jobs (with auto-posted highlight) */}
      {openJobs.length > 0 && (
        <Card className="border-slate-200 shadow-none">
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-medium flex items-center gap-2">
              <Briefcase className="w-4 h-4 text-blue-700" /> Open Positions ({openJobs.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {openJobs.map((j) => (
                <div
                  key={j.id}
                  onClick={() => navigate(`/jobs`)}
                  className="flex items-center justify-between p-2 rounded border border-slate-100 cursor-pointer hover:border-blue-300 hover:bg-blue-50/30 transition-all"
                  data-testid={`open-job-${j.id}`}
                >
                  <div>
                    <p className="text-sm font-medium text-slate-900">{j.role}</p>
                    {j.auto_created_from_exit && (
                      <p className="text-xs text-amber-700">
                        Auto-posted after {j.exit_employee_name} exited
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    {j.auto_created_from_exit && <Badge variant="outline" className="text-xs text-amber-700 border-amber-200">Refill</Badge>}
                    <Badge className="bg-emerald-100 text-emerald-700 border-0 text-xs">Open</Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Employees */}
      <Card className="border-slate-200 shadow-none">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <CardTitle className="text-base font-medium">Employees ({filtered.length})</CardTitle>
            <div className="relative w-full md:w-72">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <Input
                placeholder="Search name, role..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9 h-9"
                data-testid="branch-employee-search"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {filtered.length === 0 ? (
            <p className="text-sm text-slate-500 py-4 text-center">No employees at this branch</p>
          ) : (
            <div className="space-y-2">
              {filtered.map((emp) => (
                <div key={emp.id} className="flex items-center justify-between p-3 rounded border border-slate-100 hover:border-slate-200 transition-all" data-testid={`branch-emp-${emp.id}`}>
                  <div className="flex items-center gap-3 min-w-0 flex-1">
                    <div className="w-9 h-9 rounded-full bg-emerald-50 flex items-center justify-center flex-shrink-0">
                      <UserCheck className="w-4 h-4 text-emerald-600" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-slate-900">{emp.name}</p>
                      <div className="flex flex-wrap items-center gap-2 mt-0.5 text-xs text-slate-500">
                        <Badge variant="outline" className="text-[10px]">{emp.role}</Badge>
                        {emp.employment_type && <span className="capitalize">{emp.employment_type.replace('_',' ')}</span>}
                        {emp.phone && <span className="flex items-center gap-0.5"><Phone className="w-3 h-3" />{emp.phone}</span>}
                        {emp.email && <span className="hidden md:flex items-center gap-0.5"><Mail className="w-3 h-3" />{emp.email}</span>}
                      </div>
                    </div>
                  </div>
                  {canExit && (
                    <Button
                      variant="ghost" size="sm"
                      className="text-rose-600 hover:text-rose-700 text-xs"
                      onClick={() => { setExitTarget(emp); setExitOpen(true); }}
                      data-testid={`branch-exit-${emp.id}`}
                    >
                      <LogOut className="w-3 h-3 mr-1" /> Exit
                    </Button>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Exit dialog */}
      <Dialog open={exitOpen} onOpenChange={setExitOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader><DialogTitle className="font-heading">Mark Employee Exit</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <p className="text-sm text-slate-600">{exitTarget?.name} ({exitTarget?.role})</p>
            <div>
              <Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Exit Date</Label>
              <Input type="date" value={exitForm.exit_date} onChange={(e) => setExitForm({ ...exitForm, exit_date: e.target.value })} className="mt-1" data-testid="branch-exit-date" />
            </div>
            <div>
              <Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Exit Type</Label>
              <Select value={exitForm.exit_type} onValueChange={(v) => setExitForm({ ...exitForm, exit_type: v })}>
                <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                <SelectContent>{EXIT_TYPES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Reason</Label>
              <Input value={exitForm.exit_reason} onChange={(e) => setExitForm({ ...exitForm, exit_reason: e.target.value })} className="mt-1" placeholder="Primary reason" data-testid="branch-exit-reason" />
            </div>
            <div>
              <Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Remarks</Label>
              <Textarea value={exitForm.remarks} onChange={(e) => setExitForm({ ...exitForm, remarks: e.target.value })} rows={2} className="mt-1" />
            </div>
            <label className="flex items-center gap-2 text-xs text-slate-600 cursor-pointer">
              <input
                type="checkbox" checked={exitForm.auto_create_job}
                onChange={(e) => setExitForm({ ...exitForm, auto_create_job: e.target.checked })}
                data-testid="branch-exit-auto-job"
              />
              Auto-post a job for this role & notify Sr/Jr HR
            </label>
            <p className="text-xs text-rose-600">Exit feedback form will be auto-sent via WhatsApp.</p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setExitOpen(false)}>Cancel</Button>
            <Button onClick={handleExit} disabled={exiting} className="bg-rose-600 hover:bg-rose-700" data-testid="branch-confirm-exit">
              {exiting ? 'Saving...' : 'Confirm Exit'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div className="p-2 rounded border border-slate-100 text-center">
      <p className="text-lg font-semibold text-slate-900">{value}</p>
      <p className="text-[10px] text-slate-500 uppercase tracking-wide">{label}</p>
    </div>
  );
}
