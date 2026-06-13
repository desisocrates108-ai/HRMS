import { useState, useEffect } from 'react';
import API from '@/api';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import { Briefcase, Plus, Pencil, Trash2, Search } from 'lucide-react';
import { toast } from 'sonner';

export default function DesignationsPage() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({ name: '', office_type: 'head_office', department: '', description: '', active: true });

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const { data } = await API.get('/designations');
      setItems(data);
    } catch { toast.error('Failed to load designations'); }
    finally { setLoading(false); }
  };

  const openCreate = () => {
    setEditing(null);
    setForm({ name: '', office_type: 'head_office', department: '', description: '', active: true });
    setDialogOpen(true);
  };

  const openEdit = (d) => {
    setEditing(d);
    setForm({
      name: d.name || '',
      office_type: d.office_type || 'head_office',
      department: d.department || '',
      description: d.description || '',
      active: d.active !== false,
    });
    setDialogOpen(true);
  };

  const submit = async () => {
    if (!form.name.trim()) { toast.error('Name is required'); return; }
    if (!form.office_type) { toast.error('Office Type is required'); return; }
    try {
      if (editing) {
        await API.put(`/designations/${editing.id}`, form);
        toast.success('Designation updated');
      } else {
        await API.post('/designations', {
          name: form.name,
          office_type: form.office_type,
          department: form.department || null,
          description: form.description || null,
        });
        toast.success('Designation created');
      }
      setDialogOpen(false);
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save');
    }
  };

  const remove = async (d) => {
    if (!window.confirm(`Delete designation "${d.name}"? This cannot be undone.`)) return;
    try {
      await API.delete(`/designations/${d.id}`);
      toast.success('Designation deleted');
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to delete');
    }
  };

  const toggleActive = async (d) => {
    try {
      await API.put(`/designations/${d.id}`, { active: !d.active });
      toast.success(`Designation ${!d.active ? 'activated' : 'deactivated'}`);
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update');
    }
  };

  const filtered = items.filter(d =>
    !search ||
    d.name?.toLowerCase().includes(search.toLowerCase()) ||
    d.department?.toLowerCase().includes(search.toLowerCase())
  );

  if (loading) return <div className="flex items-center justify-center h-64 text-slate-500">Loading...</div>;

  return (
    <div className="space-y-4" data-testid="designations-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl md:text-2xl font-heading font-semibold text-slate-900 flex items-center gap-2">
            <Briefcase className="w-5 h-5" /> Designations
          </h1>
          <p className="text-sm text-slate-500">{items.length} designation{items.length !== 1 ? 's' : ''} · used in Lead forms and the Hirings module</p>
        </div>
        <Button onClick={openCreate} className="bg-blue-700 hover:bg-blue-800 active:scale-[0.98]" data-testid="create-designation-button">
          <Plus className="w-4 h-4 mr-1" /> Add Designation
        </Button>
      </div>

      <Card className="border-slate-200 shadow-none">
        <CardContent className="p-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <Input
              placeholder="Search by name or department..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 h-10"
              data-testid="designation-search-input"
            />
          </div>
        </CardContent>
      </Card>

      {filtered.length === 0 ? (
        <div className="text-center py-12 text-slate-500 text-sm">No designations found</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {filtered.map(d => (
            <Card key={d.id} className="border-slate-200 shadow-none hover:-translate-y-0.5 hover:shadow-md transition-all duration-200" data-testid={`designation-card-${d.id}`}>
              <CardContent className="p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="font-medium text-slate-900 truncate">{d.name}</p>
                      <Badge
                        className={`text-[10px] border-0 ${d.office_type === 'franchise' ? 'bg-violet-100 text-violet-700' : 'bg-blue-100 text-blue-700'}`}
                        data-testid={`designation-office-type-${d.id}`}
                      >
                        {d.office_type === 'franchise' ? 'Franchise' : 'Head Office'}
                      </Badge>
                      {!d.active && <Badge variant="outline" className="text-xs text-slate-500">Inactive</Badge>}
                    </div>
                    {d.department && <p className="text-xs text-slate-500 mt-0.5">Dept: {d.department}</p>}
                    {d.description && <p className="text-xs text-slate-500 mt-1">{d.description}</p>}
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <Switch
                      checked={d.active}
                      onCheckedChange={() => toggleActive(d)}
                      data-testid={`toggle-active-${d.id}`}
                    />
                    <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => openEdit(d)} data-testid={`edit-designation-${d.id}`}>
                      <Pencil className="w-3.5 h-3.5" />
                    </Button>
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-rose-600 hover:text-rose-700" onClick={() => remove(d)} data-testid={`delete-designation-${d.id}`}>
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader><DialogTitle className="font-heading">{editing ? 'Edit Designation' : 'Add Designation'}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div>
              <Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Name *</Label>
              <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g., Service Advisor" className="mt-1" data-testid="designation-name-input" />
            </div>
            <div>
              <Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Office Type *</Label>
              <select
                value={form.office_type}
                onChange={(e) => setForm({ ...form, office_type: e.target.value })}
                className="mt-1 w-full border border-slate-200 rounded-md px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                data-testid="designation-office-type-select"
              >
                <option value="head_office">Head Office</option>
                <option value="franchise">Franchise</option>
              </select>
              <p className="text-[11px] text-slate-400 mt-1">Determines which Hiring section this designation shows up under.</p>
            </div>
            <div>
              <Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Department</Label>
              <Input value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })} placeholder="Optional" className="mt-1" data-testid="designation-department-input" />
            </div>
            <div>
              <Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Description</Label>
              <Textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="Optional" className="mt-1" rows={3} data-testid="designation-description-input" />
            </div>
            {editing && (
              <div className="flex items-center justify-between border-t pt-3">
                <Label className="text-sm">Active</Label>
                <Switch checked={form.active} onCheckedChange={(v) => setForm({ ...form, active: v })} data-testid="designation-active-switch" />
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button onClick={submit} className="bg-blue-700 hover:bg-blue-800" data-testid="save-designation-button">
              {editing ? 'Save Changes' : 'Add Designation'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
