import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import API from '@/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { UserCog, Plus, Pencil, Trash2, KeyRound, Shield } from 'lucide-react';
import { toast } from 'sonner';

const LEVEL_COLORS = {
  super: 'bg-violet-100 text-violet-700',
  manager: 'bg-blue-100 text-blue-700',
  executor: 'bg-emerald-100 text-emerald-700',
};

export default function UsersPage() {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [branches, setBranches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [resetOpen, setResetOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);
  const [form, setForm] = useState({ email: '', password: '', name: '', role: '', department: '' });
  const [editForm, setEditForm] = useState({ name: '', email: '', role: '', department: '', branch_id: '', is_active: true });
  const [newPassword, setNewPassword] = useState('');

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const [usersRes, rolesRes, branchesRes] = await Promise.all([
        API.get('/users'), API.get('/users/roles'), API.get('/branches')
      ]);
      setUsers(usersRes.data);
      setRoles(rolesRes.data);
      setBranches(branchesRes.data);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to load data');
    }
    finally { setLoading(false); }
  };

  const handleCreate = async () => {
    try {
      const payload = { ...form };
      await API.post('/users', payload);
      toast.success('User created');
      setCreateOpen(false);
      setForm({ email: '', password: '', name: '', role: '', department: '' });
      fetchData();
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed to create user'); }
  };

  const openEdit = (u) => {
    setSelectedUser(u);
    setEditForm({ name: u.name, email: u.email, role: u.role, department: u.department || '', branch_id: u.branch_id || '', is_active: u.is_active !== false });
    setEditOpen(true);
  };

  const handleEdit = async () => {
    try {
      const payload = {};
      if (editForm.name !== selectedUser.name) payload.name = editForm.name;
      if (editForm.email !== selectedUser.email) payload.email = editForm.email;
      if (editForm.role !== selectedUser.role) payload.role = editForm.role;
      if (editForm.department !== (selectedUser.department || '')) payload.department = editForm.department;
      if (editForm.branch_id !== (selectedUser.branch_id || '')) payload.branch_id = editForm.branch_id || null;
      if (editForm.is_active !== (selectedUser.is_active !== false)) payload.is_active = editForm.is_active;
      if (Object.keys(payload).length === 0) { toast.info('No changes to save'); return; }
      await API.put(`/users/${selectedUser.id}`, payload);
      toast.success('User updated');
      setEditOpen(false);
      fetchData();
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed to update user'); }
  };

  const handleResetPassword = async () => {
    try {
      await API.post(`/users/${selectedUser.id}/reset-password`, { new_password: newPassword });
      toast.success('Password reset successful');
      setResetOpen(false);
      setNewPassword('');
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed to reset password'); }
  };

  const handleDelete = async () => {
    try {
      await API.delete(`/users/${selectedUser.id}`);
      toast.success('User deactivated');
      setDeleteOpen(false);
      fetchData();
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed to delete user'); }
  };

  const creatableRoles = roles.filter(r => r.can_create);
  const isCeoOrHr = ['CEO', 'Super Admin', 'HR'].includes(currentUser?.role);

  // Redirect non-CEO/HR users
  if (!isCeoOrHr) {
    return <div className="text-center py-12 text-slate-500">Only CEO and HR can access user management.</div>;
  }

  if (loading) return <div className="flex items-center justify-center h-64 text-slate-500">Loading...</div>;

  return (
    <div className="space-y-4" data-testid="users-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl md:text-2xl font-heading font-semibold text-slate-900">User Management</h1>
          <p className="text-sm text-slate-500">{users.length} users</p>
        </div>
        {creatableRoles.length > 0 && (
          <Button onClick={() => setCreateOpen(true)} className="bg-blue-700 hover:bg-blue-800 active:scale-[0.98]" data-testid="create-user-button">
            <Plus className="w-4 h-4 mr-1" /> Add User
          </Button>
        )}
      </div>

      {users.length === 0 ? (
        <div className="text-center py-12 text-slate-500">No users found</div>
      ) : (
        <div className="space-y-2">
          {users.map(u => {
            const roleInfo = roles.find(r => r.name === u.role);
            return (
              <Card key={u.id} className="border-slate-200 shadow-none">
                <CardContent className="p-3 md:p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="w-9 h-9 rounded-full bg-slate-100 flex items-center justify-center flex-shrink-0">
                        <UserCog className="w-4 h-4 text-slate-500" />
                      </div>
                      <div className="min-w-0">
                        <p className="font-medium text-slate-900 truncate text-sm">{u.name}</p>
                        <p className="text-xs text-slate-500 truncate">{u.email}</p>
                        {u.department && <p className="text-xs text-slate-400">{u.department}</p>}
                      </div>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <Badge className={`${LEVEL_COLORS[roleInfo?.level] || 'bg-slate-100 text-slate-700'} border-0 text-xs`}>
                        {u.role}
                      </Badge>
                      {u.is_active === false && <Badge variant="destructive" className="text-xs">Inactive</Badge>}
                      {/* Action buttons */}
                      <div className="flex gap-1 ml-2">
                        <Button variant="ghost" size="icon" className="h-7 w-7 text-slate-400 hover:text-blue-600" onClick={() => openEdit(u)} data-testid={`edit-user-${u.id}`}>
                          <Pencil className="w-3.5 h-3.5" />
                        </Button>
                        {isCeoOrHr && (
                          <>
                            <Button variant="ghost" size="icon" className="h-7 w-7 text-slate-400 hover:text-amber-600" onClick={() => { setSelectedUser(u); setResetOpen(true); }} data-testid={`reset-pwd-${u.id}`}>
                              <KeyRound className="w-3.5 h-3.5" />
                            </Button>
                            {u.role !== 'CEO' && u.id !== currentUser?.id && (
                              <Button variant="ghost" size="icon" className="h-7 w-7 text-slate-400 hover:text-red-600" onClick={() => { setSelectedUser(u); setDeleteOpen(true); }} data-testid={`delete-user-${u.id}`}>
                                <Trash2 className="w-3.5 h-3.5" />
                              </Button>
                            )}
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Create User Dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="max-w-md"><DialogDescription className="sr-only">Create a new user</DialogDescription>
          <DialogHeader><DialogTitle className="font-heading">Create User</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div><Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Name</Label><Input value={form.name} onChange={e => setForm({...form, name: e.target.value})} className="mt-1" data-testid="user-name-input" /></div>
            <div><Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Email</Label><Input type="email" value={form.email} onChange={e => setForm({...form, email: e.target.value})} className="mt-1" data-testid="user-email-input" /></div>
            <div><Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Password</Label><Input type="password" value={form.password} onChange={e => setForm({...form, password: e.target.value})} className="mt-1" /></div>
            <div>
              <Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Role</Label>
              <Select value={form.role} onValueChange={v => { const ri = roles.find(r => r.name === v); setForm({...form, role: v, department: ri?.department || ''}); }}>
                <SelectTrigger className="mt-1" data-testid="user-role-select"><SelectValue placeholder="Select role" /></SelectTrigger>
                <SelectContent>{creatableRoles.map(r => <SelectItem key={r.name} value={r.name}>{r.name} ({r.level})</SelectItem>)}</SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>Cancel</Button>
            <Button onClick={handleCreate} className="bg-blue-700 hover:bg-blue-800" data-testid="save-user-button">Create User</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit User Dialog */}
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="max-w-md"><DialogDescription className="sr-only">Edit user details</DialogDescription>
          <DialogHeader><DialogTitle className="font-heading">Edit User - {selectedUser?.name}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div><Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Name</Label><Input value={editForm.name} onChange={e => setEditForm({...editForm, name: e.target.value})} className="mt-1" /></div>
            <div><Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Email</Label><Input type="email" value={editForm.email} onChange={e => setEditForm({...editForm, email: e.target.value})} className="mt-1" /></div>
            {isCeoOrHr && (
              <div>
                <Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Role</Label>
                <Select value={editForm.role} onValueChange={v => { const ri = roles.find(r => r.name === v); setEditForm({...editForm, role: v, department: ri?.department || editForm.department}); }}>
                  <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                  <SelectContent>{roles.map(r => <SelectItem key={r.name} value={r.name}>{r.name}</SelectItem>)}</SelectContent>
                </Select>
              </div>
            )}
            <div>
              <Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Branch</Label>
              <Select value={editForm.branch_id || "none"} onValueChange={v => setEditForm({...editForm, branch_id: v === "none" ? "" : v})}>
                <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                <SelectContent><SelectItem value="none">No Branch</SelectItem>{branches.map(b => <SelectItem key={b.id} value={b.id}>{b.name}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            {isCeoOrHr && (
              <div className="flex items-center gap-2">
                <Switch checked={editForm.is_active} onCheckedChange={v => setEditForm({...editForm, is_active: v})} />
                <Label className="text-sm">Active</Label>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditOpen(false)}>Cancel</Button>
            <Button onClick={handleEdit} className="bg-blue-700 hover:bg-blue-800" data-testid="save-edit-button">Save Changes</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reset Password Dialog */}
      <Dialog open={resetOpen} onOpenChange={setResetOpen}>
        <DialogContent className="max-w-sm"><DialogDescription className="sr-only">Reset user password</DialogDescription>
          <DialogHeader><DialogTitle className="font-heading">Reset Password</DialogTitle></DialogHeader>
          <p className="text-sm text-slate-500">Set new password for <strong>{selectedUser?.name}</strong></p>
          <Input type="password" value={newPassword} onChange={e => setNewPassword(e.target.value)} placeholder="New password (min 6 chars)" data-testid="new-password-input" />
          <DialogFooter>
            <Button variant="outline" onClick={() => setResetOpen(false)}>Cancel</Button>
            <Button onClick={handleResetPassword} className="bg-amber-600 hover:bg-amber-700" data-testid="confirm-reset-button">Reset Password</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete User Dialog */}
      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent className="max-w-sm"><DialogDescription className="sr-only">Confirm user deactivation</DialogDescription>
          <DialogHeader><DialogTitle className="font-heading text-red-600">Deactivate User</DialogTitle></DialogHeader>
          <p className="text-sm text-slate-500">Are you sure you want to deactivate <strong>{selectedUser?.name}</strong>? They won't be able to login.</p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteOpen(false)}>Cancel</Button>
            <Button onClick={handleDelete} variant="destructive" data-testid="confirm-delete-button">Deactivate</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
