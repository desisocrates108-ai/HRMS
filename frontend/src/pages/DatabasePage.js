import { useState, useEffect, useRef } from 'react';
import API from '@/api';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import {
  Search, Eye, Phone, Mail, Building, Wrench, Plus, Upload, Download, FileDown,
  Pencil, ChevronRight, Users, UserCheck, Pause, X as XIcon,
} from 'lucide-react';
import { toast } from 'sonner';

const STAGES = [
  { value: 'new', label: 'New', color: 'bg-blue-700' },
  { value: 'qualified', label: 'Qualified', color: 'bg-emerald-600' },
  { value: 'hr', label: 'HR', color: 'bg-amber-600' },
  { value: 'manager', label: 'Manager', color: 'bg-violet-600' },
  { value: 'selected', label: 'Selected', color: 'bg-teal-600' },
  { value: 'three_months', label: '3 Months', color: 'bg-indigo-600' },
  { value: 'joined', label: 'Joined', color: 'bg-green-700' },
  { value: 'hold', label: 'Hold', color: 'bg-orange-500' },
  { value: 'rejected', label: 'Rejected', color: 'bg-rose-600' },
];

const EMP_TYPE_OPTIONS = [
  { value: 'all', label: 'All Types' },
  { value: 'head_office', label: 'Head Office' },
  { value: 'franchise', label: 'Franchise' },
];

