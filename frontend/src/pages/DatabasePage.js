import { useState, useEffect, useMemo, useRef } from 'react';
import API from '@/api';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import {
  Search, Eye, Plus, Upload, Download, FileDown, Users,
  Building, Wrench, UserCheck, Pause, X as XIcon, Trash2,
} from 'lucide-react';
import { toast } from 'sonner';

const STAGES = [
  { value: 'new', label: 'New', tone: 'bg-blue-50 text-blue-700 border-blue-200' },
  { value: 'qualified', label: 'Qualified', tone: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  { value: 'hr', label: 'HR', tone: 'bg-amber-50 text-amber-700 border-amber-200' },
  { value: 'manager', label: 'Manager', tone: 'bg-violet-50 text-violet-700 border-violet-200' },
  { value: 'selected', label: 'Selected', tone: 'bg-teal-50 text-teal-700 border-teal-200' },
  { value: 'three_months', label: '3 Months', tone: 'bg-indigo-50 text-indigo-700 border-indigo-200' },
  { value: 'joined', label: 'Joined', tone: 'bg-green-50 text-green-700 border-green-200' },
  { value: 'hold', label: 'Hold', tone: 'bg-orange-50 text-orange-700 border-orange-200' },
  { value: 'rejected', label: 'Rejected', tone: 'bg-rose-50 text-rose-700 border-rose-200' },
];

function fmtDate(iso) {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    return d.toLocaleDateString();
  } catch { return iso; }
}

function StageBadge({ stage }) {
  const s = STAGES.find(x => x.value === stage);
  if (!s) return <Badge variant="outline" className="text-xs">{stage || '—'}</Badge>;
  return <Badge variant="outline" className={`text-[11px] ${s.tone}`}>{s.label}</Badge>;
}

function TypeBadge({ type, size = 'sm' }) {
  const cls = type === 'franchise'
    ? 'bg-indigo-600 hover:bg-indigo-600 text-white'
    : 'bg-blue-700 hover:bg-blue-700 text-white';
  const label = type === 'franchise' ? 'FRANCHISE EMPLOYEE' : 'HEAD OFFICE EMPLOYEE';
  return <Badge className={`${cls} ${size === 'sm' ? 'text-[10px]' : 'text-xs'}`}>{label}</Badge>;
}

