import { autoDetectInstrumentFields } from './frontend/src/utils/autoDetect.tmp.mjs'
import fs from 'fs'
const MM = ['Instrument','Amount','Rate','Principal','Trade Date','Issue Date','Settlement Date','Valuation Date','Maturity Date','Days to Maturity','Currency','Day Count Convention','Instrument Type','Status']
const TB = ['TBillName','FaceValue','DiscountRate','Valuation Date','Issue Date','Settlement Date','Auction Date','Maturity Date','Days to Maturity','Currency','Day Count Convention','Instrument Type','Status']
const files = {
  '7a2a4fb4c2b74ab1b1f99719f362cfa0.xlsm': [['Input Data',MM,'money-market'],['ZWG Money Market',MM,'money-market'],['US$ Money Market',MM,'money-market'],['Sheet1',MM,'money-market'],['Bonds Input',MM,'money-market'],['NSS',MM,'money-market']],
  'b12ccdb2dc23434488e6de79580174d3.xlsm': [['Legacy Debt',TB,'tbills'],['Market Inputs ',TB,'tbills']],
  '8547d89581254ccbb2c4656083cd8069.xlsm': [['Valuation Summary',TB,'tbills'],['GZH',TB,'tbills'],['Nhimbe',TB,'tbills'],['Solgas $5m',TB,'tbills'],['Solgas $518k',TB,'tbills'],['Glytime ',TB,'tbills'],['Zimcampus',TB,'tbills'],['Richaw $5m',TB,'tbills']],
}
for (const [f, sheets] of Object.entries(files)) {
  const buf = fs.readFileSync('backend/uploads/'+f)
  const ab = buf.buffer.slice(buf.byteOffset, buf.byteOffset+buf.byteLength)
  for (const [sheet, req, type] of sheets) {
    try {
      const r = await autoDetectInstrumentFields(ab, sheet, req, type, null, null, null, null)
      const all = {...r.fields, ...r.additionalFields}
      const keys = Object.keys(all)
      console.log(`\n### ${f.slice(0,8)} / ${sheet} [${type}] — ${keys.length} fields`)
      for (const k of ['instrument_name','face_value','principal','amount','interest_rate','coupon_rate','discount_rate','valuation_date','maturity_date','issue_date','currency','present_value','fair_value','carrying_value','spread','country_risk_premium','accrued_interest','coupon_frequency','days_to_maturity','term_days']) {
        if (all[k] !== undefined) console.log(`   ${k} = ${JSON.stringify(all[k])}`)
      }
    } catch(e) { console.log(`\n### ${sheet} ERROR: ${e.message}`) }
  }
}
