import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import API from '@/api';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ArrowLeft, Search, Eye, Briefcase, Phone, Mail } from 'lucide-react';
import { toast } from 'sonner';

const STAGE_LABELS = {
  new_lead: 'New',
  qualified: 'Qualified',
  hr_interview: 'Interview Scheduled',
  manager_interview: 'Interview Completed',
  hold: 'Hold',
  selected: 'Selected',
  three_months: 'Joined',
  joined: 'Joined',
  rejected: 'Rejected',
};
const STAGE_COLORS = {
  new_lead: 'bg-slate-100 text-slate-700',
  qualified: 'bg-sky-100 text-sky-700',
  hr_interview: 'bg-amber-100 text-amber-700',
  manager_interview: 'bg-indigo-100 text-indigo-700',
  hold: 'bg-rose-100 text-rose-700',
  selected: 'bg-emerald-100 text-emerald-700',
  three_months: 'bg-emerald-200 text-emerald-800',
  joined: 'bg-emerald-200 text-emerald-800',
  rejected: 'bg-slate-200 text-slate-600',
};

const fmtDate = (iso) => {
  if (!iso) return '—';
  try { return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' }); }
  catch { return iso; }
};

export default function HiringDesignationCandidatesPage() {
  const { segment, designationId } = useParams();
  const nav = useNavigate();
  const [designation, setDesignation] = useState(null);
  const [candidates, setCandidates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await API.get(`/hirings/designations/${designationId}/candidates`);
      setDesignation(data.designation);
      setCandidates(data.candidates || []);
    } catch {
      toast.error('Failed to load candidates');
    } finally {
      setLoading(false);
    }
  }, [designationId]);

  useEffect(() => { fetchData(); }, [fetchData]);

  if (loading) return <div className="flex items-center justify-center h-64 text-slate-500">Loading...</div>;
  if (!designation) return <div className="p-6 text-slate-500">Designation not found.</div>;

  const filtered = candidates.filter((c) => {
    if (!query.trim()) return true;
    const q = query.toLowerCase();
    return (c.name || '').toLowerCase().includes(q)
      || (c.phone || '').includes(q)
      || (c.email || '').toLowerCase().includes(q);
  });

  return (
    <div className="space-y-4" data-testid="hiring-candidates-page">
      <button
        type="button"
        onClick={() => nav('/hirings')}
        className="inline-flex items-center text-sm text-slate-600 hover:text-blue-700"
        data-testid="back-to-hirings"
      >
        <ArrowLeft className="w-4 h-4 mr-1" /> Back to Hirings
      </button>

      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-xl md:text-2xl font-heading font-semibold text-slate-900 flex items-center gap-2">
            <Briefcase className="w-5 h-5" /> {designation.name}
          </h1>
          <div className="flex items-center gap-2 mt-1.5 flex-wrap">
            <Badge className={`text-[10px] border-0 ${designation.office_type === 'franchise' ? 'bg-violet-100 text-violet-700' : 'bg-blue-100 text-blue-700'}`}>
              {designation.office_type === 'franchise' ? 'Franchise' : 'Head Office'}
            </Badge>
            <p className="text-sm text-slate-500">
              {candidates.length} candidate{candidates.length !== 1 ? 's' : ''}
              {designation.department ? ` · ${designation.department}` : ''}
            </p>
          </div>
        </div>
        <div className="relative w-full sm:w-72">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by name, phone, email"
            className="pl-9"
            data-testid="candidates-search-input"
          />
        </div>
      </div>

      {filtered.length === 0 ? (
        <Card className="border-dashed border-slate-300 shadow-none">
          <CardContent className="py-10 text-center text-sm text-slate-500">
            {candidates.length === 0
              ? 'No candidates yet for this designation. Create a lead with this designation to see it here.'
              : 'No candidates match your search.'}
          </CardContent>
        </Card>
      ) : (
        <Card className="border-slate-200 shadow-none">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr className="text-xs uppercase tracking-wider text-slate-500">
                  <th className="text-left p-3">Name</th>
                  <th className="text-left p-3">Mobile</th>
                  <th className="text-left p-3 hidden md:table-cell">Email</th>
                  <th className="text-left p-3 hidden lg:table-cell">Applied</th>
                  <th className="text-left p-3">Current Stage</th>
                  <th className="text-right p-3">Action</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((c) => (
                  <tr
                    key={c.id}
                    className="border-b border-slate-100 hover:bg-blue-50/30"
                    data-testid={`candidate-row-${c.id}`}
                  >
                    <td className="p-3 font-medium text-slate-900">{c.name}</td>
                    <td className="p-3 text-slate-700">
                      <span className="inline-flex items-center gap-1"><Phone className="w-3 h-3 text-slate-400" /> {c.phone || '—'}</span>
                    </td>
                    <td className="p-3 text-slate-600 hidden md:table-cell">
                      {c.email ? (
                        <span className="inline-flex items-center gap-1"><Mail className="w-3 h-3 text-slate-400" /> {c.email}</span>
                      ) : '—'}
                    </td>
                    <td className="p-3 text-slate-600 hidden lg:table-cell">{fmtDate(c.created_at)}</td>
                    <td className="p-3">
                      <Badge className={`text-[10px] border-0 ${STAGE_COLORS[c.current_stage] || 'bg-slate-100 text-slate-700'}`}>
                        {STAGE_LABELS[c.current_stage] || c.current_stage}
                      </Badge>
                    </td>
                    <td className="p-3 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => nav(`/leads/${c.id}`)}
                        data-testid={`view-candidate-${c.id}`}
                      >
                        <Eye className="w-4 h-4 mr-1" /> View
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
