import { useState, useEffect } from 'react';
import API from '@/api';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { StarRating } from '@/components/StarRating';
import { toast } from 'sonner';

const ROUND_TITLES = {
  hr: 'HR Round — Behavior & Fit',
  manager: 'Manager Round — Role & Practical',
};

export default function InterviewFormDialog({ open, onOpenChange, leadId, round, onSubmitted }) {
  const [criteria, setCriteria] = useState([]);
  const [ratings, setRatings] = useState({});
  const [remarks, setRemarks] = useState('');
  const [existing, setExisting] = useState(null);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    setRatings({});
    setRemarks('');
    setExisting(null);
    (async () => {
      try {
        const [cRes, ivRes] = await Promise.all([
          API.get('/interviews/criteria'),
          API.get(`/interviews/${leadId}`),
        ]);
        setCriteria(cRes.data[round] || []);
        const ex = ivRes.data[round];
        if (ex) {
          setExisting(ex);
          setRatings(ex.ratings || {});
          setRemarks(ex.remarks || '');
        }
      } catch {
        toast.error('Failed to load questionnaire');
      } finally {
        setLoading(false);
      }
    })();
  }, [open, leadId, round]);

  const avg = (() => {
    const vals = Object.values(ratings).filter((v) => Number.isFinite(v));
    if (!vals.length) return 0;
    return (vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(2);
  })();

  const allRated = criteria.length > 0 && criteria.every((c) => Number.isFinite(ratings[c.key]) && ratings[c.key] >= 1);

  const handleSubmit = async () => {
    if (!allRated) {
      toast.error('Please rate all 10 criteria');
      return;
    }
    if (existing?.locked) {
      toast.error('This record is locked and cannot be edited');
      return;
    }
    setSaving(true);
    try {
      await API.post(`/interviews/${leadId}/${round}`, { ratings, remarks });
      toast.success(`${round.toUpperCase()} round saved (avg ${avg}/5)`);
      onSubmitted?.();
      onOpenChange(false);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to submit');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto" data-testid={`interview-${round}-dialog`}>
        <DialogHeader>
          <DialogTitle className="font-heading">{ROUND_TITLES[round]}</DialogTitle>
          <div className="flex items-center justify-between text-xs text-slate-500 mt-1">
            <span>Rate each criterion 1–5</span>
            <span className="font-medium text-slate-900">Avg: {avg}/5</span>
          </div>
        </DialogHeader>

        {loading ? (
          <div className="py-8 text-center text-slate-500 text-sm">Loading...</div>
        ) : (
          <div className="space-y-3 py-2">
            {criteria.map((c) => (
              <div
                key={c.key}
                className="flex items-center justify-between gap-4 px-3 py-2 rounded-md border border-slate-100 hover:border-slate-200"
              >
                <Label className="text-sm text-slate-700 flex-1">{c.label}</Label>
                <StarRating
                  value={ratings[c.key] || 0}
                  onChange={(v) => setRatings({ ...ratings, [c.key]: v })}
                  testId={`rating-${c.key}`}
                  readOnly={existing?.locked}
                />
              </div>
            ))}

            <div>
              <Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Remarks</Label>
              <Textarea
                value={remarks}
                onChange={(e) => setRemarks(e.target.value)}
                rows={3}
                className="mt-1"
                placeholder="Optional notes about the candidate..."
                disabled={existing?.locked}
                data-testid={`interview-${round}-remarks`}
              />
            </div>

            {existing && (
              <p className="text-xs text-slate-400">
                Last submitted by {existing.submitted_by_name} on{' '}
                {new Date(existing.submitted_at).toLocaleString()}
                {existing.locked && ' (Locked)'}
              </p>
            )}
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button
            onClick={handleSubmit}
            disabled={saving || loading || !allRated || existing?.locked}
            className="bg-blue-700 hover:bg-blue-800"
            data-testid={`submit-interview-${round}`}
          >
            {saving ? 'Saving...' : existing ? 'Update' : 'Submit'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
