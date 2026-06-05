import { useState, useEffect } from 'react';
import API from '@/api';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Trash2, RotateCcw, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';

function fmt(iso) { return iso ? new Date(iso).toLocaleString() : '—'; }

export default function DeletedLeadsPage() {
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [confirm, setConfirm] = useState({ open: false, lead: null, action: null });

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const { data } = await API.get('/leads/deleted');
      setLeads(data);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to load deleted leads');
    } finally { setLoading(false); }
  };

  const doAction = async () => {
    const { lead, action } = confirm;
    try {
      if (action === 'restore') {
        await API.post(`/leads/${lead.id}/restore`);
        toast.success('Lead restored');
      } else if (action === 'hard_delete') {
        await API.delete(`/leads/${lead.id}`);
        toast.success('Lead permanently deleted');
      }
      setConfirm({ open: false, lead: null, action: null });
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Action failed');
    }
  };

  if (loading) return <div className="flex items-center justify-center h-64 text-slate-500">Loading...</div>;

  return (
    <div className="space-y-4" data-testid="deleted-leads-page">
      <div>
        <h1 className="text-xl md:text-2xl font-heading font-semibold text-slate-900 flex items-center gap-2">
          <Trash2 className="w-5 h-5" /> Deleted Leads
        </h1>
        <p className="text-sm text-slate-500">{leads.length} soft-deleted lead{leads.length !== 1 ? 's' : ''} · CEO can restore or permanently delete</p>
      </div>

      {leads.length === 0 ? (
        <Card className="border-slate-200 shadow-none">
          <CardContent className="p-10 text-center text-slate-500 text-sm">No deleted leads.</CardContent>
        </Card>
      ) : (
        <Card className="border-slate-200 shadow-none">
          <CardContent className="p-0 overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="bg-slate-50">
                  <TableHead className="text-xs uppercase font-semibold text-slate-600">Name</TableHead>
                  <TableHead className="text-xs uppercase font-semibold text-slate-600">Phone</TableHead>
                  <TableHead className="text-xs uppercase font-semibold text-slate-600">Type</TableHead>
                  <TableHead className="text-xs uppercase font-semibold text-slate-600">Last Stage</TableHead>
                  <TableHead className="text-xs uppercase font-semibold text-slate-600">Deleted By</TableHead>
                  <TableHead className="text-xs uppercase font-semibold text-slate-600">Deleted At</TableHead>
                  <TableHead className="text-xs uppercase font-semibold text-slate-600 text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {leads.map(l => (
                  <TableRow key={l.id} className="hover:bg-slate-50" data-testid={`deleted-lead-row-${l.id}`}>
                    <TableCell className="font-medium">{l.name}</TableCell>
                    <TableCell className="text-xs text-slate-600">{l.phone || '—'}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-[10px]">
                        {l.is_technician ? 'Franchise' : 'Head Office'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs text-slate-600">{l.current_stage || '—'}</TableCell>
                    <TableCell className="text-xs text-slate-600">{l.deleted_by_name || '—'}</TableCell>
                    <TableCell className="text-xs text-slate-600">{fmt(l.deleted_at)}</TableCell>
                    <TableCell className="text-right">
                      <Button
                        size="sm"
                        variant="outline"
                        className="h-7 text-xs text-emerald-700 hover:bg-emerald-50 mr-1"
                        onClick={() => setConfirm({ open: true, lead: l, action: 'restore' })}
                        data-testid={`restore-lead-${l.id}`}
                      >
                        <RotateCcw className="w-3 h-3 mr-1" /> Restore
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        className="h-7 text-xs text-rose-700 hover:bg-rose-50"
                        onClick={() => setConfirm({ open: true, lead: l, action: 'hard_delete' })}
                        data-testid={`permanent-delete-lead-${l.id}`}
                      >
                        <Trash2 className="w-3 h-3 mr-1" /> Permanent
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      <Dialog open={confirm.open} onOpenChange={(v) => !v && setConfirm({ open: false, lead: null, action: null })}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2">
              {confirm.action === 'restore' ? <RotateCcw className="w-4 h-4 text-emerald-600" /> : <AlertTriangle className="w-4 h-4 text-rose-600" />}
              {confirm.action === 'restore' ? 'Restore Lead?' : 'Permanently Delete?'}
            </DialogTitle>
          </DialogHeader>
          <p className="text-sm text-slate-600">
            {confirm.action === 'restore'
              ? <>Restore <strong>{confirm.lead?.name}</strong> back to the active pipeline?</>
              : <>This will <strong>permanently erase</strong> {confirm.lead?.name} and all related records (stage history, interviews, candidate form data). This cannot be undone.</>}
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirm({ open: false, lead: null, action: null })}>Cancel</Button>
            <Button
              className={confirm.action === 'restore' ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-rose-600 hover:bg-rose-700'}
              onClick={doAction}
              data-testid="confirm-deleted-action-button"
            >
              {confirm.action === 'restore' ? 'Restore' : 'Delete Permanently'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