function EmployeeDetail({ emp, onClose, onChanged, designations, branches }) {
  const [form, setForm] = useState({});
  const [saving, setSaving] = useState(false);
  const [history, setHistory] = useState([]);

  useEffect(() => {
    if (!emp) return;
    setForm({
      name: emp.name || '',
      phone: emp.phone || '',
      email: emp.email || '',
      employee_type: emp.employee_type || 'head_office',
      role: emp.role || '',
      department: emp.department || '',
      branch_id: emp.branch_id || '',
      location_city: emp.location_city || '',
      location_area: emp.location_area || '',
      joining_date: emp.joining_date || '',
      salary: emp.salary || '',
    });
    API.get(`/employees/${emp.id}/history`).then(r => setHistory(r.data)).catch(() => setHistory([]));
  }, [emp]);

  if (!emp) return null;

  const save = async () => {
    setSaving(true);
    try {
      const payload = { ...form };
      if (payload.salary === '') payload.salary = null;
      else if (payload.salary) payload.salary = parseFloat(payload.salary);
      if (!payload.branch_id) payload.branch_id = null;
      await API.put(`/employees/${emp.id}`, payload);
      toast.success('Employee updated');
      onChanged && onChanged();
      onClose();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update');
    } finally { setSaving(false); }
  };

  return (
    <Dialog open={!!emp} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto" data-testid="employee-detail-dialog">
        <DialogHeader>
          <DialogTitle className="font-heading text-xl flex items-center gap-2">
            {emp.name}
            <Badge variant="outline" className="text-[10px] font-mono">{emp.employee_code}</Badge>
            <Badge variant={emp.employee_type === 'franchise' ? 'default' : 'secondary'} className="text-[10px]">
              {emp.employee_type === 'franchise' ? 'FRANCHISE EMPLOYEE' : 'HEAD OFFICE EMPLOYEE'}
            </Badge>
          </DialogTitle>
        </DialogHeader>

        <div className="grid grid-cols-2 gap-3">
          <div><Label className="text-xs">Name</Label><Input value={form.name} onChange={e => setForm({...form, name: e.target.value})} className="mt-1" /></div>
          <div><Label className="text-xs">Phone</Label><Input value={form.phone} onChange={e => setForm({...form, phone: e.target.value})} className="mt-1" /></div>
          <div className="col-span-2"><Label className="text-xs">Email</Label><Input value={form.email} onChange={e => setForm({...form, email: e.target.value})} className="mt-1" /></div>
          <div>
            <Label className="text-xs">Employee Type</Label>
            <Select value={form.employee_type} onValueChange={v => setForm({...form, employee_type: v})}>
              <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="head_office">Head Office</SelectItem>
                <SelectItem value="franchise">Franchise</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label className="text-xs">Designation</Label>
            <Select value={form.role} onValueChange={v => setForm({...form, role: v})}>
              <SelectTrigger className="mt-1"><SelectValue placeholder="Select" /></SelectTrigger>
              <SelectContent>
                {designations.map(d => <SelectItem key={d.id} value={d.name}>{d.name}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div><Label className="text-xs">Department</Label><Input value={form.department} onChange={e => setForm({...form, department: e.target.value})} className="mt-1" /></div>
          <div>
            <Label className="text-xs">Branch</Label>
            <Select value={form.branch_id || '__none'} onValueChange={v => setForm({...form, branch_id: v === '__none' ? '' : v})}>
              <SelectTrigger className="mt-1"><SelectValue placeholder="None" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="__none">— None —</SelectItem>
                {branches.map(b => <SelectItem key={b.id} value={b.id}>{b.name}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div><Label className="text-xs">City</Label><Input value={form.location_city} onChange={e => setForm({...form, location_city: e.target.value})} className="mt-1" /></div>
          <div><Label className="text-xs">Area</Label><Input value={form.location_area} onChange={e => setForm({...form, location_area: e.target.value})} className="mt-1" /></div>
          <div><Label className="text-xs">Joining Date</Label><Input type="date" value={form.joining_date} onChange={e => setForm({...form, joining_date: e.target.value})} className="mt-1" /></div>
          <div><Label className="text-xs">Salary</Label><Input type="number" value={form.salary} onChange={e => setForm({...form, salary: e.target.value})} className="mt-1" /></div>
        </div>

        {emp.hold_reason && emp.current_stage === 'hold' && (
          <div className="p-2 bg-orange-50 border border-orange-200 rounded text-xs text-orange-800">
            <strong>On Hold:</strong> {emp.hold_reason}
          </div>
        )}
        {emp.rejection_reason && emp.current_stage === 'rejected' && (
          <div className="p-2 bg-rose-50 border border-rose-200 rounded text-xs text-rose-800">
            <strong>Rejected:</strong> {emp.rejection_reason}
          </div>
        )}

        {history.length > 0 && (
          <Card className="border-slate-200 shadow-none">
            <CardContent className="p-3 text-sm">
              <p className="font-semibold text-slate-700 mb-1">Stage History</p>
              <div className="space-y-1 max-h-32 overflow-y-auto">
                {history.map((h, i) => (
                  <div key={i} className="text-xs text-slate-600 flex justify-between">
                    <span>{h.from_stage || 'start'} → <strong>{h.to_stage}</strong> · {h.changed_by_name}</span>
                    <span className="text-slate-400">{new Date(h.timestamp).toLocaleString()}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Close</Button>
          <Button onClick={save} disabled={saving} className="bg-blue-700 hover:bg-blue-800" data-testid="save-employee-edit-button">
            {saving ? 'Saving...' : 'Save Changes'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function DatabasePage() {
  const fileInputRef = useRef(null);

  const [employees, setEmployees] = useState([]);
  const [stats, setStats] = useState({ stage_counts: {}, summary: {} });
  const [designations, setDesignations] = useState([]);
  const [branches, setBranches] = useState([]);

  const [loading, setLoading] = useState(true);
  const [activeStage, setActiveStage] = useState('joined');
  const [empTypeFilter, setEmpTypeFilter] = useState('all');
  const [search, setSearch] = useState('');

  const [createOpen, setCreateOpen] = useState(false);
  const [createForm, setCreateForm] = useState({
    name: '', phone: '', email: '', employee_type: 'head_office',
    current_stage: 'new', role: '', department: '', branch_id: '',
    location_city: '', location_area: '', joining_date: '', salary: '', employee_code: '',
  });

  const [stageDialog, setStageDialog] = useState({ open: false, emp: null, to: '', reason: '' });
  const [detailEmp, setDetailEmp] = useState(null);
  const [importResult, setImportResult] = useState(null);

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [empRes, statsRes, dRes, bRes] = await Promise.all([
        API.get('/employees'),
        API.get('/employees/pipeline-stats'),
        API.get('/designations', { params: { active_only: true } }),
        API.get('/branches'),
      ]);
      setEmployees(empRes.data);
      setStats(statsRes.data);
      setDesignations(dRes.data);
      setBranches(bRes.data);
    } catch { toast.error('Failed to load database'); }
    finally { setLoading(false); }
  };

  const handleCreate = async () => {
    if (!createForm.name.trim()) { toast.error('Name is required'); return; }
    if (!createForm.employee_type) { toast.error('Employee Type is required'); return; }
    try {
      const payload = { ...createForm };
      if (payload.salary === '') payload.salary = null;
      else if (payload.salary) payload.salary = parseFloat(payload.salary);
      if (!payload.branch_id) payload.branch_id = null;
      Object.keys(payload).forEach(k => { if (payload[k] === '') payload[k] = null; });
      payload.name = createForm.name;
      payload.employee_type = createForm.employee_type;
      payload.current_stage = createForm.current_stage || 'new';
      await API.post('/employees', payload);
      toast.success('Employee added');
      setCreateOpen(false);
      setCreateForm({
        name: '', phone: '', email: '', employee_type: 'head_office',
        current_stage: 'new', role: '', department: '', branch_id: '',
        location_city: '', location_area: '', joining_date: '', salary: '', employee_code: '',
      });
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to add employee');
    }
  };

  const moveStage = (emp, to) => {
    if (to === 'hold' || to === 'rejected') {
      setStageDialog({ open: true, emp, to, reason: '' });
      return;
    }
    confirmMove(emp, to, null);
  };

  const confirmMove = async (emp, to, reason) => {
    try {
      const body = { to_stage: to };
      if (to === 'hold') body.hold_reason = reason;
      if (to === 'rejected') body.rejection_reason = reason;
      await API.post(`/employees/${emp.id}/transition`, body);
      toast.success(`Moved to ${STAGES.find(s => s.value === to)?.label}`);
      setStageDialog({ open: false, emp: null, to: '', reason: '' });
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to move stage');
    }
  };

  const downloadTemplate = async () => {
    try {
      const res = await API.get('/employees/excel/template', { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url; link.setAttribute('download', 'employee_template.xlsx');
      document.body.appendChild(link); link.click(); link.remove();
      toast.success('Template downloaded');
    } catch { toast.error('Failed to download template'); }
  };

  const exportExcel = async () => {
    try {
      const params = {};
      if (empTypeFilter !== 'all') params.employee_type = empTypeFilter;
      const res = await API.get('/employees/excel/export', { params, responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url; link.setAttribute('download', `employees_${Date.now()}.xlsx`);
      document.body.appendChild(link); link.click(); link.remove();
      toast.success('Export downloaded');
    } catch { toast.error('Failed to export'); }
  };

  const handleImport = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await API.post('/employees/excel/import', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setImportResult(res.data);
      toast.success(`Imported ${res.data.created} employees (${res.data.skipped} skipped)`);
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Import failed');
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  // Filter on client
  const filtered = employees.filter(e => {
    const matchStage = e.current_stage === activeStage;
    const matchType = empTypeFilter === 'all' || e.employee_type === empTypeFilter;
    const matchSearch = !search ||
      e.name?.toLowerCase().includes(search.toLowerCase()) ||
      e.phone?.includes(search) ||
      e.employee_code?.toLowerCase().includes(search.toLowerCase()) ||
      e.role?.toLowerCase().includes(search.toLowerCase());
    return matchStage && matchType && matchSearch;
  });

  // Compute live stage counts for current type filter
  const stageCounts = {};
  STAGES.forEach(s => {
    stageCounts[s.value] = employees.filter(e => {
      const matchType = empTypeFilter === 'all' || e.employee_type === empTypeFilter;
      return e.current_stage === s.value && matchType;
    }).length;
  });

  const summary = stats.summary || {};

  if (loading) return <div className="flex items-center justify-center h-64 text-slate-500">Loading...</div>;

  const branchById = (id) => branches.find(b => b.id === id);

  return (
    <div className="space-y-4" data-testid="database-page">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-xl md:text-2xl font-heading font-semibold text-slate-900 flex items-center gap-2">
            <Users className="w-5 h-5" /> Employee Database
          </h1>
          <p className="text-sm text-slate-500">Pipeline of all employees · Head Office + Franchise</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="outline" size="sm" onClick={downloadTemplate} data-testid="download-template-button">
            <FileDown className="w-3.5 h-3.5 mr-1" /> Template
          </Button>
          <Button variant="outline" size="sm" onClick={() => fileInputRef.current?.click()} data-testid="excel-import-button">
            <Upload className="w-3.5 h-3.5 mr-1" /> Import Excel
          </Button>
          <input ref={fileInputRef} type="file" accept=".xlsx,.xls" className="hidden" onChange={handleImport} data-testid="excel-import-input" />
          <Button variant="outline" size="sm" onClick={exportExcel} data-testid="excel-export-button">
            <Download className="w-3.5 h-3.5 mr-1" /> Export
          </Button>
          <Button size="sm" onClick={() => setCreateOpen(true)} className="bg-blue-700 hover:bg-blue-800" data-testid="create-employee-button">
            <Plus className="w-3.5 h-3.5 mr-1" /> Add Employee
          </Button>
        </div>
      </div>

      {/* Summary counters */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2" data-testid="employee-summary-counters">
        <CounterCard label="Total" value={summary.total || 0} color="bg-slate-100 text-slate-900" testid="counter-total" />
        <CounterCard label="Head Office" value={summary.head_office || 0} color="bg-blue-50 text-blue-900" testid="counter-ho" icon={<Building className="w-3 h-3" />} />
        <CounterCard label="Franchise" value={summary.franchise || 0} color="bg-indigo-50 text-indigo-900" testid="counter-franchise" icon={<Wrench className="w-3 h-3" />} />
        <CounterCard label="Joined" value={summary.joined || 0} color="bg-emerald-50 text-emerald-900" testid="counter-joined" icon={<UserCheck className="w-3 h-3" />} />
        <CounterCard label="Hold" value={summary.hold || 0} color="bg-orange-50 text-orange-900" testid="counter-hold" icon={<Pause className="w-3 h-3" />} />
        <CounterCard label="Rejected" value={summary.rejected || 0} color="bg-rose-50 text-rose-900" testid="counter-rejected" icon={<XIcon className="w-3 h-3" />} />
      </div>

      {/* Filters */}
      <Card className="border-slate-200 shadow-none">
        <CardContent className="p-3 space-y-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <Input
              placeholder="Search by name, phone, employee code, designation..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 h-10"
              data-testid="employee-search-input"
            />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <Select value={empTypeFilter} onValueChange={setEmpTypeFilter}>
              <SelectTrigger className="h-9" data-testid="employee-type-filter"><SelectValue /></SelectTrigger>
              <SelectContent>
                {EMP_TYPE_OPTIONS.map(o => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Stage tabs */}
      <Tabs value={activeStage} onValueChange={setActiveStage}>
        <TabsList className="w-full grid h-auto p-1 grid-cols-3 md:grid-cols-9">
          {STAGES.map(s => (
            <TabsTrigger key={s.value} value={s.value} className="text-xs md:text-sm px-1 py-2" data-testid={`stage-tab-${s.value}`}>
              <span className="truncate">{s.label}</span>
              <Badge variant="secondary" className="ml-1 text-xs px-1.5 py-0">{stageCounts[s.value]}</Badge>
            </TabsTrigger>
          ))}
        </TabsList>

        {STAGES.map(s => (
          <TabsContent key={s.value} value={s.value} className="mt-3">
            {filtered.length === 0 ? (
              <div className="text-center py-8 text-slate-500 text-sm">No employees in this stage</div>
            ) : (
              <div className="space-y-2">
                {filtered.map(e => {
                  const branch = branchById(e.branch_id);
                  return (
                    <Card key={e.id} className="border-slate-200 shadow-none hover:-translate-y-0.5 hover:shadow-md transition-all duration-200" data-testid={`employee-card-${e.id}`}>
                      <CardContent className="p-3 md:p-4">
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex items-start gap-3 min-w-0 cursor-pointer flex-1" onClick={() => setDetailEmp(e)}>
                            <div className={`w-2 self-stretch rounded-full ${s.color} flex-shrink-0`} />
                            <div className="min-w-0 flex-1">
                              <div className="flex items-center gap-2 flex-wrap">
                                <p className="font-medium text-slate-900 truncate">{e.name}</p>
                                <Badge variant="outline" className="text-[10px] font-mono">{e.employee_code || '—'}</Badge>
                                <Badge className={`text-[10px] ${e.employee_type === 'franchise' ? 'bg-indigo-600 hover:bg-indigo-600' : 'bg-blue-700 hover:bg-blue-700'}`}>
                                  {e.employee_type === 'franchise' ? 'FRANCHISE EMPLOYEE' : 'HEAD OFFICE EMPLOYEE'}
                                </Badge>
                              </div>
                              <div className="flex items-center gap-x-3 gap-y-1 mt-1 flex-wrap text-xs text-slate-500">
                                {e.phone && <span className="flex items-center gap-1"><Phone className="w-3 h-3" />{e.phone}</span>}
                                {e.email && <span className="flex items-center gap-1"><Mail className="w-3 h-3" />{e.email}</span>}
                                {e.role && <span>· {e.role}</span>}
                                {e.department && <span>· {e.department}</span>}
                                {branch && <span>· {branch.name}</span>}
                              </div>
                              {e.hold_reason && s.value === 'hold' && (
                                <Badge variant="outline" className="mt-1 text-xs px-1.5 py-0 text-orange-700 border-orange-200">Hold: {e.hold_reason.slice(0, 40)}</Badge>
                              )}
                              {e.rejection_reason && s.value === 'rejected' && (
                                <Badge variant="outline" className="mt-1 text-xs px-1.5 py-0 text-rose-700 border-rose-200">Reason: {e.rejection_reason.slice(0, 40)}</Badge>
                              )}
                            </div>
                          </div>
                          <div className="flex items-center gap-1 flex-shrink-0">
                            <Select value="" onValueChange={(v) => moveStage(e, v)}>
                              <SelectTrigger className="h-7 w-28 text-xs" data-testid={`move-stage-${e.id}`}>
                                <SelectValue placeholder="Move →" />
                              </SelectTrigger>
                              <SelectContent>
                                {STAGES.filter(x => x.value !== e.current_stage).map(x => (
                                  <SelectItem key={x.value} value={x.value} className="text-xs">{x.label}</SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setDetailEmp(e)} data-testid={`view-employee-${e.id}`}>
                              <Eye className="w-3.5 h-3.5" />
                            </Button>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}
          </TabsContent>
        ))}
      </Tabs>

      {/* Create Employee Dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle className="font-heading">Add Employee</DialogTitle></DialogHeader>
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2"><Label className="text-xs">Name *</Label><Input value={createForm.name} onChange={e => setCreateForm({...createForm, name: e.target.value})} className="mt-1" data-testid="emp-name-input" /></div>
            <div><Label className="text-xs">Phone</Label><Input value={createForm.phone} onChange={e => setCreateForm({...createForm, phone: e.target.value})} className="mt-1" data-testid="emp-phone-input" /></div>
            <div><Label className="text-xs">Email</Label><Input value={createForm.email} onChange={e => setCreateForm({...createForm, email: e.target.value})} className="mt-1" /></div>
            <div>
              <Label className="text-xs">Employee Type *</Label>
              <Select value={createForm.employee_type} onValueChange={v => setCreateForm({...createForm, employee_type: v})}>
                <SelectTrigger className="mt-1" data-testid="emp-type-select"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="head_office">Head Office</SelectItem>
                  <SelectItem value="franchise">Franchise</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs">Stage</Label>
              <Select value={createForm.current_stage} onValueChange={v => setCreateForm({...createForm, current_stage: v})}>
                <SelectTrigger className="mt-1" data-testid="emp-stage-select"><SelectValue /></SelectTrigger>
                <SelectContent>{STAGES.map(s => <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs">Designation</Label>
              <Select value={createForm.role} onValueChange={v => setCreateForm({...createForm, role: v})}>
                <SelectTrigger className="mt-1" data-testid="emp-designation-select"><SelectValue placeholder="Select" /></SelectTrigger>
                <SelectContent>{designations.map(d => <SelectItem key={d.id} value={d.name}>{d.name}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div><Label className="text-xs">Department</Label><Input value={createForm.department} onChange={e => setCreateForm({...createForm, department: e.target.value})} className="mt-1" /></div>
            <div>
              <Label className="text-xs">Branch</Label>
              <Select value={createForm.branch_id || '__none'} onValueChange={v => setCreateForm({...createForm, branch_id: v === '__none' ? '' : v})}>
                <SelectTrigger className="mt-1"><SelectValue placeholder="None" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none">— None —</SelectItem>
                  {branches.map(b => <SelectItem key={b.id} value={b.id}>{b.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div><Label className="text-xs">City</Label><Input value={createForm.location_city} onChange={e => setCreateForm({...createForm, location_city: e.target.value})} className="mt-1" /></div>
            <div><Label className="text-xs">Area</Label><Input value={createForm.location_area} onChange={e => setCreateForm({...createForm, location_area: e.target.value})} className="mt-1" /></div>
            <div><Label className="text-xs">Joining Date</Label><Input type="date" value={createForm.joining_date} onChange={e => setCreateForm({...createForm, joining_date: e.target.value})} className="mt-1" /></div>
            <div><Label className="text-xs">Salary</Label><Input type="number" value={createForm.salary} onChange={e => setCreateForm({...createForm, salary: e.target.value})} className="mt-1" /></div>
            <div className="col-span-2"><Label className="text-xs">Employee Code (leave blank to auto-generate)</Label><Input value={createForm.employee_code} onChange={e => setCreateForm({...createForm, employee_code: e.target.value})} placeholder="e.g., EMP0099" className="mt-1" data-testid="emp-code-input" /></div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>Cancel</Button>
            <Button onClick={handleCreate} className="bg-blue-700 hover:bg-blue-800" data-testid="save-employee-button">Add Employee</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Stage Transition Dialog (Hold/Reject reason) */}
      <Dialog open={stageDialog.open} onOpenChange={(v) => !v && setStageDialog({ open: false, emp: null, to: '', reason: '' })}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="font-heading">Move to {STAGES.find(s => s.value === stageDialog.to)?.label}</DialogTitle>
          </DialogHeader>
          <div className="space-y-2">
            <p className="text-sm text-slate-600">
              Provide a reason for <strong>{stageDialog.emp?.name}</strong>. This is required and visible in history.
            </p>
            <Textarea
              placeholder={stageDialog.to === 'hold' ? 'e.g., Awaiting documents, salary discussion pending...' : 'e.g., Did not clear interview, no-show...'}
              rows={4}
              value={stageDialog.reason}
              onChange={(e) => setStageDialog({ ...stageDialog, reason: e.target.value })}
              data-testid="stage-reason-textarea"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setStageDialog({ open: false, emp: null, to: '', reason: '' })}>Cancel</Button>
            <Button
              onClick={() => {
                if (!stageDialog.reason.trim()) { toast.error('Reason is required'); return; }
                confirmMove(stageDialog.emp, stageDialog.to, stageDialog.reason.trim());
              }}
              className={stageDialog.to === 'hold' ? 'bg-orange-500 hover:bg-orange-600' : 'bg-rose-600 hover:bg-rose-700'}
              data-testid="confirm-stage-move-button"
            >
              Confirm
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Import result */}
      <Dialog open={!!importResult} onOpenChange={(v) => !v && setImportResult(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader><DialogTitle className="font-heading">Import Result</DialogTitle></DialogHeader>
          <div className="space-y-2 text-sm">
            <p><strong>{importResult?.created || 0}</strong> employees created.</p>
            <p><strong>{importResult?.skipped || 0}</strong> rows skipped.</p>
            {importResult?.errors?.length > 0 && (
              <div className="border border-rose-200 bg-rose-50 rounded p-2 max-h-48 overflow-y-auto text-xs">
                <p className="font-semibold text-rose-700 mb-1">Errors:</p>
                {importResult.errors.map((er, i) => (
                  <p key={i} className="text-rose-700">Row {er.row}: {er.error}</p>
                ))}
              </div>
            )}
          </div>
          <DialogFooter>
            <Button onClick={() => setImportResult(null)}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {detailEmp && (
        <EmployeeDetail
          emp={detailEmp}
          onClose={() => setDetailEmp(null)}
          onChanged={fetchData}
          designations={designations}
          branches={branches}
        />
      )}
    </div>
  );
}

function CounterCard({ label, value, color, testid, icon }) {
  return (
    <Card className={`border-slate-200 shadow-none ${color}`} data-testid={testid}>
      <CardContent className="p-3">
        <div className="flex items-center justify-between">
          <p className="text-xs font-medium uppercase tracking-wider opacity-70 flex items-center gap-1">{icon}{label}</p>
        </div>
        <p className="text-2xl font-heading font-semibold mt-1">{value}</p>
      </CardContent>
    </Card>
  );
}
