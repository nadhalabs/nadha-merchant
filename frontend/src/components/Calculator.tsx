import { useState } from 'react';

export function Calculator() {
  const [display, setDisplay] = useState('0');
  const [stored, setStored] = useState<number | null>(null);
  const [operator, setOperator] = useState('');
  const [fresh, setFresh] = useState(true);

  const number = (value: string) => {
    setDisplay(current => fresh ? (value === '.' ? '0.' : value) : (value === '.' && current.includes('.') ? current : current + value));
    setFresh(false);
  };
  const choose = (next: string) => { setStored(Number(display)); setOperator(next); setFresh(true); };
  const calculate = () => {
    if (stored === null || !operator) return;
    const second = Number(display);
    const result = operator === '+' ? stored + second : operator === '−' ? stored - second : operator === '×' ? stored * second : second === 0 ? 0 : stored / second;
    setDisplay(String(Number(result.toFixed(8)))); setStored(null); setOperator(''); setFresh(true);
  };
  const clear = () => { setDisplay('0'); setStored(null); setOperator(''); setFresh(true); };
  const formatted = display.endsWith('.') ? `${Number(display.slice(0, -1)).toLocaleString('en-IN')}.` : Number(display).toLocaleString('en-IN', { maximumFractionDigits: 8 });
  const keys = [
    ['AC', 'utility', clear], ['±', 'utility', () => setDisplay(value => String(-Number(value)))], ['%', 'utility', () => setDisplay(String(Number(display) / 100))], ['÷', 'operator', () => choose('÷')],
    ['7', 'number', () => number('7')], ['8', 'number', () => number('8')], ['9', 'number', () => number('9')], ['×', 'operator', () => choose('×')],
    ['4', 'number', () => number('4')], ['5', 'number', () => number('5')], ['6', 'number', () => number('6')], ['−', 'operator', () => choose('−')],
    ['1', 'number', () => number('1')], ['2', 'number', () => number('2')], ['3', 'number', () => number('3')], ['+', 'operator', () => choose('+')],
    ['0', 'number zero', () => number('0')], ['.', 'number', () => number('.')], ['=', 'operator', calculate],
  ] as const;
  return <section className="ios-calculator" aria-label="Calculator"><div className="ios-display" aria-live="polite">{formatted}</div><div className="ios-keys">{keys.map(([label, kind, action]) => <button type="button" key={label} aria-label={label} className={`${kind} ${operator === label ? 'active' : ''}`} onClick={action}>{label}</button>)}</div></section>;
}
