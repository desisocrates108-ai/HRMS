import { useState, useEffect } from 'react';
import API from '@/api';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Search, Building, Wrench, Eye, Phone, Mail, Calendar, FileText, Star, Award } from 'lucide-react';
import { toast } from 'sonner';

function EmployeeDetail({ emp, onClose }) {
  const [lead, setLead] = useState(null);
  const [hrInterview, setHrInterview] = useState(null);
  const [mgrInterview, setMgrInterview] = useState(null);
  const [history, setHistory] = useState([]);
  const [offerLetters, setOfferLetters] = useState([]);

  useEffect(() => {
    if (!emp) return;
    const lid = emp.lead_id;
    if (!lid) return;
    Promise.all([
      API.get(`/leads/${lid}`).then(r => r.data).catch(() => null),
      API.get(`/interviews/${lid}`).then(r => r.data).catch(() => ({})),
      API.get(`/leads/${lid}/history`).then(r => r.data).catch(() => []),
      API.get('/offer-letters', { params: { lead_id: lid } }).then(r => r.data).catch(() => []),
    ]).then(([l, i, h, o]) => {
      setLead(l);
      setHrInterview(i?.hr);
      setMgrInterview(i?.manager);
      setHistory(h);
      setOfferLetters(o);
    });
  }, [emp]);

  if (!emp) return null;
  return (
    <Dialog open={!!emp} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto" data-testid="employee-detail-dialog">
        <DialogHeader>
          <DialogTitle className="font-heading text-xl">{emp.name}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          {/* Basic Info */}
          <Card className="border-slate-200 shadow-none">
            <CardContent className="p-3 space-y-2 text-sm">
              <div className="grid grid-cols-2 gap-2">
                <div><span className="text-slate-500">Role:</span> <strong>{emp.role}</strong></div>
                <div><span className="text-slate-500">Status:</span> <Badge variant={emp.status === 'left' ? 'destructive' : 'default'}>{emp.status || 'active'}</Badge></div>
                <div className="flex items-center gap-1 text-slate-700"><Phone className="w-3 h-3" /> {emp.phone || '—'}</div>
                <div className="flex items-center gap-1 text-slate-700"><Mail className="w-3 h-3" /> {emp.email || '—'}</div>
                <div><span className="text-slate-500">Department:</span> {emp.department || '—'}</div>
                <div><span className="text-slate-500">Category:</span> {emp.category || '—'}</div>
                <div className="flex items-center gap-1 text-slate-700"><Calendar className="w-3 h-3" /> Joined: {emp.joining_date || '—'}</div>
                <div><span className="text-slate-500">Branch:</span> {emp.branch_id ? 'Linked' : 'Head Office'}</div>
              </div>
            </CardContent>
          </Card>

          {/* Resume / Source Lead */}
          {lead && (
            <Card className="border-slate-200 shadow-none">
              <CardContent className="p-3 space-y-1 text-sm">
                <p className="font-semibold text-slate-700 mb-1">Source Lead</p>
                <div className="grid grid-cols-2 gap-1">
                  <div><span className="text-slate-500">Source:</span> {lead.source}</div>
                  <div><span className="text-slate-500">Lead Type:</span> {lead.is_technician ? 'Franchise' : 'Head Office'}</div>
                  <div><span className="text-slate-500">City:</span> {lead.location_city}</div>
                  <div><span className="text-slate-500">Area:</span> {lead.location_area}</div>
                </div>
                {lead.resume_url && (
                  <a href={`${process.env.REACT_APP_BACKEND_URL}${lead.resume_url}`} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-blue-700 text-sm mt-2" data-testid="resume-link">
                    <FileText className="w-3 h-3" /> View Resume
                  </a>
                )}
              </CardContent>
            </Card>
          )}

          {/* HR Interview */}
          {hrInterview && (
            <Card className="border-slate-200 shadow-none">
              <CardContent className="p-3 text-sm">
                <p className="font-semibold text-slate-700 mb-1 flex items-center gap-1"><Star className="w-3 h-3 text-amber-500" /> HR Interview Review</p>
                <p>Avg Rating: <strong>{hrInterview.avg_rating}/5</strong> · By {hrInterview.submitted_by_name}</p>
                {hrInterview.remarks && <p className="text-slate-600 italic mt-1">"{hrInterview.remarks}"</p>}
              </CardContent>
            </Card>
          )}

          {/* Manager Interview */}
          {mgrInterview && (
            <Card className="border-slate-200 shadow-none">
              <CardContent className="p-3 text-sm">
                <p className="font-semibold text-slate-700 mb-1 flex items-center gap-1"><Star className="w-3 h-3 text-violet-500" /> Manager Interview Review</p>
                <p>Avg Rating: <strong>{mgrInterview.avg_rating}/5</strong> · By {mgrInterview.submitted_by_name}</p>
                {mgrInterview.remarks && <p className="text-slate-600 italic mt-1">"{mgrInterview.remarks}"</p>}
              </CardContent>
            </Card>
          )}

          {/* Offer Letters */}
          {offerLetters.length > 0 && (
            <Card className="border-slate-200 shadow-none">
              <CardContent className="p-3 text-sm space-y-1">
                <p className="font-semibold text-slate-700 mb-1 flex items-center gap-1"><Award className="w-3 h-3 text-emerald-500" /> Offer Letter History</p>
                {offerLetters.map(o => (
                  <div key={o.id} className="text-xs text-slate-600">
                    {new Date(o.sent_at).toLocaleString()} · {o.role} @ {o.branch_name} · WA: {o.whatsapp_status || 'queued'}
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Stage History */}
          {history.length > 0 && (
            <Card className="border-slate-200 shadow-none">
              <CardContent className="p-3 text-sm">
                <p className="font-semibold text-slate-700 mb-1">Stage History</p>
                <div className="space-y-1 max-h-40 overflow-y-auto">
                  {history.map((h, i) => (
                    <div key={i} className="text-xs text-slate-600 flex justify-between">
                      <span>{h.from_stage || 'start'} → <strong>{h.to_stage}</strong></span>
                      <span className="text-slate-400">{new Date(h.timestamp).toLocaleDateString()}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Exit */}
          {emp.status === 'left' && (
            <Card className="border-rose-200 shadow-none bg-rose-50">
              <CardContent className="p-3 text-sm">
                <p className="font-semibold text-rose-700">Exit Details</p>
                <p>Date: {emp.exit_date} · Type: {emp.exit_type}</p>
                <p>Reason: {emp.exit_reason}</p>
                {emp.exit_remarks && <p className="text-slate-600 italic">"{emp.exit_remarks}"</p>}
              </CardContent>
            </Card>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default function DatabasePage() {
  const [tab, setTab] = useState('head_office');
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [selected, setSelected] = useState(null);

  useEffect(() => { fetchData(); }, [tab, statusFilter]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const params = { category: tab };
      if (statusFilter !== 'all') params.status = statusFilter;
      const { data } = await API.get('/employees', { params });
      setEmployees(data);
    } catch { toast.error('Failed to load employees'); }
    finally { setLoading(false); }
  };

  const filtered = employees.filter(e =>
    !search || e.name?.toLowerCase().includes(search.toLowerCase()) || e.role?.toLowerCase().includes(search.toLowerCase()) || e.phone?.includes(search)
  );

  return (
    <div className="space-y-4" data-testid="database-page">
      <div>
        <h1 className="text-xl md:text-2xl font-heading font-semibold text-slate-900">Database</h1>
        <p className="text-sm text-slate-500">Employee records (joined from leads pipeline)</p>
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="grid grid-cols-2 w-full md:w-96">
          <TabsTrigger value="head_office" data-testid="tab-head-office"><Building className="w-4 h-4 mr-1" /> Head Office</TabsTrigger>
          <TabsTrigger value="branch" data-testid="tab-franchise"><Wrench className="w-4 h-4 mr-1" /> Franchise</TabsTrigger>
        </TabsList>

        <div className="mt-3 flex flex-col md:flex-row gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <Input
              placeholder="Search by name, role, phone..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 h-10"
              data-testid="employee-search-input"
            />
          </div>
          <select
            className="h-10 px-3 border border-slate-200 rounded-md text-sm bg-white"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            data-testid="status-filter"
          >
            <option value="all">All Status</option>
            <option value="active">Active</option>
            <option value="left">Left</option>
          </select>
        </div>

        <TabsContent value={tab} className="mt-4">
          {loading ? (
            <div className="text-center py-8 text-slate-500">Loading...</div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-8 text-slate-500 text-sm">No employees found</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {filtered.map(e => (
                <Card
                  key={e.id}
                  className="border-slate-200 shadow-none cursor-pointer hover:-translate-y-0.5 hover:shadow-md hover:border-slate-300 transition-all duration-200"
                  onClick={() => setSelected(e)}
                  data-testid={`employee-card-${e.id}`}
                >
                  <CardContent className="p-3 flex items-center justify-between">
                    <div className="min-w-0">
                      <p className="font-medium text-slate-900 truncate">{e.name}</p>
                      <p className="text-xs text-slate-500">{e.role} · {e.department || 'No Dept'} · Joined {e.joining_date}</p>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <Badge variant={e.status === 'left' ? 'destructive' : 'secondary'}>{e.status || 'active'}</Badge>
                      <Eye className="w-4 h-4 text-slate-400" />
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>

      {selected && <EmployeeDetail emp={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}
