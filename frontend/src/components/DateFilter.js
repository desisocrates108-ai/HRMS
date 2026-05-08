import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Calendar as CalIcon } from 'lucide-react';

/**
 * Emits { date_from?, date_to?, days? } via onChange.
 * Presets: today, yesterday, 7d, 30d, this_month, custom
 */
const PRESETS = [
  { key: 'today', label: 'Today' },
  { key: 'yesterday', label: 'Yesterday' },
  { key: '7d', label: 'Last 7 Days' },
  { key: '30d', label: 'Last 30 Days' },
  { key: 'this_month', label: 'This Month' },
  { key: 'all', label: 'All Time' },
];

function rangeFor(preset) {
  const now = new Date();
  const iso = (d) => d.toISOString();
  const dayStart = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).toISOString();
  const dayEnd = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate(), 23, 59, 59).toISOString();
  if (preset === 'today') return { date_from: dayStart(now), date_to: dayEnd(now) };
  if (preset === 'yesterday') {
    const y = new Date(now); y.setDate(y.getDate() - 1);
    return { date_from: dayStart(y), date_to: dayEnd(y) };
  }
  if (preset === '7d') { const d = new Date(now); d.setDate(d.getDate() - 7); return { date_from: iso(d) }; }
  if (preset === '30d') { const d = new Date(now); d.setDate(d.getDate() - 30); return { date_from: iso(d) }; }
  if (preset === 'this_month') {
    const d = new Date(now.getFullYear(), now.getMonth(), 1);
    return { date_from: iso(d) };
  }
  return {};
}

export default function DateFilter({ value, onChange, testId = 'date-filter' }) {
  const [preset, setPreset] = useState(value?.preset || '30d');
  const [customFrom, setCustomFrom] = useState('');
  const [customTo, setCustomTo] = useState('');
  const [open, setOpen] = useState(false);

  const pick = (p) => {
    setPreset(p);
    setOpen(false);
    onChange?.({ preset: p, ...rangeFor(p) });
  };

  const applyCustom = () => {
    if (!customFrom && !customTo) return;
    setPreset('custom');
    setOpen(false);
    const range = {};
    if (customFrom) range.date_from = new Date(customFrom).toISOString();
    if (customTo) range.date_to = new Date(customTo + 'T23:59:59').toISOString();
    onChange?.({ preset: 'custom', ...range });
  };

  const label = preset === 'custom'
    ? (customFrom || '') + ' → ' + (customTo || '')
    : PRESETS.find((p) => p.key === preset)?.label || 'Select';

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="outline" className="h-9 gap-2" data-testid={testId}>
          <CalIcon className="w-4 h-4" /> {label}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-64 p-2" align="end">
        <div className="space-y-1 mb-2">
          {PRESETS.map((p) => (
            <button
              key={p.key}
              onClick={() => pick(p.key)}
              className={`w-full text-left text-sm px-3 py-1.5 rounded ${preset === p.key ? 'bg-blue-700 text-white' : 'hover:bg-slate-100'}`}
              data-testid={`${testId}-${p.key}`}
            >
              {p.label}
            </button>
          ))}
        </div>
        <div className="border-t border-slate-100 pt-2 space-y-2">
          <p className="text-xs font-semibold uppercase text-slate-500">Custom</p>
          <Input type="date" value={customFrom} onChange={(e) => setCustomFrom(e.target.value)} className="h-8 text-xs" />
          <Input type="date" value={customTo} onChange={(e) => setCustomTo(e.target.value)} className="h-8 text-xs" />
          <Button size="sm" onClick={applyCustom} className="w-full h-7 text-xs bg-blue-700 hover:bg-blue-800">Apply</Button>
        </div>
      </PopoverContent>
    </Popover>
  );
}
