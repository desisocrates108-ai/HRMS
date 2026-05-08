import { Star } from 'lucide-react';

export function StarRating({ value = 0, onChange, size = 20, readOnly = false, testId }) {
  return (
    <div className="flex items-center gap-1" data-testid={testId}>
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          type="button"
          key={n}
          onClick={() => !readOnly && onChange?.(n)}
          className={`transition-transform ${readOnly ? 'cursor-default' : 'hover:scale-110 active:scale-95'}`}
          disabled={readOnly}
          data-testid={testId ? `${testId}-star-${n}` : undefined}
        >
          <Star
            width={size}
            height={size}
            className={n <= value ? 'fill-amber-400 text-amber-400' : 'fill-transparent text-slate-300'}
          />
        </button>
      ))}
    </div>
  );
}

export default StarRating;
