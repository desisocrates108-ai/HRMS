import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { StarRating } from '@/components/StarRating';
import { CheckCircle, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';

const API = axios.create({ baseURL: `${process.env.REACT_APP_BACKEND_URL}/api` });

export default function FeedbackPage() {
  const { token } = useParams();
  const [state, setState] = useState('loading'); // loading | ready | submitted | error | already_submitted
  const [form, setForm] = useState(null);
  const [answers, setAnswers] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    (async () => {
      try {
        const { data } = await API.get(`/feedback/form/${token}`);
        setForm(data);
        setState('ready');
      } catch (err) {
        const status = err?.response?.status;
        if (status === 410) setState('already_submitted');
        else { setErrorMsg(err?.response?.data?.detail || 'Invalid or expired link'); setState('error'); }
      }
    })();
  }, [token]);

  const handleSubmit = async () => {
    // Validate required non-text fields
    for (const f of form.fields) {
      if (f.type !== 'text' && (!answers[f.key] || answers[f.key] === '')) {
        toast.error(`Please answer: ${f.label}`);
        return;
      }
    }
    setSubmitting(true);
    try {
      // Convert all answers to strings for API
      const stringAnswers = {};
      Object.entries(answers).forEach(([k, v]) => { stringAnswers[k] = String(v); });
      await API.post(`/feedback/${token}`, { answers: stringAnswers });
      setState('submitted');
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Failed to submit');
    } finally { setSubmitting(false); }
  };

  const renderField = (f) => {
    const val = answers[f.key];
    if (f.type === 'rating') {
      return (
        <StarRating
          value={val || 0}
          onChange={(v) => setAnswers({ ...answers, [f.key]: v })}
          size={28}
          testId={`fb-rating-${f.key}`}
        />
      );
    }
    if (f.type === 'yes_no') {
      return (
        <div className="flex gap-2">
          {['yes', 'no'].map((opt) => (
            <button
              key={opt}
              onClick={() => setAnswers({ ...answers, [f.key]: opt })}
              className={`flex-1 px-4 py-2 rounded-md border text-sm font-medium transition-all ${
                val === opt
                  ? 'bg-blue-700 text-white border-blue-700'
                  : 'bg-white text-slate-700 border-slate-200 hover:border-slate-300'
              }`}
              data-testid={`fb-yesno-${f.key}-${opt}`}
            >
              {opt.toUpperCase()}
            </button>
          ))}
        </div>
      );
    }
    return (
      <Textarea
        value={val || ''}
        onChange={(e) => setAnswers({ ...answers, [f.key]: e.target.value })}
        rows={3}
        placeholder="Type your answer..."
        data-testid={`fb-text-${f.key}`}
      />
    );
  };

  if (state === 'loading') return <CenteredBox><p className="text-slate-500">Loading...</p></CenteredBox>;
  if (state === 'error') return (
    <CenteredBox>
      <AlertCircle className="w-12 h-12 text-rose-500 mx-auto" />
      <h2 className="text-lg font-semibold mt-3">Link unavailable</h2>
      <p className="text-slate-500 text-sm mt-1">{errorMsg}</p>
    </CenteredBox>
  );
  if (state === 'already_submitted' || state === 'submitted') return (
    <CenteredBox>
      <CheckCircle className="w-14 h-14 text-emerald-500 mx-auto" />
      <h2 className="text-xl font-semibold mt-3">Thank you!</h2>
      <p className="text-slate-500 text-sm mt-1">
        {state === 'submitted' ? 'Your feedback has been submitted successfully.' : 'This form has already been submitted.'}
      </p>
    </CenteredBox>
  );

  const title = form.kind === 'rejection' ? 'Candidate Feedback' : 'Exit Feedback';
  const subtitle = form.kind === 'rejection'
    ? 'We appreciate you sharing your experience with us.'
    : 'Your honest feedback helps us grow. Thank you for your time at Servall.';

  return (
    <div className="min-h-screen bg-slate-50 py-8 px-4" data-testid="feedback-page">
      <div className="max-w-xl mx-auto">
        <div className="text-center mb-6">
          <h1 className="text-2xl font-heading font-bold text-slate-900">Servall</h1>
          <p className="text-xs text-slate-500 mt-1">Two-Wheeler Servicing</p>
        </div>
        <Card className="border-slate-200 shadow-sm">
          <CardHeader>
            <CardTitle className="font-heading">{title}</CardTitle>
            <p className="text-sm text-slate-500">Hi {form.subject_name || 'there'}, {subtitle}</p>
          </CardHeader>
          <CardContent className="space-y-5">
            {form.fields.map((f) => (
              <div key={f.key} className="space-y-2">
                <Label className="text-sm text-slate-800">{f.label}{f.type !== 'text' && ' *'}</Label>
                {renderField(f)}
              </div>
            ))}
            <Button
              onClick={handleSubmit}
              disabled={submitting}
              className="w-full bg-blue-700 hover:bg-blue-800 h-11"
              data-testid="fb-submit"
            >
              {submitting ? 'Submitting...' : 'Submit Feedback'}
            </Button>
            <p className="text-xs text-slate-400 text-center">Your response is anonymous to interviewers and visible only to leadership.</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function CenteredBox({ children }) {
  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center px-4">
      <Card className="border-slate-200 shadow-sm max-w-md w-full">
        <CardContent className="p-8 text-center">{children}</CardContent>
      </Card>
    </div>
  );
}
