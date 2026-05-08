import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import API from '@/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Megaphone, ArrowLeft, Clock, CheckCircle, Play } from 'lucide-react';
import { toast } from 'sonner';

const STATUS_COLORS = { pending: 'bg-amber-100 text-amber-700', running: 'bg-blue-100 text-blue-700', completed: 'bg-emerald-100 text-emerald-700' };
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function CampaignsPage() {
  const nav = useNavigate();
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');

  useEffect(() => { fetchCampaigns(); }, []);

  const fetchCampaigns = async () => {
    try { const { data } = await API.get('/campaigns'); setCampaigns(data); } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); } finally { setLoading(false); }
  };

  const updateStatus = async (id, status) => {
    try { await API.put(`/campaigns/${id}`, { status }); toast.success('Status updated'); fetchCampaigns(); } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
  };

  const filtered = filter === 'all' ? campaigns : campaigns.filter(c => c.status === filter);
  if (loading) return <div className="flex items-center justify-center h-64 text-slate-500">Loading...</div>;

  return (
    <div className="space-y-4" data-testid="campaigns-page">
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon" onClick={() => nav(-1)}><ArrowLeft className="w-4 h-4" /></Button>
        <div><h1 className="text-xl md:text-2xl font-heading font-semibold text-slate-900">Ad Campaigns</h1><p className="text-sm text-slate-500">{campaigns.length} campaigns</p></div>
      </div>

      <div className="flex gap-2">
        {['all', 'pending', 'running', 'completed'].map(f => (
          <Button key={f} variant={filter === f ? 'default' : 'outline'} size="sm" className={filter === f ? 'bg-blue-700' : ''} onClick={() => setFilter(f)}>{f === 'all' ? 'All' : f}</Button>
        ))}
      </div>

      {filtered.length === 0 ? <p className="text-center py-12 text-slate-500">No campaigns found</p> : (
        <div className="space-y-2">
          {filtered.map(c => (
            <Card key={c.id} className="border-slate-200 shadow-none">
              <CardContent className="p-4">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-medium text-slate-900">{c.role}</p>
                    <p className="text-sm text-slate-500">{c.location}</p>
                    <p className="text-xs text-slate-400 mt-1">Platform: {c.platform?.replace('_', ' ')} | Assigned: {c.assigned_to_name}</p>
                    {c.post_file_url && <a href={`${BACKEND_URL}${c.post_file_url}`} target="_blank" rel="noopener noreferrer" className="text-xs text-blue-600 underline mt-1 inline-block">View Design</a>}
                  </div>
                  <div className="flex items-center gap-2">
                    <Select value={c.status} onValueChange={v => updateStatus(c.id, v)}>
                      <SelectTrigger className="w-28 h-8 text-xs" data-testid={`campaign-status-${c.id}`}><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="pending">Pending</SelectItem>
                        <SelectItem value="running">Running</SelectItem>
                        <SelectItem value="completed">Completed</SelectItem>
                      </SelectContent>
                    </Select>
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
