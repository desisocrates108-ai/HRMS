import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { CheckCircle2, FileText, UploadCloud } from 'lucide-react';
import { toast } from 'sonner';

const PUBLIC = axios.create({ baseURL: `${process.env.REACT_APP_BACKEND_URL}/api` });

const SECTIONS = [
  { key: 'personal', label: 'Personal Details' },
  { key: 'education', label: 'Education' },
  { key: 'employment', label: 'Employment Details' },
  { key: 'interview', label: 'Interview Details' },
  { key: 'documents', label: 'Documents' },
];

export default function CandidateFormPage() {
  const { token } = useParams();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [schema, setSchema] = useState(null);
  const [candidate, setCandidate] = useState({});
  const [values, setValues] = useState({});
  const [files, setFiles] = useState({});
  const [declaration, setDeclaration] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    let mounted = true;
    PUBLIC.get(`/candidate-forms/form/${token}`)
      .then(({ data }) => {
        if (!mounted) return;
        setSchema(data.schema);
        setCandidate(data.candidate || {});
        setValues({
          full_name: data.candidate?.name || '',
          mobile: data.candidate?.phone || '',
          email: data.candidate?.email || '',
        });
      })
      .catch((err) => {
        setError(err.response?.data?.detail || 'This form is no longer available.');
      })
      .finally(() => mounted && setLoading(false));
    return () => { mounted = false; };
  }, [token]);

  const updateValue = (k, v) => setValues({ ...values, [k]: v });

  const handleSubmit = async () => {
    if (!declaration) { toast.error('Please confirm the declaration'); return; }
    // Required fields
    for (const f of (schema?.personal || [])) {
      if (f.required && !String(values[f.key] || '').trim()) {
        toast.error(`${f.label} is required`);
        return;
      }
    }
    setSubmitting(true);
    try {
      const fd = new FormData();
      fd.append('answers', JSON.stringify(values));
      fd.append('declaration', 'true');
      ['resume', 'aadhaar', 'pan', 'photo'].forEach((k) => {
        if (files[k]) fd.append(k, files[k]);
      });
      await PUBLIC.post(`/candidate-forms/form/${token}`, fd, { headers: { 'Content-Type': 'multipart/form-data' } });
      setSuccess(true);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Submission failed');
    } finally { setSubmitting(false); }
  };

  if (loading) return <div className="min-h-screen flex items-center justify-center text-slate-500">Loading...</div>;

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4">
        <Card className="max-w-md border-rose-200">
          <CardContent className="p-6 text-center">
            <p className="text-rose-700 font-medium">{error}</p>
            <p className="text-xs text-slate-500 mt-2">If you believe this is a mistake, contact the HR team.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4">
        <Card className="max-w-md border-emerald-200">
          <CardContent className="p-6 text-center" data-testid="candidate-form-success">
            <CheckCircle2 className="w-12 h-12 text-emerald-600 mx-auto mb-3" />
            <p className="text-lg font-heading font-semibold text-slate-900">Thank you!</p>
            <p className="text-sm text-slate-600 mt-1">Your information has been submitted to our HR team. We'll be in touch soon.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const renderField = (f) => {
    const common = { value: values[f.key] || '', onChange: (e) => updateValue(f.key, e.target.value), className: 'mt-1', 'data-testid': `field-${f.key}` };
    if (f.type === 'textarea') return <Textarea rows={2} {...common} />;
    if (f.type === 'select') {
      return (
        <Select value={values[f.key] || ''} onValueChange={(v) => updateValue(f.key, v)}>
          <SelectTrigger className="mt-1" data-testid={`field-${f.key}`}><SelectValue placeholder="Select" /></SelectTrigger>
          <SelectContent>{(f.options || []).map(o => <SelectItem key={o} value={o}>{o}</SelectItem>)}</SelectContent>
        </Select>
      );
    }
    if (f.type === 'file') {
      const file = files[f.key];
      return (
        <div className="mt-1">
          <label
            className="flex items-center gap-2 border-2 border-dashed border-slate-300 hover:border-blue-400 rounded-lg p-3 cursor-pointer transition-colors"
            data-testid={`field-${f.key}-label`}
          >
            <UploadCloud className="w-4 h-4 text-slate-400" />
            <span className="text-xs text-slate-600 flex-1">{file ? file.name : `Tap to upload (${f.accept})`}</span>
            <input
              type="file"
              className="hidden"
              accept={f.accept}
              onChange={(e) => setFiles({ ...files, [f.key]: e.target.files?.[0] || null })}
              data-testid={`field-${f.key}`}
            />
          </label>
        </div>
      );
    }
    return <Input type={f.type === 'tel' ? 'tel' : f.type === 'email' ? 'email' : f.type === 'date' ? 'date' : 'text'} {...common} />;
  };

  return (
    <div className="min-h-screen bg-slate-50 py-6 px-4" data-testid="candidate-form-page">
      <div className="max-w-2xl mx-auto space-y-4">
        <Card className="border-slate-200">
          <CardContent className="p-5">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-blue-700 flex items-center justify-center">
                <FileText className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-heading font-semibold text-slate-900">Candidate Information Form</h1>
                <p className="text-xs text-slate-500">Hi {candidate.name || 'there'}, please fill in your details below.</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {SECTIONS.map(sec => (
          <Card key={sec.key} className="border-slate-200">
            <CardContent className="p-5 space-y-3">
              <h2 className="font-heading font-semibold text-base text-slate-900">{sec.label}</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {(schema[sec.key] || []).map(f => (
                  <div key={f.key} className={f.type === 'textarea' || f.type === 'file' ? 'sm:col-span-2' : ''}>
                    <Label className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                      {f.label}{f.required && ' *'}
                    </Label>
                    {renderField(f)}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}

        <Card className="border-slate-200">
          <CardContent className="p-5 space-y-3">
            <div className="flex items-start gap-2">
              <Checkbox id="declaration" checked={declaration} onCheckedChange={setDeclaration} data-testid="declaration-checkbox" />
              <Label htmlFor="declaration" className="text-sm text-slate-700 leading-snug cursor-pointer">
                I declare that all the information provided above is true and correct to the best of my knowledge.
              </Label>
            </div>
            <Button
              onClick={handleSubmit}
              disabled={submitting || !declaration}
              className="w-full bg-blue-700 hover:bg-blue-800 h-11"
              data-testid="submit-candidate-form-button"
            >
              {submitting ? 'Submitting...' : 'Submit My Information'}
            </Button>
            <p className="text-[10px] text-slate-400 text-center">Your data is shared only with the HR team.</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
