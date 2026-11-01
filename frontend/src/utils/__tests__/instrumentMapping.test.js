import { describe, expect, it } from 'vitest'
import {
  applyMappingToRows,
  mapSourceColumnToTarget
} from '../instrumentMapping.js'

describe('applyMappingToRows', () => {
  it('keeps mapped values attached to target fields when source key casing differs', () => {
    const mapped = applyMappingToRows(
      [
        {
          'Borrower Principal': 125000,
          'ANNUAL RATE': 0,
          'Term Days': 90
        }
      ],
      ['Principal', 'Interest Rate', 'Term'],
      {
        Principal: 'borrower principal',
        'Interest Rate': 'Annual Rate',
        Term: 'Term Days'
      }
    )

    expect(mapped).toEqual([{
      Principal: 125000,
      'Interest Rate': 0,
      Term: 90
    }])
  })

  it('unwraps workbook cell values and leaves unmapped fields empty', () => {
    const mapped = applyMappingToRows(
      [{ Balance: { t: 'n', v: 250000, w: '250,000.00' } }],
      ['Face Value', 'Coupon Rate'],
      { 'Face Value': 'Balance', 'Coupon Rate': '__na__' }
    )

    expect(mapped).toEqual([{
      'Face Value': 250000,
      'Coupon Rate': ''
    }])
  })

  it('stores source-header selections in the target-to-source mapping shape', () => {
    const updated = mapSourceColumnToTarget(
      { Principal: 'Balance', 'Interest Rate': 'Rate' },
      'Balance',
      'Face Value'
    )

    expect(updated).toEqual({
      'Interest Rate': 'Rate',
      'Face Value': 'Balance'
    })
  })
})
