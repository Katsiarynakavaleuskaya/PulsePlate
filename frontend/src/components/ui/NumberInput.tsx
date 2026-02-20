import { useMemo } from 'react';
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

  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    const parsedValue = parseNumericInput(event.target.value);
    onValueChange(parsedValue);
  };

  return <Input type="text" inputMode={inputMode} value={displayValue} onChange={handleChange} {...props} />;
}

export default NumberInput;
