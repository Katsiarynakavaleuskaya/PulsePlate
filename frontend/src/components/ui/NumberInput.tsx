import { useEffect, useMemo, useState } from 'react';
import type { ChangeEvent, FocusEvent, InputHTMLAttributes } from 'react';
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

function shouldDeferNumericCommit(rawValue: string): boolean {
  const normalized = rawValue.trim();
  return normalized === '-' || normalized.endsWith('.') || normalized.endsWith(',');
}

export function NumberInput({
  value,
  onValueChange,
  locale = 'en',
  inputMode = 'decimal',
  ...props
}: NumberInputProps) {
  const displayValue = useMemo(() => {
    if (value === '') return '';
    const asString = String(value);
    return locale === 'ru' ? asString.replace('.', ',') : asString;
  }, [locale, value]);
  const [draftValue, setDraftValue] = useState(displayValue);

  useEffect(() => {
    setDraftValue(displayValue);
  }, [displayValue]);

  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    const rawValue = event.target.value;
    setDraftValue(rawValue);

    if (shouldDeferNumericCommit(rawValue)) {
      return;
    }

    const parsedValue = parseNumericInput(rawValue);
    onValueChange(parsedValue);
  };

  const handleBlur = (event: FocusEvent<HTMLInputElement>) => {
    if (shouldDeferNumericCommit(draftValue)) {
      const parsedValue = parseNumericInput(draftValue);
      onValueChange(parsedValue);
    }
    setDraftValue(displayValue);
    props.onBlur?.(event);
  };

  return (
    <Input
      {...props}
      type="text"
      inputMode={inputMode}
      value={draftValue}
      onChange={handleChange}
      onBlur={handleBlur}
    />
  );
}

export default NumberInput;
