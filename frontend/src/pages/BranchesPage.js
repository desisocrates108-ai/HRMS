import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import API from '@/api';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Building2, Plus, MapPin, Calendar, Edit, Trash2, Save } from 'lucide-react';
import { toast } from 'sonner';

const EDIT_ROLES = [
  'CEO', 'HR',
  'Marketing Manager', 'Operations Manager', 'Sales Manager', 'Accounts Manager',
  'Sr HR', 'Jr HR',
];
const DELETE_ROLES = ['CEO', 'HR', 'Sr HR', 'Jr HR'];

export default function BranchesPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const canEdit = EDIT_ROLES.includes(user?.role);
  const canDelete = DELETE_ROLES.includes(user?.role);

  const [branches, setBranches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all'); // all | upcoming | active
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    name: '', city: '', area: '',
    tentative_opening_date: '', actual_opening_date: '',
  });

  useEffect(() => { fetchBranches(); }, []);

  const fetchBranches = async () => {
    try {
      const { data } = await API.get('/branches');
      setBranches(data);
    } catch { toast.error('Failed to load branches'); }
    finally { setLoading(false); }
  };

  const resetForm = () => {
    setForm({ name: '', city: '', area: '', tentative_opening_date: '', actual_opening_date: '' });
    setEditingId(null);
  };

  const openCreate = () => { resetForm(); setDialogOpen(true); };

  const openEdit = (b) => {
    setEditingId(b.id);
    setForm({
      name: b.name || '',
      city: b.city || '',
      area: b.area || '',
      tentative_opening_date: b.tentative_opening_date || '',
      actual_opening_date: b.actual_opening_date || '',
    });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    if (!form.name?.trim() || !form.city?.trim() || !form.area?.trim()) {
      toast.error('Name, City and Area are required');
      return;
    }
    setSaving(true);
    try {
      const payload = { ...form };
      if (!payload.tentative_opening_date) payload.tentative_opening_date = null;
      if (!payload.actual_opening_date) payload.actual_opening_date = null;
      if (editingId) {
        await API.put(`/branches/${editingId}`, payload);
        toast.success('Branch updated');
      } else {
        await API.post('/branches', payload);
        toast.success('Branch created');
      }
      setDialogOpen(false);
      resetForm();
      fetchBranches();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save branch');
    } finally { setSaving(false); }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await API.delete(`/branches/${deleteTarget.id}`);
      toast.success('Branch deleted');
      setDeleteTarget(null);
      fetchBranches();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to delete');
    }
  };

  if (loading) return <div className="flex items-center justify-center h-64 text-slate-500">Loading...</div>;

  const upcoming = branches.filter((b) => b.status === 'upcoming');
  const active = branches.filter((b) => b.status === 'active');
  const filtered = filter === 'upcoming' ? upcoming : filter === 'active' ? active : branches;

  return (
    <div className="space-y-4" data-testid="branches-page">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-xl md:text-2xl font-heading font-semibold text-slate-900">Branches</h1>
          <p className="text-sm text-slate-500">{branches.length} total · {upcoming.length} upcoming · {active.length} active</p>
        </div>
        {canEdit && (
          <Button onClick={openCreate} className="bg-blue-700 hover:bg-blue-800 active:scale-[0.98]" data-testid="create-branch-button">
            <Plus className="w-4 h-4 mr-1" /> Add Branch
          </Button>
        )}
      </div>

      <Tabs value={filter} onValueChange={setFilter}>
        <TabsList className="grid w-full grid-cols-3 md:w-96">
          <TabsTrigger value="all" data-testid="branch-filter-all">All ({branches.length})</TabsTrigger>
          <TabsTrigger value="upcoming" data-testid="branch-filter-upcoming">Upcoming ({upcoming.length})</TabsTrigger>
          <TabsTrigger value="active" data-testid="branch-filter-active">Active ({active.length})</TabsTrigger>
        </TabsList>
      </Tabs>

      {filtered.length === 0 ? (
        <div className="text-center py-12 text-slate-500">No branches match this filter</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {filtered.map((b) => (
            <Card
              key={b.id}
              onClick={() => navigate(`/branches/${b.id}`)}
              className="border-slate-200 shadow-none hover:-translate-y-0.5 hover:shadow-md hover:border-blue-300 transition-all duration-200 cursor-pointer"
              data-testid={`branch-card-${b.id}`}
            >
              <CardContent className="p-4">
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center flex-shrink-0">
                    <Building2 className="w-5 h-5 text-blue-700" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <p className="font-medium text-slate-900 truncate">{b.name}</p>
                      <Badge variant="outline" className={`text-xs flex-shrink-0 ${b.status === 'upcoming' ? 'text-amber-600 border-amber-200' : 'text-emerald-600 border-emerald-200'}`}>
                        {b.status}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-1 mt-1 text-sm text-slate-500">
                      <MapPin className="w-3 h-3" />
                      <span className="truncate">{b.city}, {b.area}</span>
                    </div>
                    {(b.tentative_opening_date || b.actual_opening_date) && (
                      <div className="flex items-center gap-1 mt-1 text-xs text-slate-400">
                        <Calendar className="w-3 h-3" />
                        <span>
                          {b.actual_opening_date ? `Opened ${b.actual_opening_date}` : `Tentative ${b.tentative_opening_date}`}
                        </span>
                      </div>
                    )}
                    {(canEdit || canDelete) && (
                      <div className="flex gap-2 mt-3 pt-3 border-t border-slate-100">
                        {canEdit && (
                          <Button size="sm" variant="outline" onClick={(e) => { e.stopPropagation(); openEdit(b); }} className="h-8 text-xs flex-1" data-testid={`edit-branch-${b.id}`}>
                            <Edit className="w-3 h-3 mr-1" /> Edit
                          </Button>
                        )}
                        {canDelete && (
                          <Button size="sm" variant="outline" onClick={(e) => { e.stopPropagation(); setDeleteTarget(b); }} className="h-8 text-xs text-rose-600 hover:text-rose-700 hover:bg-rose-50" data-testid={`delete-branch-${b.id}`}>
                            <Trash2 className="w-3 h-3 mr-1" /> Delete
                          </Button>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create / Edit dialog */}
      <Dialog open={dialogOpen} onOpenChange={(o) => { if (!o) resetForm(); setDialogOpen(o); }}>
        <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="font-heading">{editingId ? 'Edit Branch' : 'Add New Branch'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Branch Name</Label>
              <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Servall Koramangala" className="mt-1" data-testid="branch-name-input" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">City</Label>
                <Input value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} placeholder="Bangalore" className="mt-1" data-testid="branch-city-input" />
              </div>
              <div>
                <Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Area</Label>
                <Input value={form.area} onChange={(e) => setForm({ ...form, area: e.target.value })} placeholder="Koramangala" className="mt-1" data-testid="branch-area-input" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Tentative Opening</Label>
                <Input type="date" value={form.tentative_opening_date} onChange={(e) => setForm({ ...form, tentative_opening_date: e.target.value })} className="mt-1" data-testid="branch-tentative-date" />
              </div>
              <div>
                <Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Actual Opening</Label>
                <Input type="date" value={form.actual_opening_date} onChange={(e) => setForm({ ...form, actual_opening_date: e.target.value })} className="mt-1" data-testid="branch-actual-date" />
              </div>
            </div>
            <p className="text-xs text-slate-400">Set "Actual Opening" to mark this branch as Active. Otherwise it stays Upcoming.</p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { resetForm(); setDialogOpen(false); }} data-testid="branch-cancel-button">Cancel</Button>
            <Button onClick={handleSave} disabled={saving} className="bg-blue-700 hover:bg-blue-800" data-testid="save-branch-button">
              <Save className="w-4 h-4 mr-1" /> {saving ? 'Saving...' : editingId ? 'Update' : 'Save Branch'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete confirmation */}
      <Dialog open={!!deleteTarget} onOpenChange={(o) => !o && setDeleteTarget(null)}>
        <DialogContent className="max-w-md" data-testid="delete-branch-dialog">
          <DialogHeader>
            <DialogTitle className="font-heading text-rose-700">Delete Branch?</DialogTitle>
            <DialogDescription>
              This action cannot be undone. All historical data linked to <strong>{deleteTarget?.name}</strong> will be preserved, but the branch will be removed from the active list.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>Cancel</Button>
            <Button onClick={handleDelete} className="bg-rose-600 hover:bg-rose-700" data-testid="confirm-delete-branch">
              <Trash2 className="w-4 h-4 mr-1" /> Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
