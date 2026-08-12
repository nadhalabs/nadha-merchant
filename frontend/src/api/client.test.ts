import {describe,expect,it} from 'vitest';
import {money} from './client';
describe('money formatting',()=>{it('formats INR without floating point calculations',()=>{expect(money('1250.50')).toContain('1,250.5')})});
