import { autoDetectInstrumentFields } from './frontend/src/utils/autoDetect.tmp.mjs'
import fs from 'fs'
const buf = fs.readFileSync('backend/uploads/3b9461b5011a4c269555dd52fa7f0e7f.xlsm')
const ab = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength)
const REQ = ['BondName','FaceValue','CouponRate','Yield','Years to Maturity','Maturity Date','Issue Date','Settlement Date','Valuation Date','Last Coupon Date','Coupon Frequency','Currency','Day Count Convention','Instrument Type','Status']
const r = await autoDetectInstrumentFields(ab, 'Richaw $205k', REQ, 'bonds', null, null, null, null)
const all = {...r.fields, ...r.additionalFields}
// simulate cleaning number conversion (fixed logic)
const clean = {}
for (const [k,v] of Object.entries(all)) {
  if (typeof v === 'string') {
    const s = v.trim()
    const ns = /^-?\d{1,3}(,\d{3})+(\.\d+)?$/.test(s) ? s.replace(/,/g,'') : s
    const n = parseFloat(ns)
    clean[k] = (!isNaN(n) && ns !== '') ? n : v
  } else clean[k] = v
}
// derivations
clean.status='Active'; clean.day_count_convention='ACT/360'
clean.coupon_frequency = /semi/i.test(String(all.coupon_frequency)) ? 2 : all.coupon_frequency
for (const n of ['fairvalue','presentvalue','marketvalue','carryingvalue']) {
  const k = Object.keys(clean).find(k=>k.toLowerCase().replace(/[\s_\-]/g,'')===n)
  if (k) { const num=parseFloat(String(clean[k]).replace(/[$,\s]/g,'')); if(!isNaN(num)&&num>0){clean.current_price=num;break} }
}
const vd=clean.valuation_date, md=clean.maturity_date
if (vd&&md){const y=(new Date(md)-new Date(vd))/(365.25*864e5); if(y>0) clean.years_to_maturity=Math.round(y*100)/100}
console.log('DETECTED:', JSON.stringify({maturity_date:all.maturity_date, issue_date:all.issue_date, valuation_date:all.valuation_date, accrued_interest:all.accrued_interest}))
console.log('CLEANED :', JSON.stringify({maturity_date:clean.maturity_date, issue_date:clean.issue_date, valuation_date:clean.valuation_date, accrued_interest:clean.accrued_interest, current_price:clean.current_price, years_to_maturity:clean.years_to_maturity}))
const res = await fetch('http://127.0.0.1:5000/api/calculate/bonds',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({data:[clean]})})
const j = await res.json()
const c = j.data?.calculations?.[0]||{}
console.log('BACKEND :', JSON.stringify({status:c.status, maturity_date:c.maturity_date, issue_date:c.issue_date, valuation_date:c.valuation_date, accrued_interest:c.accrued_interest, days_accrued:c.days_accrued, current_price:c.current_price, ytm:c.yield_to_maturity, missing:c.missing_fields}))
