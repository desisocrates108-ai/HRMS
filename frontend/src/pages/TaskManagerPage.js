import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import API from '@/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { CheckSquare, Clock, CheckCircle, Circle, AlertTriangle, Plus, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import DateFilter from '@/components/DateFilter';

const SUPER_ROLES = ['CEO', 'HR'];
const MANAGER_ROLES = ['Marketing Manager', 'Operations Manager', 'Sales Manager', 'Accounts Manager'];

const STATUS_OPTIONS = ['pending', 'in_progress', 'completed'];
const PRIORITY_COLORS = {
  low: 'bg-slate-100 text-slate-700',
  medium: 'bg-blue-100 text-blue-700',
  high: 'bg-amber-100 text-amber-700',
  urgent: 'bg-rose-100 text-rose-700',
};
const STATUS_META = {
  pending: { icon: Circle, color: 'text-amber-500' },
  in_progress: { icon: Clock, color: 'text-blue-600' },
  completed: { icon: CheckCircle, color: 'text-emerald-600' },
  overdue: { icon: AlertTriangle, color: 'text-rose-600' },
};

export default function TaskManagerPage() {
  const { user } = useAuth();
  const isSuper = SUPER_ROLES.includes(user?.role);
  const canAssign = true; // All users can assign tasks now

  const [tasks, setTasks] = useState([]);
  const [assignableUsers, setAssignableUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [scope, setScope] = useState('all'); // my | assigned_by_me | all
  const [statusFilter, setStatusFilter] = useState('all');
  const [dateRange, setDateRange] = useState({ preset: '30d' });
  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState({ title: '', description: '', assigned_to: '', priority: 'medium', due_date: '' });
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (scope !== 'all') params.set('scope', scope);
      if (statusFilter !== 'all') params.set('status', statusFilter);
      if (dateRange.date_from) params.set('date_from', dateRange.date_from);
      if (dateRange.date_to) params.set('date_to', dateRange.date_to);
      const { data } = await API.get(`/tasks?${params.toString()}`);
      setTasks(data);
      if (canAssign && assignableUsers.length === 0) {
        const { data: u } = await API.get('/tasks/assignable-users');
        setAssignableUsers(u);
      }
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Failed to load tasks');
    } finally { setLoading(false); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scope, statusFilter, dateRange, canAssign]);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async () => {
    if (!form.title || !form.assigned_to) { toast.error('Title and assignee required'); return; }
    setSaving(true);
    try {
      const payload = { ...form };
      if (!payload.due_date) delete payload.due_date;
      await API.post('/tasks', payload);
      toast.success('Task assigned');
      setCreateOpen(false);
      setForm({ title: '', description: '', assigned_to: '', priority: 'medium', due_date: '' });
      load();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Failed to create task');
    } finally { setSaving(false); }
  };

  const updateStatus = async (taskId, status) => {
    try {
      await API.put(`/tasks/${taskId}`, { status });
      load();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Failed to update');
    }
  };

  const handleDelete = async () => {
    try {
      await API.delete(`/tasks/${deleteTarget.id}`);
      toast.success('Task deleted');
      setDeleteTarget(null);
      load();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Delete failed');
    }
  };

  if (loading) return <div className="flex items-center justify-center h-64 text-slate-500">Loading...</div>;

  const scopeTabs = isSuper
    ? [['all', 'All Tasks'], ['my', 'My Tasks'], ['assigned_by_me', 'Assigned by Me']]
    : isManager
      ? [['my', 'My + Team'], ['assigned_by_me', 'Assigned by Me']]
      : [['my', 'My Tasks']];

  return (
    <div className="space-y-4" data-testid="task-manager-page">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl md:text-2xl font-heading font-semibold text-slate-900">Task Manager</h1>
          <p className="text-sm text-slate-500">{tasks.length} task{tasks.length === 1 ? '' : 's'}</p>
        </div>
        <div className="flex items-center gap-2">
          <DateFilter value={dateRange} onChange={setDateRange} testId="task-date-filter" />
          {canAssign && (
            <Button onClick={() => setCreateOpen(true)} className="bg-blue-700 hover:bg-blue-800" data-testid="create-task-button">
              <Plus className="w-4 h-4 mr-1" /> New Task
            </Button>
          )}
        </div>
      </div>

      <div className="flex items-center gap-3 flex-wrap">
        <Tabs value={scope} onValueChange={setScope}>
          <TabsList>{scopeTabs.map(([k, l]) => <TabsTrigger key={k} value={k} data-testid={`scope-${k}`}>{l}</TabsTrigger>)}</TabsList>
        </Tabs>
        <Tabs value={statusFilter} onValueChange={setStatusFilter}>
          <TabsList>
            <TabsTrigger value="all" data-testid="status-all">All</TabsTrigger>
            <TabsTrigger value="pending" data-testid="status-pending">Pending</TabsTrigger>
            <TabsTrigger value="in_progress" data-testid="status-in_progress">In Progress</TabsTrigger>
            <TabsTrigger value="overdue" data-testid="status-overdue">Overdue</TabsTrigger>
            <TabsTrigger value="completed" data-testid="status-completed">Done</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {tasks.length === 0 ? (
        <div className="text-center py-12 text-slate-500 text-sm">No tasks in this view</div>
      ) : (
        <div className="space-y-2">
          {tasks.map((t) => {
            const meta = STATUS_META[t.status] || STATUS_META.pending;
            const Icon = meta.icon;
            const canUpdate = isSuper || t.assigned_to === user?.id || t.created_by === user?.id;
            const canDelete = isSuper || t.created_by === user?.id;
            return (
              <Card key={t.id} className="border-slate-200 shadow-none" data-testid={`task-row-${t.id}`}>
                <CardContent className="p-3 md:p-4">
                  <div className="flex items-start justify-between gap-3 flex-wrap md:flex-nowrap">
                    <div className="flex items-start gap-3 min-w-0 flex-1">
                      <Icon className={`w-5 h-5 mt-0.5 flex-shrink-0 ${meta.color}`} />
                      <div className="min-w-0 flex-1">
                        <p className={`font-medium text-sm ${t.status === 'completed' ? 'line-through text-slate-400' : 'text-slate-900'}`}>{t.title}</p>
                        {t.description && <p className="text-xs text-slate-500 mt-0.5">{t.description}</p>}
                        <div className="flex flex-wrap items-center gap-2 mt-1">
                          <Badge className={`${PRIORITY_COLORS[t.priority]} border-0 text-[10px]`}>{(t.priority || 'medium').toUpperCase()}</Badge>
                          <span className="text-xs text-slate-500">To: {t.assigned_to_name}</span>
                          <span className="text-xs text-slate-400">By: {t.created_by_name}</span>
                          {t.due_date && <span className="text-xs text-slate-400">Due: {new Date(t.due_date).toLocaleDateString()}</span>}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      {canUpdate && (
                        <Select value={t.status === 'overdue' ? 'pending' : t.status} onValueChange={(v) => updateStatus(t.id, v)}>
                          <SelectTrigger className="w-32 h-8 text-xs" data-testid={`task-status-${t.id}`}><SelectValue /></SelectTrigger>
                          <SelectContent>{STATUS_OPTIONS.map(s => <SelectItem key={s} value={s}>{s.replace('_', ' ')}</SelectItem>)}</SelectContent>
                        </Select>
                      )}
                      {canDelete && (
                        <Button variant="ghost" size="sm" className="text-rose-600 h-8 w-8 p-0" onClick={() => setDeleteTarget(t)} data-testid={`task-delete-${t.id}`}>
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Create dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle className="font-heading">New Task</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div><Label className="text-xs font-semibold uppercase text-slate-500">Title</Label><Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} className="mt-1" data-testid="task-title-input" /></div>
            <div><Label className="text-xs font-semibold uppercase text-slate-500">Description</Label><Textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={3} className="mt-1" /></div>
            <div>
              <Label className="text-xs font-semibold uppercase text-slate-500">Assignee</Label>
              <Select value={form.assigned_to} onValueChange={(v) => setForm({ ...form, assigned_to: v })}>
                <SelectTrigger className="mt-1" data-testid="task-assignee-select"><SelectValue placeholder="Select user" /></SelectTrigger>
                <SelectContent>{assignableUsers.map(u => <SelectItem key={u.id} value={u.id}>{u.name} ({u.role})</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs font-semibold uppercase text-slate-500">Priority</Label>
                <Select value={form.priority} onValueChange={(v) => setForm({ ...form, priority: v })}>
                  <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                  <SelectContent>{['low', 'medium', 'high', 'urgent'].map(p => <SelectItem key={p} value={p}>{p}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs font-semibold uppercase text-slate-500">Due Date</Label>
                <Input type="date" value={form.due_date} onChange={(e) => setForm({ ...form, due_date: e.target.value })} className="mt-1" />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>Cancel</Button>
            <Button onClick={handleCreate} disabled={saving} className="bg-blue-700 hover:bg-blue-800" data-testid="task-save-button">{saving ? 'Saving...' : 'Assign'}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete dialog */}
      <Dialog open={!!deleteTarget} onOpenChange={(o) => !o && setDeleteTarget(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="font-heading text-rose-700">Delete Task?</DialogTitle>
            <DialogDescription>Delete "<strong>{deleteTarget?.title}</strong>"? This cannot be undone.</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>Cancel</Button>
            <Button onClick={handleDelete} className="bg-rose-600 hover:bg-rose-700">Delete</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