// ---------------- Employee Detail Drawer ----------------
function EmployeeDetailDrawer({ open, emp, onClose, onChanged, designations, branches, isSuper }) {
  const [history, setHistory] = useState([]);
  const [audit, setAudit] = useState([]);
  const [notes, setNotes] = useState([]);
  const [docs, setDocs] = useState([]);
  const [newNote, setNewNote] = useState('');
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({});
  const [stageDialog, setStageDialog] = useState({ open: false, to: '', reason: '' });

  useEffect(() => {
    if (!open || !emp) return;
    setEditing(false);
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
    Promise.allSettled([
      API.get(`/employees/${emp.id}/history`).then(r => setHistory(r.data)),
      API.get(`/employees/${emp.id}/notes`).then(r => setNotes(r.data)),
      isSuper ? API.get('/audit', { params: { entity_id: emp.id, entity_type: 'employee', limit: 50 } }).then(r => setAudit(r.data)).catch(() => setAudit([])) : Promise.resolve(),
      API.get(`/documents/lead/${emp.id}`).then(r => setDocs(r.data || [])).catch(() => setDocs([])),
    ]);
  }, [open, emp, isSuper]);

  if (!emp) return null;

  const saveEdit = async () => {
    try {
      const payload = { ...form };
      if (payload.salary === '') payload.salary = null;
      else if (payload.salary !== null) payload.salary = parseFloat(payload.salary);
      if (!payload.branch_id) payload.branch_id = null;
      Object.keys(payload).forEach(k => { if (payload[k] === '') payload[k] = null; });
      payload.name = form.name; // keep required
      await API.put(`/employees/${emp.id}`, payload);
      toast.success('Employee updated');
      setEditing(false);
      onChanged && onChanged();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update');
    }
  };

  const onMoveStage = (toValue) => {
    if (toValue === 'hold' || toValue === 'rejected') {
      setStageDialog({ open: true, to: toValue, reason: '' });
    } else {
      doMove(toValue, null);
    }
  };

  const doMove = async (to, reason) => {
    try {
      const body = { to_stage: to };
      if (to === 'hold') body.hold_reason = reason;
      if (to === 'rejected') body.rejection_reason = reason;
      await API.post(`/employees/${emp.id}/transition`, body);
      toast.success(`Moved to ${STAGES.find(s => s.value === to)?.label}`);
      setStageDialog({ open: false, to: '', reason: '' });
      onChanged && onChanged();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Stage move failed');
    }
  };

  const addNote = async () => {
    if (!newNote.trim()) return;
    try {
      const { data } = await API.post(`/employees/${emp.id}/notes`, { text: newNote.trim() });
      setNotes([data, ...notes]);
      setNewNote('');
      toast.success('Note added');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to add note');
    }
  };

  const deleteNote = async (id) => {
    if (!window.confirm('Delete this note?')) return;
    try {
      await API.delete(`/employees/${emp.id}/notes/${id}`);
      setNotes(notes.filter(n => n.id !== id));
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to delete');
    }
  };

  const branchName = (id) => branches.find(b => b.id === id)?.name || '—';

  return (
    <Sheet open={open} onOpenChange={(v) => !v && onClose()}>
      <SheetContent side="right" className="w-full sm:max-w-2xl overflow-y-auto" data-testid="employee-detail-drawer">
        <SheetHeader>
          <SheetTitle className="font-heading text-xl flex items-center gap-2 flex-wrap">
            {emp.name}
            <Badge variant="outline" className="font-mono text-xs">{emp.employee_code || '—'}</Badge>
            <TypeBadge type={emp.employee_type} />
            <StageBadge stage={emp.current_stage} />
          </SheetTitle>
        </SheetHeader>

        {/* Stage transition row (prominent) */}
        <div className="mt-3 flex items-center gap-2 flex-wrap">
          <Label className="text-xs text-slate-500">Change Stage:</Label>
          <Select value="" onValueChange={onMoveStage}>
            <SelectTrigger className="h-9 w-44" data-testid="drawer-move-stage-select">
              <SelectValue placeholder="Move to..." />
            </SelectTrigger>
            <SelectContent>
              {STAGES.filter(s => s.value !== emp.current_stage).map(s => (
                <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <div className="flex-1" />
          {!editing ? (
            <Button size="sm" variant="outline" onClick={() => setEditing(true)} data-testid="drawer-edit-button">Edit</Button>
          ) : (
            <>
              <Button size="sm" variant="outline" onClick={() => setEditing(false)}>Cancel</Button>
              <Button size="sm" className="bg-blue-700 hover:bg-blue-800" onClick={saveEdit} data-testid="drawer-save-button">Save</Button>
            </>
          )}
        </div>

        <Tabs defaultValue="basic" className="mt-4">
          <TabsList className="grid grid-cols-4 md:grid-cols-7 h-auto p-1">
            <TabsTrigger value="basic" className="text-xs">Basic</TabsTrigger>
            <TabsTrigger value="employment" className="text-xs">Employment</TabsTrigger>
            <TabsTrigger value="salary" className="text-xs">Salary</TabsTrigger>
            <TabsTrigger value="history" className="text-xs">Stage History</TabsTrigger>
            <TabsTrigger value="audit" className="text-xs">Audit Log</TabsTrigger>
            <TabsTrigger value="docs" className="text-xs">Documents</TabsTrigger>
            <TabsTrigger value="notes" className="text-xs">Notes</TabsTrigger>
          </TabsList>

          {/* Basic */}
          <TabsContent value="basic" className="mt-3 space-y-3">
            {editing ? (
              <div className="grid grid-cols-2 gap-3">
                <Field label="Name *"><Input value={form.name} onChange={e => setForm({...form, name: e.target.value})} /></Field>
                <Field label="Phone"><Input value={form.phone} onChange={e => setForm({...form, phone: e.target.value})} /></Field>
                <Field label="Email" span={2}><Input value={form.email} onChange={e => setForm({...form, email: e.target.value})} /></Field>
                <Field label="Employee Type">
                  <Select value={form.employee_type} onValueChange={v => setForm({...form, employee_type: v})}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="head_office">Head Office</SelectItem>
                      <SelectItem value="franchise">Franchise</SelectItem>
                    </SelectContent>
                  </Select>
                </Field>
                <Field label="City"><Input value={form.location_city} onChange={e => setForm({...form, location_city: e.target.value})} /></Field>
                <Field label="Area"><Input value={form.location_area} onChange={e => setForm({...form, location_area: e.target.value})} /></Field>
              </div>
            ) : (
              <DetailGrid items={[
                ['Employee Code', emp.employee_code],
                ['Name', emp.name],
                ['Mobile', emp.phone],
                ['Email', emp.email],
                ['Employee Type', emp.employee_type === 'franchise' ? 'Franchise' : 'Head Office'],
                ['City', emp.location_city],
                ['Area', emp.location_area],
                ['Status', emp.status],
              ]} />
            )}
          </TabsContent>

          {/* Employment */}
          <TabsContent value="employment" className="mt-3 space-y-3">
            {editing ? (
              <div className="grid grid-cols-2 gap-3">
                <Field label="Designation">
                  <Select value={form.role || '__none'} onValueChange={v => setForm({...form, role: v === '__none' ? '' : v})}>
                    <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="__none">— None —</SelectItem>
                      {designations.map(d => <SelectItem key={d.id} value={d.name}>{d.name}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </Field>
                <Field label="Department"><Input value={form.department} onChange={e => setForm({...form, department: e.target.value})} /></Field>
                <Field label="Branch">
                  <Select value={form.branch_id || '__none'} onValueChange={v => setForm({...form, branch_id: v === '__none' ? '' : v})}>
                    <SelectTrigger><SelectValue placeholder="None" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="__none">— None —</SelectItem>
                      {branches.map(b => <SelectItem key={b.id} value={b.id}>{b.name}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </Field>
                <Field label="Joining Date"><Input type="date" value={form.joining_date} onChange={e => setForm({...form, joining_date: e.target.value})} /></Field>
              </div>
            ) : (
              <DetailGrid items={[
                ['Designation', emp.role],
                ['Department', emp.department],
                ['Branch', branchName(emp.branch_id)],
                ['Branch ID', emp.branch_id],
                ['Joining Date', fmtDate(emp.joining_date)],
                ['Current Stage', STAGES.find(s => s.value === emp.current_stage)?.label || emp.current_stage],
                ['Reporting Manager ID', emp.reporting_manager_id],
                ['Source', emp.source],
              ]} />
            )}
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
          </TabsContent>

          {/* Salary */}
          <TabsContent value="salary" className="mt-3 space-y-3">
            {editing ? (
              <Field label="Salary"><Input type="number" value={form.salary} onChange={e => setForm({...form, salary: e.target.value})} /></Field>
            ) : (
              <DetailGrid items={[
                ['Salary', emp.salary ? `₹ ${Number(emp.salary).toLocaleString()}` : '—'],
                ['Created At', fmtDate(emp.created_at)],
                ['Updated At', fmtDate(emp.updated_at)],
              ]} />
            )}
          </TabsContent>

          {/* Stage History */}
          <TabsContent value="history" className="mt-3">
            {history.length === 0 ? (
              <p className="text-sm text-slate-500 text-center py-6">No stage transitions yet</p>
            ) : (
              <div className="space-y-1.5">
                {history.map((h, i) => (
                  <div key={i} className="flex items-center justify-between p-2 border border-slate-200 rounded text-xs">
                    <span>
                      <span className="text-slate-400">{h.from_stage || 'start'}</span>
                      {' → '}
                      <strong>{STAGES.find(s => s.value === h.to_stage)?.label || h.to_stage}</strong>
                      {' · '}<span className="text-slate-500">{h.changed_by_name}</span>
                      {h.hold_reason && <span className="block text-orange-700 mt-0.5">Hold: {h.hold_reason}</span>}
                      {h.rejection_reason && <span className="block text-rose-700 mt-0.5">Reject: {h.rejection_reason}</span>}
                    </span>
                    <span className="text-slate-400 flex-shrink-0">{fmtDate(h.timestamp)}</span>
                  </div>
                ))}
              </div>
            )}
          </TabsContent>

          {/* Audit */}
          <TabsContent value="audit" className="mt-3">
            {!isSuper ? (
              <p className="text-sm text-slate-500 text-center py-6">Audit logs are visible to CEO only.</p>
            ) : audit.length === 0 ? (
              <p className="text-sm text-slate-500 text-center py-6">No audit entries yet</p>
            ) : (
              <div className="space-y-1.5 max-h-96 overflow-y-auto">
                {audit.map((a, i) => (
                  <div key={i} className="flex items-start justify-between p-2 border border-slate-200 rounded text-xs">
                    <div>
                      <strong className="text-slate-700">{a.action}</strong>
                      <span className="text-slate-500 ml-1">by {a.user_name}</span>
                      {a.details && <pre className="text-[10px] text-slate-500 mt-1 whitespace-pre-wrap">{JSON.stringify(a.details, null, 0)}</pre>}
                    </div>
                    <span className="text-slate-400 flex-shrink-0">{fmtDate(a.timestamp)}</span>
                  </div>
                ))}
              </div>
            )}
          </TabsContent>

          {/* Docs */}
          <TabsContent value="docs" className="mt-3">
            {docs.length === 0 ? (
              <p className="text-sm text-slate-500 text-center py-6">No documents uploaded</p>
            ) : (
              <div className="space-y-1.5">
                {docs.map((d, i) => (
                  <div key={i} className="flex items-center justify-between p-2 border border-slate-200 rounded text-xs">
                    <span>{d.filename || d.name || 'Document'}</span>
                    <span className="text-slate-400">{fmtDate(d.uploaded_at || d.created_at)}</span>
                  </div>
                ))}
              </div>
            )}
          </TabsContent>

          {/* Notes */}
          <TabsContent value="notes" className="mt-3 space-y-3">
            <div className="flex gap-2">
              <Textarea rows={2} placeholder="Add a note about this employee..." value={newNote} onChange={(e) => setNewNote(e.target.value)} data-testid="drawer-note-textarea" />
              <Button size="sm" className="bg-blue-700 hover:bg-blue-800" onClick={addNote} data-testid="drawer-add-note-button">Add</Button>
            </div>
            {notes.length === 0 ? (
              <p className="text-sm text-slate-500 text-center py-4">No notes yet</p>
            ) : (
              <div className="space-y-1.5 max-h-72 overflow-y-auto">
                {notes.map(n => (
                  <div key={n.id} className="p-2 border border-slate-200 rounded text-xs">
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-slate-700 whitespace-pre-wrap">{n.text}</p>
                      <Button variant="ghost" size="icon" className="h-6 w-6 text-rose-600 flex-shrink-0" onClick={() => deleteNote(n.id)}>
                        <Trash2 className="w-3 h-3" />
                      </Button>
                    </div>
                    <p className="text-[10px] text-slate-400 mt-1">{n.created_by_name} · {fmtDate(n.created_at)}</p>
                  </div>
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>

        {/* Stage reason dialog (hold/reject) */}
        <Dialog open={stageDialog.open} onOpenChange={(v) => !v && setStageDialog({ open: false, to: '', reason: '' })}>
          <DialogContent className="max-w-md">
            <DialogHeader><DialogTitle className="font-heading">Move to {STAGES.find(s => s.value === stageDialog.to)?.label}</DialogTitle></DialogHeader>
            <Textarea
              rows={4}
              placeholder={stageDialog.to === 'hold' ? 'Reason for hold...' : 'Reason for rejection...'}
              value={stageDialog.reason}
              onChange={(e) => setStageDialog({ ...stageDialog, reason: e.target.value })}
              data-testid="drawer-stage-reason"
            />
            <DialogFooter>
              <Button variant="outline" onClick={() => setStageDialog({ open: false, to: '', reason: '' })}>Cancel</Button>
              <Button
                className={stageDialog.to === 'hold' ? 'bg-orange-500 hover:bg-orange-600' : 'bg-rose-600 hover:bg-rose-700'}
                onClick={() => {
                  if (!stageDialog.reason.trim()) { toast.error('Reason required'); return; }
                  doMove(stageDialog.to, stageDialog.reason.trim());
                }}
                data-testid="drawer-confirm-stage"
              >Confirm</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </SheetContent>
    </Sheet>
  );
}

function Field({ label, span = 1, children }) {
  return (
    <div className={span === 2 ? 'col-span-2' : ''}>
      <Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">{label}</Label>
      <div className="mt-1">{children}</div>
    </div>
  );
}

function DetailGrid({ items }) {
  return (
    <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
      {items.map(([k, v], i) => (
        <div key={i}>
          <p className="text-[11px] uppercase tracking-wider text-slate-500">{k}</p>
          <p className="text-slate-900 break-words">{v || '—'}</p>
        </div>
      ))}
    </div>
  );
}

// ---------------- Main Database Page ----------------
export default function DatabasePage() {
  const { user } = useAuth();
  const isSuper = user?.role === 'CEO';
  const fileInputRef = useRef(null);

  const [employees, setEmployees] = useState([]);
  const [stats, setStats] = useState({ summary: {} });
  const [designations, setDesignations] = useState([]);
  const [branches, setBranches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [importResult, setImportResult] = useState(null);

  // Filters
  const [search, setSearch] = useState('');
  const [fEmpType, setFEmpType] = useState('all');
  const [fStage, setFStage] = useState('all');
  const [fDesignation, setFDesignation] = useState('all');
  const [fDepartment, setFDepartment] = useState('all');
  const [fBranch, setFBranch] = useState('all');
  const [fCity, setFCity] = useState('all');
  const [fStatus, setFStatus] = useState('all');

  // Add Employee dialog
  const [createOpen, setCreateOpen] = useState(false);
  const [createForm, setCreateForm] = useState({
    name: '', phone: '', email: '', employee_type: 'head_office',
    current_stage: 'new', role: '', department: '', branch_id: '',
    location_city: '', location_area: '', joining_date: '', salary: '', employee_code: '',
  });

  // Drawer
  const [drawerEmp, setDrawerEmp] = useState(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  // Inline stage transition (when row dropdown picks hold/reject)
  const [rowStageDialog, setRowStageDialog] = useState({ open: false, emp: null, to: '', reason: '' });

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

  const distinctDepartments = useMemo(() =>
    [...new Set(employees.map(e => e.department).filter(Boolean))].sort()
  , [employees]);
  const distinctCities = useMemo(() =>
    [...new Set(employees.map(e => e.location_city).filter(Boolean))].sort()
  , [employees]);

  const filtered = useMemo(() => {
    return employees.filter(e => {
      if (fEmpType !== 'all' && e.employee_type !== fEmpType) return false;
      if (fStage !== 'all' && e.current_stage !== fStage) return false;
      if (fDesignation !== 'all' && e.role !== fDesignation) return false;
      if (fDepartment !== 'all' && e.department !== fDepartment) return false;
      if (fBranch !== 'all' && e.branch_id !== fBranch) return false;
      if (fCity !== 'all' && e.location_city !== fCity) return false;
      if (fStatus !== 'all' && (e.status || 'active') !== fStatus) return false;
      if (search) {
        const q = search.toLowerCase();
        const hay = `${e.name || ''} ${e.phone || ''} ${e.email || ''} ${e.employee_code || ''} ${e.role || ''} ${e.department || ''} ${e.location_city || ''}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [employees, search, fEmpType, fStage, fDesignation, fDepartment, fBranch, fCity, fStatus]);

  // ----- Actions -----
  const handleCreate = async () => {
    if (!createForm.name.trim()) { toast.error('Name is required'); return; }
    try {
      const payload = { ...createForm };
      if (payload.salary === '') payload.salary = null;
      else if (payload.salary) payload.salary = parseFloat(payload.salary);
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

  const rowMoveStage = (emp, to) => {
    if (to === 'hold' || to === 'rejected') {
      setRowStageDialog({ open: true, emp, to, reason: '' });
    } else {
      confirmRowMove(emp, to, null);
    }
  };

  const confirmRowMove = async (emp, to, reason) => {
    try {
      const body = { to_stage: to };
      if (to === 'hold') body.hold_reason = reason;
      if (to === 'rejected') body.rejection_reason = reason;
      await API.post(`/employees/${emp.id}/transition`, body);
      toast.success(`${emp.name}: moved to ${STAGES.find(s => s.value === to)?.label}`);
      setRowStageDialog({ open: false, emp: null, to: '', reason: '' });
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Stage move failed');
    }
  };

  const openDrawer = (emp) => {
    setDrawerEmp(emp);
    setDrawerOpen(true);
  };

  const downloadTemplate = async () => {
    try {
      const res = await API.get('/employees/excel/template', { responseType: 'blob' });
      triggerDownload(res.data, 'employee_template.xlsx');
      toast.success('Template downloaded');
    } catch { toast.error('Failed to download template'); }
  };

  const exportExcel = async () => {
    try {
      const params = {};
      if (fEmpType !== 'all') params.employee_type = fEmpType;
      if (fStage !== 'all') params.current_stage = fStage;
      const res = await API.get('/employees/excel/export', { params, responseType: 'blob' });
      triggerDownload(res.data, `employees_${Date.now()}.xlsx`);
      toast.success('Export downloaded');
    } catch { toast.error('Failed to export'); }
  };

  const triggerDownload = (data, filename) => {
    const url = window.URL.createObjectURL(new Blob([data]));
    const link = document.createElement('a');
    link.href = url; link.setAttribute('download', filename);
    document.body.appendChild(link); link.click(); link.remove();
  };

  const handleImport = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await API.post('/employees/excel/import', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
      setImportResult(res.data);
      toast.success(`Imported ${res.data.created} employees (${res.data.skipped} skipped)`);
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Import failed');
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const summary = stats.summary || {};

  if (loading) return <div className="flex items-center justify-center h-64 text-slate-500">Loading...</div>;

  return (
    <div className="space-y-4" data-testid="database-page">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-xl md:text-2xl font-heading font-semibold text-slate-900 flex items-center gap-2">
            <Users className="w-5 h-5" /> Employee Database
          </h1>
          <p className="text-sm text-slate-500">{filtered.length} of {employees.length} employees</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="outline" size="sm" onClick={downloadTemplate} data-testid="download-template-button">
            <FileDown className="w-3.5 h-3.5 mr-1" /> Template
          </Button>
          <Button variant="outline" size="sm" onClick={() => fileInputRef.current?.click()} data-testid="excel-import-button">
            <Upload className="w-3.5 h-3.5 mr-1" /> Import
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

      {/* Search + Filters */}
      <Card className="border-slate-200 shadow-none">
        <CardContent className="p-3 space-y-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <Input
              placeholder="Search by name, phone, email, employee code, designation, department..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 h-10"
              data-testid="employee-search-input"
            />
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-2">
            <Select value={fEmpType} onValueChange={setFEmpType}>
              <SelectTrigger className="h-9 text-xs" data-testid="filter-employee-type"><SelectValue placeholder="Type" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="head_office">Head Office</SelectItem>
                <SelectItem value="franchise">Franchise</SelectItem>
              </SelectContent>
            </Select>
            <Select value={fStage} onValueChange={setFStage}>
              <SelectTrigger className="h-9 text-xs" data-testid="filter-stage"><SelectValue placeholder="Stage" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Stages</SelectItem>
                {STAGES.map(s => <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>)}
              </SelectContent>
            </Select>
            <Select value={fDesignation} onValueChange={setFDesignation}>
              <SelectTrigger className="h-9 text-xs" data-testid="filter-designation"><SelectValue placeholder="Designation" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Designations</SelectItem>
                {designations.map(d => <SelectItem key={d.id} value={d.name}>{d.name}</SelectItem>)}
              </SelectContent>
            </Select>
            <Select value={fDepartment} onValueChange={setFDepartment}>
              <SelectTrigger className="h-9 text-xs" data-testid="filter-department"><SelectValue placeholder="Department" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Departments</SelectItem>
                {distinctDepartments.map(d => <SelectItem key={d} value={d}>{d}</SelectItem>)}
              </SelectContent>
            </Select>
            <Select value={fBranch} onValueChange={setFBranch}>
              <SelectTrigger className="h-9 text-xs" data-testid="filter-branch"><SelectValue placeholder="Branch" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Branches</SelectItem>
                {branches.map(b => <SelectItem key={b.id} value={b.id}>{b.name}</SelectItem>)}
              </SelectContent>
            </Select>
            <Select value={fCity} onValueChange={setFCity}>
              <SelectTrigger className="h-9 text-xs" data-testid="filter-city"><SelectValue placeholder="City" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Cities</SelectItem>
                {distinctCities.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
              </SelectContent>
            </Select>
            <Select value={fStatus} onValueChange={setFStatus}>
              <SelectTrigger className="h-9 text-xs" data-testid="filter-status"><SelectValue placeholder="Status" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="left">Left</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <Card className="border-slate-200 shadow-none">
        <CardContent className="p-0 overflow-x-auto">
          <Table data-testid="employee-table">
            <TableHeader>
              <TableRow className="bg-slate-50">
                <TableHead className="font-semibold text-xs uppercase tracking-wider text-slate-600">Name</TableHead>
                <TableHead className="font-semibold text-xs uppercase tracking-wider text-slate-600">Mobile</TableHead>
                <TableHead className="font-semibold text-xs uppercase tracking-wider text-slate-600">Email</TableHead>
                <TableHead className="font-semibold text-xs uppercase tracking-wider text-slate-600">Type</TableHead>
                <TableHead className="font-semibold text-xs uppercase tracking-wider text-slate-600">Stage</TableHead>
                <TableHead className="font-semibold text-xs uppercase tracking-wider text-slate-600">Designation</TableHead>
                <TableHead className="font-semibold text-xs uppercase tracking-wider text-slate-600">Department</TableHead>
                <TableHead className="font-semibold text-xs uppercase tracking-wider text-slate-600">Branch ID</TableHead>
                <TableHead className="font-semibold text-xs uppercase tracking-wider text-slate-600">City</TableHead>
                <TableHead className="font-semibold text-xs uppercase tracking-wider text-slate-600">Area</TableHead>
                <TableHead className="font-semibold text-xs uppercase tracking-wider text-slate-600">Joining</TableHead>
                <TableHead className="font-semibold text-xs uppercase tracking-wider text-slate-600 text-right">Salary</TableHead>
                <TableHead className="font-semibold text-xs uppercase tracking-wider text-slate-600">Code</TableHead>
                <TableHead className="font-semibold text-xs uppercase tracking-wider text-slate-600">Status</TableHead>
                <TableHead className="font-semibold text-xs uppercase tracking-wider text-slate-600">Created</TableHead>
                <TableHead className="font-semibold text-xs uppercase tracking-wider text-slate-600 text-center">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={16} className="text-center py-10 text-slate-500 text-sm">No employees match these filters</TableCell>
                </TableRow>
              ) : filtered.map(e => (
                <TableRow key={e.id} className="hover:bg-slate-50" data-testid={`employee-row-${e.id}`}>
                  <TableCell className="font-medium text-slate-900 whitespace-nowrap">{e.name}</TableCell>
                  <TableCell className="text-slate-600 whitespace-nowrap text-xs">{e.phone || '—'}</TableCell>
                  <TableCell className="text-slate-600 text-xs">{e.email || '—'}</TableCell>
                  <TableCell><TypeBadge type={e.employee_type} /></TableCell>
                  <TableCell>
                    <Select value="" onValueChange={(v) => rowMoveStage(e, v)}>
                      <SelectTrigger className="h-7 w-32 text-xs" data-testid={`row-move-stage-${e.id}`}>
                        <SelectValue placeholder={<StageBadge stage={e.current_stage} />} />
                      </SelectTrigger>
                      <SelectContent>
                        {STAGES.filter(s => s.value !== e.current_stage).map(s => (
                          <SelectItem key={s.value} value={s.value} className="text-xs">{s.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </TableCell>
                  <TableCell className="text-slate-600 text-xs whitespace-nowrap">{e.role || '—'}</TableCell>
                  <TableCell className="text-slate-600 text-xs whitespace-nowrap">{e.department || '—'}</TableCell>
                  <TableCell className="text-slate-600 text-xs">{e.branch_id ? (branches.find(b => b.id === e.branch_id)?.name || e.branch_id.slice(0, 6)) : '—'}</TableCell>
                  <TableCell className="text-slate-600 text-xs">{e.location_city || '—'}</TableCell>
                  <TableCell className="text-slate-600 text-xs">{e.location_area || '—'}</TableCell>
                  <TableCell className="text-slate-600 text-xs whitespace-nowrap">{fmtDate(e.joining_date)}</TableCell>
                  <TableCell className="text-slate-600 text-xs text-right">{e.salary ? `₹${Number(e.salary).toLocaleString()}` : '—'}</TableCell>
                  <TableCell className="font-mono text-xs">{e.employee_code || '—'}</TableCell>
                  <TableCell>
                    <Badge variant="outline" className={`text-[10px] ${e.status === 'left' ? 'text-rose-700 border-rose-200' : 'text-emerald-700 border-emerald-200'}`}>
                      {e.status || 'active'}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-slate-600 text-xs whitespace-nowrap">{fmtDate(e.created_at)}</TableCell>
                  <TableCell className="text-center">
                    <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => openDrawer(e)} data-testid={`view-employee-${e.id}`}>
                      <Eye className="w-3.5 h-3.5" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Create dialog */}
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

      {/* Row stage transition (hold/reject) */}
      <Dialog open={rowStageDialog.open} onOpenChange={(v) => !v && setRowStageDialog({ open: false, emp: null, to: '', reason: '' })}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="font-heading">Move to {STAGES.find(s => s.value === rowStageDialog.to)?.label}</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-slate-600">Reason for <strong>{rowStageDialog.emp?.name}</strong>:</p>
          <Textarea
            rows={4}
            value={rowStageDialog.reason}
            onChange={(e) => setRowStageDialog({ ...rowStageDialog, reason: e.target.value })}
            data-testid="row-stage-reason-textarea"
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setRowStageDialog({ open: false, emp: null, to: '', reason: '' })}>Cancel</Button>
            <Button
              className={rowStageDialog.to === 'hold' ? 'bg-orange-500 hover:bg-orange-600' : 'bg-rose-600 hover:bg-rose-700'}
              onClick={() => {
                if (!rowStageDialog.reason.trim()) { toast.error('Reason required'); return; }
                confirmRowMove(rowStageDialog.emp, rowStageDialog.to, rowStageDialog.reason.trim());
              }}
              data-testid="row-confirm-stage-move"
            >Confirm</Button>
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

      {/* Detail drawer */}
      <EmployeeDetailDrawer
        open={drawerOpen}
        emp={drawerEmp}
        onClose={() => setDrawerOpen(false)}
        onChanged={fetchData}
        designations={designations}
        branches={branches}
        isSuper={isSuper}
      />
    </div>
  );
}

function CounterCard({ label, value, color, testid, icon }) {
  return (
    <Card className={`border-slate-200 shadow-none ${color}`} data-testid={testid}>
      <CardContent className="p-3">
        <p className="text-xs font-medium uppercase tracking-wider opacity-70 flex items-center gap-1">{icon}{label}</p>
        <p className="text-2xl font-heading font-semibold mt-1">{value}</p>
      </CardContent>
    </Card>
  );
}
