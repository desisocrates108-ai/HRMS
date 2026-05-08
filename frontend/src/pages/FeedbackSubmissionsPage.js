import { useState, useEffect, useCallback } from 'react';
import API from '@/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { StarRating } from '@/components/StarRating';
import { MessageCircle, LogOut } from 'lucide-react';
import { toast } from 'sonner';

export default function FeedbackSubmissionsPage() {
  const [kind, setKind] = useState('rejection');
  const [subs, setSubs] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [viewing, setViewing] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [s, sum] = await Promise.all([
        API.get(`/feedback/submissions?kind=${kind}`),
        API.get('/feedback/submissions/summary'),
      ]);
      setSubs(s.data);
      setSummary(sum.data);
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Failed to load feedback');
    } finally { setLoading(false); }
  }, [kind]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="space-y-4" data-testid="feedback-submissions-page">
      <div>
        <h1 className="text-xl md:text-2xl font-heading font-semibold text-slate-900">Feedback Submissions</h1>
        <p className="text-sm text-slate-500">
          {summary ? `${summary.rejection_count} rejection · ${summary.exit_count} exit · ${summary.pending_invitations} pending` : 'Loading...'}
        </p>
      </div>

      <Tabs value={kind} onValueChange={setKind}>
        <TabsList className="grid grid-cols-2 w-full md:w-96">
          <TabsTrigger value="rejection" data-testid="fb-tab-rejection">
            <MessageCircle className="w-4 h-4 mr-1" /> Rejection ({summary?.rejection_count || 0})
          </TabsTrigger>
          <TabsTrigger value="exit" data-testid="fb-tab-exit">
            <LogOut className="w-4 h-4 mr-1" /> Exit ({summary?.exit_count || 0})
          </TabsTrigger>
        </TabsList>

        <TabsContent value={kind} className="mt-4">
          {loading ? (
            <div className="text-center py-8 text-slate-500">Loading...</div>
          ) : subs.length === 0 ? (
            <div className="text-center py-12 text-slate-500 text-sm">No {kind} feedback submitted yet.</div>
          ) : (
            <div className="space-y-2">
              {subs.map((s) => (
                <Card key={s.id} className="border-slate-200 shadow-none cursor-pointer hover:shadow-md transition-all" onClick={() => setViewing(s)} data-testid={`fb-row-${s.id}`}>
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-slate-900">{s.subject_name || 'Anonymous'}</p>
                        <p className="text-xs text-slate-500 mt-0.5">
                          {s.subject_phone} · {new Date(s.submitted_at).toLocaleString()}
                        </p>
                      </div>
                      <Badge variant="outline" className="capitalize">{s.kind}</Badge>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* Detail dialog */}
      <Dialog open={!!viewing} onOpenChange={(o) => !o && setViewing(null)}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto" data-testid="fb-detail-dialog">
          <DialogHeader>
            <DialogTitle className="font-heading">{viewing?.subject_name || 'Feedback'}</DialogTitle>
            <p className="text-xs text-slate-500">{viewing && new Date(viewing.submitted_at).toLocaleString()}</p>
          </DialogHeader>
          {viewing && (
            <div className="space-y-3">
              {Object.entries(viewing.answers || {}).map(([k, v]) => (
                <div key={k} className="p-3 rounded border border-slate-100">
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">{k.replace(/_/g, ' ')}</p>
                  {/^[1-5]$/.test(String(v)) ? (
                    <StarRating value={Number(v)} readOnly size={18} />
                  ) : (
                    <p className="text-sm text-slate-800">{v || <span className="text-slate-400 italic">No answer</span>}</p>
                  )}
                </div>
              ))}
              {viewing.meta && Object.keys(viewing.meta).length > 0 && (
                <div className="text-xs text-slate-400 pt-2 border-t border-slate-100">
                  Context: {JSON.stringify(viewing.meta)}
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
