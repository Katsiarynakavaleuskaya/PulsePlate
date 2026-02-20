import { useEffect, useMemo, useState } from 'react';
import type { ChangeEvent, InputHTMLAttributes } from 'react';
import { Input } from './Input';

type NumberInputValue = number | '';
type NumberInputLocale = 'ru' | 'en';

interface NumberInputProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, 'value' | 'onChange' | 'type'> {
  value: NumberInputValue;
  onValueChange: (value: NumberInputValue) => void;
  locale?: NumberInputLocale;
}

function parseNumericInput(rawValue: string): NumberInputValue {
  const normalized = rawValue.trim().replace(',', '.');
  if (normalized.length === 0) return '';
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : '';
}

function isCompleteNumericInput(rawValue: string): boolean {
  const normalized = rawValue.trim().replace(',', '.');
  if (normalized.length === 0) return false;
  if (normalized.endsWith('.')) return false;
  return /^[-+]?(?:\d+\.?\d*|\.\d+)$/.test(normalized);
}

export function NumberInput({
  value,
  onValueChange,
  locale = 'en',
  inputMode = 'decimal',
  ...props
}: NumberInputProps) {
  const displayValueFromValue = useMemo(() => {
    if (value === '') return '';
    const asString = String(value);
    return locale === 'ru' ? asString.replace('.', ',') : asString;
  }, [locale, value]);
  const [rawValue, setRawValue] = useState(displayValueFromValue);

  useEffect(() => {
    setRawValue(displayValueFromValue);
  }, [displayValueFromValue]);

  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    const nextRawValue = event.target.value;
    setRawValue(nextRawValue);

    if (nextRawValue.trim().length === 0) {
      onValueChange('');
      return;
    }
    if (!isCompleteNumericInput(nextRawValue)) return;

    const parsedValue = parseNumericInput(nextRawValue);
    if (parsedValue !== '') {
      onValueChange(parsedValue);
    }
  };

  return <Input type="text" inputMode={inputMode} value={rawValue} onChange={handleChange} {...props} />;
}

export default NumberInput;
