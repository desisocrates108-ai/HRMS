import { useState, useEffect, useCallback } from 'react';
import API from '@/api';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { UserCheck, Phone, Mail, Calendar, Building2, Wrench, LogOut, Users as UsersIcon, Search } from 'lucide-react';
import { toast } from 'sonner';

const EXIT_TYPES = ['resigned', 'terminated', 'absconding', 'retired'];

const CEO_ROLES = ['CEO', 'Super Admin', 'HR'];

export default function EmployeesPage() {
  const { user } = useAuth();
  const isCEOorHR = CEO_ROLES.includes(user?.role);

  const [active, setActive] = useState([]);
  const [exited, setExited] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  const [topTab, setTopTab] = useState('branch'); // branch | head_office | exited
  const [subTab, setSubTab] = useState('technician'); // technician|management OR mid_level|management
  const [globalSearch, setGlobalSearch] = useState('');

  const [exitOpen, setExitOpen] = useState(false);
  const [exitTarget, setExitTarget] = useState(null);
  const [exitForm, setExitForm] = useState({ exit_date: '', exit_reason: '', exit_type: 'resigned', remarks: '' });
  const [exiting, setExiting] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const reqs = [API.get('/employees'), API.get('/employees/segments/summary')];
      if (isCEOorHR) reqs.push(API.get('/employees/exited'));
      const results = await Promise.all(reqs);
      setActive(results[0].data);
      setSummary(results[1].data);
      if (isCEOorHR) setExited(results[2].data);
    } catch {
      toast.error('Failed to load employees');
    } finally {
      setLoading(false);
    }
  }, [isCEOorHR]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // Sync sub-tab default on top tab change
  useEffect(() => {
    if (topTab === 'branch') setSubTab('technician');
    else if (topTab === 'head_office') setSubTab('mid_level');
  }, [topTab]);

  const handleExit = async () => {
    if (!exitForm.exit_date || !exitForm.exit_reason) {
      toast.error('Exit date and reason are required');
      return;
    }
    setExiting(true);
    try {
      await API.post(`/employees/${exitTarget.id}/exit`, exitForm);
      toast.success('Employee marked as exited. WhatsApp feedback queued.');
      setExitOpen(false);
      setExitForm({ exit_date: '', exit_reason: '', exit_type: 'resigned', remarks: '' });
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to record exit');
    } finally {
      setExiting(false);
    }
  };

  if (loading) return <div className="flex items-center justify-center h-64 text-slate-500">Loading...</div>;

  const matchSearch = (e) => {
    if (!globalSearch) return true;
    const s = globalSearch.toLowerCase();
    return [e.name, e.role, e.department, e.employment_type, e.phone, e.email, e.location_city, e.category]
      .filter(Boolean).some((v) => String(v).toLowerCase().includes(s));
  };

  const filteredActive = active.filter((e) => {
    if (globalSearch) return matchSearch(e); // search across ALL segments
    return e.category === topTab && e.employment_type === subTab;
  });
  const rows = topTab === 'exited'
    ? (globalSearch ? exited.filter(matchSearch) : exited)
    : filteredActive;

  return (
    <div className="space-y-4" data-testid="employees-page">
      <div>
        <h1 className="text-xl md:text-2xl font-heading font-semibold text-slate-900">Employees</h1>
        <p className="text-sm text-slate-500">
          {summary?.total_active || 0} active
          {isCEOorHR && summary?.total_exited ? ` · ${summary.total_exited} exited` : ''}
        </p>
      </div>

      {/* Global search (searches across ALL segments) */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
        <Input
          placeholder="Search by name, role, city, phone, email..."
          value={globalSearch}
          onChange={(e) => setGlobalSearch(e.target.value)}
          className="pl-9 h-10"
          data-testid="employee-search-input"
        />
        {globalSearch && (
          <p className="text-xs text-slate-500 mt-1">Showing global results across Branch, Head Office, and Exited</p>
        )}
      </div>

      {/* Segment summary chips */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          <SummaryChip icon={<Wrench className="w-4 h-4" />} label="Branch Technicians" value={summary.branch.technician} color="bg-blue-50 text-blue-700" />
          <SummaryChip icon={<Building2 className="w-4 h-4" />} label="Branch Mgmt" value={summary.branch.management} color="bg-emerald-50 text-emerald-700" />
          <SummaryChip icon={<UsersIcon className="w-4 h-4" />} label="HO Mid-Level" value={summary.head_office.mid_level} color="bg-violet-50 text-violet-700" />
          <SummaryChip icon={<Building2 className="w-4 h-4" />} label="HO Mgmt" value={summary.head_office.management} color="bg-amber-50 text-amber-700" />
        </div>
      )}

      {/* Top-level tabs: Branch / Head Office / Exited (CEO-HR only) */}
      <Tabs value={topTab} onValueChange={setTopTab}>
        <TabsList className={`grid w-full ${isCEOorHR ? 'grid-cols-3' : 'grid-cols-2'}`}>
          <TabsTrigger value="branch" data-testid="tab-branch">
            <Wrench className="w-4 h-4 mr-1" /> Branch
          </TabsTrigger>
          <TabsTrigger value="head_office" data-testid="tab-ho">
            <Building2 className="w-4 h-4 mr-1" /> Head Office
          </TabsTrigger>
          {isCEOorHR && (
            <TabsTrigger value="exited" data-testid="tab-exited">
              <LogOut className="w-4 h-4 mr-1" /> Left ({summary?.total_exited || 0})
            </TabsTrigger>
          )}
        </TabsList>

        {/* Branch sub-tabs */}
        <TabsContent value="branch" className="mt-3">
          <Tabs value={subTab} onValueChange={setSubTab}>
            <TabsList className="grid grid-cols-2 w-full md:w-80">
              <TabsTrigger value="technician" data-testid="sub-tab-technician">Technicians</TabsTrigger>
              <TabsTrigger value="management" data-testid="sub-tab-branch-mgmt">Management</TabsTrigger>
            </TabsList>
          </Tabs>
        </TabsContent>

        {/* Head Office sub-tabs */}
        <TabsContent value="head_office" className="mt-3">
          <Tabs value={subTab} onValueChange={setSubTab}>
            <TabsList className="grid grid-cols-2 w-full md:w-80">
              <TabsTrigger value="mid_level" data-testid="sub-tab-mid-level">Mid-Level</TabsTrigger>
              <TabsTrigger value="management" data-testid="sub-tab-ho-mgmt">Management</TabsTrigger>
            </TabsList>
          </Tabs>
        </TabsContent>
      </Tabs>

      {/* Employee list */}
      {rows.length === 0 ? (
        <div className="text-center py-12 text-slate-500 text-sm">No employees in this segment</div>
      ) : (
        <div className="space-y-2">
          {rows.map((emp) => (
            <Card key={emp.id} className="border-slate-200 shadow-none" data-testid={`employee-row-${emp.id}`}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3 min-w-0 flex-1">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${emp.status === 'left' ? 'bg-rose-50' : 'bg-emerald-50'}`}>
                      {emp.status === 'left' ? <LogOut className="w-5 h-5 text-rose-600" /> : <UserCheck className="w-5 h-5 text-emerald-600" />}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="font-medium text-slate-900 text-sm">{emp.name}</p>
                      <div className="flex flex-wrap items-center gap-2 mt-0.5 text-xs text-slate-500">
                        {emp.phone && <span className="flex items-center gap-1"><Phone className="w-3 h-3" />{emp.phone}</span>}
                        {emp.email && <span className="flex items-center gap-1"><Mail className="w-3 h-3" />{emp.email}</span>}
                        {emp.joining_date && <span className="flex items-center gap-1"><Calendar className="w-3 h-3" />Joined {emp.joining_date}</span>}
                        {emp.exit_date && <span className="flex items-center gap-1 text-rose-600"><LogOut className="w-3 h-3" />Exited {emp.exit_date}</span>}
                      </div>
                      {emp.status === 'left' && emp.exit_reason && (
                        <p className="text-xs text-rose-600 mt-1 italic">{emp.exit_type}: {emp.exit_reason}</p>
                      )}
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-1 flex-shrink-0">
                    <Badge variant="outline" className="text-xs">{emp.role}</Badge>
                    {emp.department && <span className="text-xs text-slate-400">{emp.department}</span>}
                    {isCEOorHR && emp.status !== 'left' && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-rose-600 hover:text-rose-700 text-xs h-7 px-2"
                        onClick={() => { setExitTarget(emp); setExitOpen(true); }}
                        data-testid={`exit-button-${emp.id}`}
                      >
                        Mark Exit
                      </Button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Exit dialog */}
      <Dialog open={exitOpen} onOpenChange={setExitOpen}>
        <DialogContent className="max-w-md" data-testid="exit-dialog">
          <DialogHeader><DialogTitle className="font-heading">Mark Employee Exit</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <p className="text-sm text-slate-600">{exitTarget?.name}</p>
            <div>
              <Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Exit Date</Label>
              <Input type="date" value={exitForm.exit_date} onChange={(e) => setExitForm({ ...exitForm, exit_date: e.target.value })} className="mt-1" data-testid="exit-date-input" />
            </div>
            <div>
              <Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Exit Type</Label>
              <Select value={exitForm.exit_type} onValueChange={(v) => setExitForm({ ...exitForm, exit_type: v })}>
                <SelectTrigger className="mt-1" data-testid="exit-type-select"><SelectValue /></SelectTrigger>
                <SelectContent>{EXIT_TYPES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Reason</Label>
              <Input value={exitForm.exit_reason} onChange={(e) => setExitForm({ ...exitForm, exit_reason: e.target.value })} className="mt-1" placeholder="Primary reason" data-testid="exit-reason-input" />
            </div>
            <div>
              <Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Remarks</Label>
              <Textarea value={exitForm.remarks} onChange={(e) => setExitForm({ ...exitForm, remarks: e.target.value })} rows={3} className="mt-1" data-testid="exit-remarks-input" />
            </div>
            <p className="text-xs text-rose-600">Exit feedback form will be auto-sent via WhatsApp.</p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setExitOpen(false)}>Cancel</Button>
            <Button onClick={handleExit} disabled={exiting} className="bg-rose-600 hover:bg-rose-700" data-testid="confirm-exit-button">
              {exiting ? 'Saving...' : 'Confirm Exit'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function SummaryChip({ icon, label, value, color }) {
  return (
    <div className={`flex items-center gap-2 px-3 py-2 rounded-md ${color}`}>
      {icon}
      <div className="min-w-0">
        <p className="text-xs truncate">{label}</p>
        <p className="text-sm font-semibold">{value}</p>
      </div>
    </div>
  );
}
