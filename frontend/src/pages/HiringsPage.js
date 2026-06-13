import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import API from '@/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Briefcase, Building2, Users, ChevronRight } from 'lucide-react';
import { toast } from 'sonner';

const STAGE_COLORS = {
  new_lead: 'bg-slate-100 text-slate-700',
  qualified: 'bg-sky-100 text-sky-700',
  hr_interview: 'bg-amber-100 text-amber-700',
  manager_interview: 'bg-indigo-100 text-indigo-700',
  hold: 'bg-rose-100 text-rose-700',
  selected: 'bg-emerald-100 text-emerald-700',
  joined: 'bg-emerald-200 text-emerald-800',
  rejected: 'bg-slate-200 text-slate-600',
};

export default function HiringsPage() {
  const [activeTab, setActiveTab] = useState('head_office');
  const [data, setData] = useState({ head_office: null, franchise: null });
  const [loading, setLoading] = useState(true);
  const nav = useNavigate();

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [ho, fr] = await Promise.all([
        API.get('/hirings/head_office'),
        API.get('/hirings/franchise'),
      ]);
      setData({ head_office: ho.data, franchise: fr.data });
    } catch {
      toast.error('Failed to load Hirings data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  if (loading) return <div className="flex items-center justify-center h-64 text-slate-500">Loading...</div>;

  const Section = ({ payload, segmentKey }) => {
    if (!payload) return null;
    const stages = payload.stages || [];
    const designations = payload.designations || [];
    const summary = payload.summary || { designations: 0, candidates: 0, stages: {} };
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2 flex-wrap">
          <Badge className="bg-blue-50 text-blue-700 border-0">
            <span className="font-semibold mr-1">{summary.designations}</span> designations
          </Badge>
          <Badge className="bg-emerald-50 text-emerald-700 border-0">
            <span className="font-semibold mr-1">{summary.candidates}</span> total candidates
          </Badge>
        </div>
        {designations.length === 0 ? (
          <Card className="border-dashed border-slate-300 shadow-none">
            <CardContent className="py-10 text-center text-sm text-slate-500">
              No designations under {segmentKey === 'franchise' ? 'Franchise' : 'Head Office'}.<br />
              <button onClick={() => nav('/designations')} className="mt-2 text-blue-700 hover:underline text-xs">
                Create a designation →
              </button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {designations.map((d) => (
              <Card
                key={`${segmentKey}-${d.designation_id || d.name}`}
                className={`border-slate-200 shadow-none cursor-pointer hover:-translate-y-0.5 hover:shadow-md transition-all ${d.designation_id ? '' : 'border-dashed'}`}
                onClick={() => {
                  if (d.designation_id) {
                    nav(`/hirings/${segmentKey}/designations/${d.designation_id}`);
                  } else {
                    // Legacy ad-hoc — open with name-based path (segment leads filtered by role)
                    const seg = segmentKey === 'franchise' ? '/leads/franchise' : '/leads/head-office';
                    nav(`${seg}?job_role=${encodeURIComponent(d.name)}`);
                  }
                }}
                data-testid={`hiring-designation-card-${(d.designation_id || d.name.replace(/\s+/g, '-').toLowerCase())}`}
              >
                <CardContent className="p-4">
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <p className={`font-medium truncate ${d.designation_id ? 'text-slate-900' : 'text-slate-600 italic'}`}>{d.name}</p>
                        {!d.designation_id && <Badge variant="outline" className="text-[10px] text-slate-500">Legacy</Badge>}
                        {d.designation_id && !d.active && <Badge variant="outline" className="text-[10px] text-slate-500">Inactive</Badge>}
                      </div>
                      {d.department && <p className="text-xs text-slate-500 mt-0.5">{d.department}</p>}
                    </div>
                    <div className="text-right shrink-0">
                      <p className="text-2xl font-heading font-semibold text-blue-700 leading-none">{d.total}</p>
                      <p className="text-[10px] uppercase tracking-wider text-slate-400 mt-1">Total</p>
                    </div>
                  </div>
                  <div className="grid grid-cols-4 gap-1 mt-2">
                    {stages.map((s) => (
                      <div
                        key={s.key}
                        className={`text-center py-1.5 px-1 rounded ${STAGE_COLORS[s.key] || 'bg-slate-100 text-slate-700'}`}
                        data-testid={`stage-${segmentKey}-${(d.designation_id || d.name.replace(/\s+/g, '-').toLowerCase())}-${s.key}`}
                      >
                        <p className="text-sm font-semibold leading-none">{d.counts[s.key] || 0}</p>
                        <p className="text-[9px] mt-0.5 uppercase tracking-wider leading-tight">{s.label}</p>
                      </div>
                    ))}
                  </div>
                  <div className="flex items-center justify-end mt-3 text-xs text-blue-700">
                    View candidates <ChevronRight className="w-3.5 h-3.5 ml-0.5" />
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-4" data-testid="hirings-page">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl md:text-2xl font-heading font-semibold text-slate-900 flex items-center gap-2">
            <Briefcase className="w-5 h-5" /> Hirings
          </h1>
          <p className="text-sm text-slate-500">Designation-based candidate pipeline</p>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid grid-cols-2 max-w-md">
          <TabsTrigger value="head_office" data-testid="hirings-tab-head_office">
            <Building2 className="w-4 h-4 mr-1.5" /> Head Office
          </TabsTrigger>
          <TabsTrigger value="franchise" data-testid="hirings-tab-franchise">
            <Users className="w-4 h-4 mr-1.5" /> Franchise
          </TabsTrigger>
        </TabsList>
        <TabsContent value="head_office" className="mt-4">
          <Section payload={data.head_office} segmentKey="head_office" />
        </TabsContent>
        <TabsContent value="franchise" className="mt-4">
          <Section payload={data.franchise} segmentKey="franchise" />
        </TabsContent>
      </Tabs>
    </div>
  );
}
