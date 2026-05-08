import { useState, useEffect } from 'react';
import API from '@/api';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { ScrollText } from 'lucide-react';
import { toast } from 'sonner';

const ACTION_COLORS = {
  login: 'bg-blue-100 text-blue-700',
  create: 'bg-emerald-100 text-emerald-700',
  create_user: 'bg-emerald-100 text-emerald-700',
  update: 'bg-amber-100 text-amber-700',
  update_user: 'bg-amber-100 text-amber-700',
  delete: 'bg-rose-100 text-rose-700',
  delete_user: 'bg-rose-100 text-rose-700',
  stage_transition: 'bg-violet-100 text-violet-700',
  add_call: 'bg-blue-100 text-blue-700',
  ai_recommend: 'bg-indigo-100 text-indigo-700',
  reset_password: 'bg-amber-100 text-amber-700',
  convert_employee: 'bg-emerald-100 text-emerald-700',
};

export default function AuditPage() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');

  useEffect(() => { fetchLogs(); }, [filter]);

  const fetchLogs = async () => {
    try {
      const params = filter !== 'all' ? `?entity_type=${filter}` : '';
      const { data } = await API.get(`/audit${params}`);
      setLogs(data);
    } catch { toast.error('Failed to load audit logs'); }
    finally { setLoading(false); }
  };

  if (loading) return <div className="flex items-center justify-center h-64 text-slate-500">Loading...</div>;

  return (
    <div className="space-y-4" data-testid="audit-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl md:text-2xl font-heading font-semibold text-slate-900">Audit Logs</h1>
          <p className="text-sm text-slate-500">Track all system actions</p>
        </div>
        <Select value={filter} onValueChange={setFilter}>
          <SelectTrigger className="w-36"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Actions</SelectItem>
            <SelectItem value="user">Users</SelectItem>
            <SelectItem value="lead">Leads</SelectItem>
            <SelectItem value="branch">Branches</SelectItem>
            <SelectItem value="job">Jobs</SelectItem>
            <SelectItem value="task">Tasks</SelectItem>
            <SelectItem value="employee">Employees</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {logs.length === 0 ? (
        <div className="text-center py-12 text-slate-500">No audit logs found</div>
      ) : (
        <div className="space-y-2">
          {logs.map((log, i) => (
            <Card key={log.id || i} className="border-slate-200 shadow-none">
              <CardContent className="p-3">
                <div className="flex items-start gap-3">
                  <ScrollText className="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-medium text-slate-900">{log.user_name}</span>
                      <Badge className={`${ACTION_COLORS[log.action] || 'bg-slate-100 text-slate-700'} border-0 text-xs`}>{log.action}</Badge>
                      <Badge variant="outline" className="text-xs">{log.entity_type}</Badge>
                    </div>
                    {log.details && Object.keys(log.details).length > 0 && (
                      <p className="text-xs text-slate-500 mt-1">
                        {Object.entries(log.details).slice(0, 3).map(([k, v]) => `${k}: ${typeof v === 'object' ? JSON.stringify(v) : v}`).join(' | ')}
                      </p>
                    )}
                    <p className="text-xs text-slate-400 mt-0.5">{new Date(log.timestamp).toLocaleString()}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
