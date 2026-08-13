import {describe,expect,it} from 'vitest';
import {ApiError,errorKey,money} from './client';
describe('money formatting',()=>{it('formats INR without floating point calculations',()=>{expect(money('1250.50')).toContain('1,250.5')})});
describe('merchant-safe errors',()=>{it('maps technical API failures to translation keys',()=>{expect(errorKey(new ApiError('NETWORK_ERROR'))).toBe('errors.network');expect(errorKey(new ApiError('SESSION_EXPIRED',401))).toBe('errors.session');expect(errorKey(new Error('Failed to fetch'))).toBe('errors.unknown')})});
