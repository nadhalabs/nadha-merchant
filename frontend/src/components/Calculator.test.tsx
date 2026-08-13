import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { Calculator } from './Calculator';

describe('Calculator', () => {
  it('performs arithmetic and keeps decimal entry visible', () => {
    render(<Calculator />);
    for (const key of ['2', '+', '3', '=']) fireEvent.click(screen.getByRole('button', { name: key }));
    expect(screen.getByText('5', { selector: '.ios-display' })).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'AC' }));
    fireEvent.click(screen.getByRole('button', { name: '.' }));
    expect(screen.getByText('0.', { selector: '.ios-display' })).toBeTruthy();
  });
});
