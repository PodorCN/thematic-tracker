import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {spawnSync} from "node:child_process";
import {pathToFileURL} from "node:url";
// Importing the module must not run a fetch or write production data.
globalThis.fetch = () => { throw new Error("Unexpected network access"); };
const {parsePolymarket, configuredMarket, normalizeProbs, fetchPolymarket, mergeResults, writeCandidate} = await import("./fetch_betting.mjs");
const now = Date.parse("2026-11-16T14:00:00Z");
const cfg = {slug: "fed-decision-december", meetingDate: "2026-12-09", meetingDatetime: "2026-12-09T14:00:00-05:00", now};
function event() { return {slug: cfg.slug, closed: false, active: true,
  endDate: "2026-12-09T19:00:00Z", updatedAt: "2026-11-16T13:59:00Z",
  markets: ["No Change", "25 bps increase", "50+ bps increase", "25 bps decrease", "50+ bps decrease"].map((label, i) =>
    ({groupItemTitle: label, updatedAt: "2026-11-16T13:59:00Z", outcomes: '["Yes","No"]', outcomePrices: JSON.stringify([i === 0 ? .6 : .1, i === 0 ? .4 : .9])}))}; }
const parse = e => parsePolymarket([e], cfg);
function cleanupTemp(tmp) {
  assert.ok(fs.realpathSync(tmp).startsWith(fs.realpathSync(os.tmpdir()) + path.sep));
  fs.rmSync(tmp, {recursive: true});
}
test("No Change case/whitespace variants map to hold", () => {
  for (const label of ["No Change", "No change", "no change", "  NO   CHANGE  "]) {
    const e = event(); e.markets[0].groupItemTitle = label;
    assert.deepEqual(parse(e).probabilities, {cut: .2, hold: .6, hike: .2});
  }
});
test("reversed binary outcome order uses actual Yes index", () => {
  const e = event(); e.markets[0].outcomes = '["No","Yes"]'; e.markets[0].outcomePrices = '[0.4,0.6]';
  assert.equal(parse(e).probabilities.hold, .6);
});
test("missing leg refuses rather than normalizing incomplete data", () => {const e=event();e.markets.pop();assert.throws(()=>parse(e),/Missing/);});
test("duplicate normalized leg refuses", () => {const e=event();e.markets.push({...e.markets[0],groupItemTitle:"NO CHANGE"});assert.throws(()=>parse(e),/Duplicate/);});
test("unknown label refuses", () => {const e=event();e.markets[0].groupItemTitle="Other";assert.throws(()=>parse(e),/Unrecognized/);});
test("zero ladder cannot manufacture 100% hold", () => {const e=event();e.markets.forEach(m=>m.outcomePrices='[0,1]');assert.throws(()=>parse(e),/ladder deviates/);});
test("negative/nonfinite/out-of-range/empty prices refuse", () => {
  for(const n of [-.1,1.1,"NaN","Infinity",null,""]) {const e=event();e.markets[0].outcomePrices=JSON.stringify([n,.4]);assert.throws(()=>parse(e));}
  assert.throws(()=>normalizeProbs(NaN,0,0));
});
test("closed archived inactive and unknown-open events refuse",()=>{for(const patch of [{closed:true},{closed:undefined},{active:false},{archived:true}])assert.throws(()=>parse({...event(),...patch}),/closed|archived|open/);});
test("closed market leg refuses",()=>{const e=event();e.markets[0].closed=true;assert.throws(()=>parse(e),/Closed/);});
test("past or wrong meeting cannot be relabelled current",()=>{for(const endDate of ['2026-10-28T18:00:00Z','2026-12-10T19:00:00Z'])assert.throws(()=>parse({...event(),endDate}),/upcoming/);});
test("venue settlement metadata accepts end-of-day Toronto or UTC date, without claiming announcement clock",()=>{
  for(const endDate of ['2026-12-10T04:59:00Z','2026-12-09T00:00:00Z']) {
    const got=parse({...event(),endDate});assert.match(got.note,/not the policy announcement time/);
  }
});
test("mismatched or multiple event identity refuses",()=>{assert.throws(()=>parse({...event(),slug:'wrong'}),/identity/);assert.throws(()=>parsePolymarket([event(),event()],cfg),/exactly one/);});
test("stale/future/naive/invalid venue timestamps refuse",()=>{for(const updatedAt of ['2026-11-16T12:00:00Z','2026-11-16T14:06:00Z','2026-11-16T13:59:00','invalid'])assert.throws(()=>parse({...event(),updatedAt}));});
test("exact source timestamp is preserved rather than restamped",()=>assert.equal(parse(event()).as_of,'2026-11-16T13:59:00Z'));
test("largest remainder rounding stays nonnegative at 49.5/0/50.5",()=>{
  const result=normalizeProbs(.495,0,.505);assert.ok(Object.values(result).every(n=>n>=0));
  assert.equal(Object.values(result).reduce((a,b)=>a+Math.round(b*100),0),100);
});
test("each price leg must be fresh; newest event cannot mask stale prices",()=>{
  const e=event();e.markets[0].updatedAt='2026-10-01T14:00:00Z';assert.throws(()=>parse(e),/leg timestamp stale/);
});
test("as_of is conservative oldest actual price timestamp",()=>{
  const e=event();e.markets[0].updatedAt='2026-11-16T13:50:00Z';assert.equal(parse(e).as_of,e.markets[0].updatedAt);
});
test("coarse BoC settlement metadata cannot expire a still-upcoming announcement",()=>{
  const e=event();e.endDate='2026-12-09T00:00:00Z';e.updatedAt='2026-12-09T12:59:00Z';e.markets.forEach(m=>m.updatedAt=e.updatedAt);
  assert.equal(parsePolymarket([e],{...cfg,meetingDatetime:'2026-12-09T09:45:00-05:00',now:Date.parse('2026-12-09T13:00:00Z')}).status,'available');
  assert.throws(()=>parsePolymarket([e],{...cfg,meetingDatetime:'2026-12-09T09:45:00-05:00',now:Date.parse('2026-12-09T15:00:00Z')}),/upcoming/);
});
test("incoherent binary prices refuse instead of manufacturing a ladder",()=>{
  const e=event();e.markets.forEach(m=>m.outcomePrices='[0.001,0.001]');assert.throws(()=>parse(e),/sum to one/);
});
test("grossly incoherent mutually exclusive ladder refuses even with valid binary pairs",()=>{
  for(const pair of ['[0.001,0.999]','[1,0]']) {const e=event();e.markets.forEach(m=>m.outcomePrices=pair);assert.throws(()=>parse(e),/ladder deviates/);}
});
test("malformed or ambiguous outcome arrays refuse",()=>{for(const patch of [{outcomes:'bad'},{outcomes:'["Yes","Yes"]'},{outcomePrices:'[0.6]'}]){const e=event();Object.assign(e.markets[0],patch);assert.throws(()=>parse(e));}});
const doc=()=>({meetings:{fed:{next_meeting:{datetime_toronto:'2026-12-09T14:00:00-05:00'}},boc:{next_meeting:{datetime_toronto:'2026-12-09T09:45:00-05:00'}}},betting:{fed:[{platform:'Polymarket',event_slug:cfg.slug},{platform:'Kalshi',note:'preserve'}],boc:[{platform:'Polymarket',event_slug:'boc-december'}]},unrelated:{keep:true}});
test("slugs come from current configured meeting, never hardcoded October",()=>{assert.equal(configuredMarket(doc(),'fed').slug,cfg.slug);assert.equal(configuredMarket(doc(),'boc').meetingDate,'2026-12-09');});
test("missing duplicate or unsafe configured slugs refuse",()=>{for(const rows of [[],[{platform:'Polymarket',event_slug:'../../other'}],[{platform:'Polymarket',event_slug:'x'},{platform:'Polymarket',event_slug:'y'}]]){const d=doc();d.betting.fed=rows;assert.throws(()=>configuredMarket(d,'fed'));}});
test("HTTP failure stops; no automatic retry",async()=>{let calls=0;await assert.rejects(fetchPolymarket(cfg,{now,fetchImpl:async()=>{calls++;return {ok:false,status:403};}}),/HTTP 403/);assert.equal(calls,1);});
test("mock fetch uses bounded signal and validates source",async()=>{const got=await fetchPolymarket(cfg,{now,fetchImpl:async(url,opts)=>{assert.match(url,/slug=fed-decision-december/);assert.ok(opts.signal);return {ok:true,json:async()=>[event()]};}});assert.equal(got.probabilities.hold,.6);});
test("partial bank update refuses and inputs remain unchanged",()=>{const d=doc(),before=JSON.stringify(d);assert.throws(()=>mergeResults(d,{fed:parse(event())}),/Both banks/);assert.equal(JSON.stringify(d),before);});
test("complete merge preserves other venues and unrelated bytes in data model",()=>{const d=doc(),before=JSON.stringify(d);const fed=parse(event()),boc={...fed,event_slug:'boc-december'};const next=mergeResults(d,{fed,boc});assert.deepEqual(next.betting.fed[1],d.betting.fed[1]);assert.deepEqual(next.unrelated,d.unrelated);assert.equal(JSON.stringify(d),before);assert.throws(()=>mergeResults(d,{fed:{...fed,event_slug:'wrong'},boc}),/slug mismatch/);});
test("candidate publication is atomic and never overwrites current or an existing candidate",()=>{
 const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'rates-candidate-'));
 try {const current=path.join(tmp,'current.json'),candidate=path.join(tmp,'betting-candidate.json');fs.writeFileSync(current,'original user bytes');
  writeCandidate(candidate,{complete:true});assert.deepEqual(JSON.parse(fs.readFileSync(candidate)),{complete:true});
  assert.throws(()=>writeCandidate(candidate,{overwrite:true}),/EEXIST/);assert.equal(fs.readFileSync(current,'utf8'),'original user bytes');
  assert.deepEqual(JSON.parse(fs.readFileSync(candidate)),{complete:true});assert.equal(fs.readdirSync(tmp).filter(n=>n.endsWith('.tmp')).length,0);
 } finally {cleanupTemp(tmp);}
});
test("interrupted candidate staging cannot truncate current or expose partial candidate",()=>{
 const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'rates-candidate-'));
 try {const current=path.join(tmp,'current.json'),candidate=path.join(tmp,'betting-candidate.json');fs.writeFileSync(current,'original user bytes');
  assert.throws(()=>writeCandidate(candidate,{complete:true},{write:(fd)=>{fs.writeSync(fd,'partial');throw new Error('simulated interruption');}}),/simulated/);
  assert.equal(fs.existsSync(candidate),false);assert.equal(fs.readFileSync(current,'utf8'),'original user bytes');assert.deepEqual(fs.readdirSync(tmp),['current.json']);
 } finally {cleanupTemp(tmp);}
});
function cliFixture(fn) {
 const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'rates-cli-'));
 try {
  fs.mkdirSync(path.join(tmp,'scripts'));fs.mkdirSync(path.join(tmp,'data'));
  fs.copyFileSync(new URL('./fetch_betting.mjs',import.meta.url),path.join(tmp,'scripts','fetch_betting.mjs'));
  const d=doc(),future=new Date(Date.now()+60*86400000).toISOString();
  d.meetings.fed.next_meeting.datetime_toronto=future;d.meetings.boc.next_meeting.datetime_toronto=future;
  const current=path.join(tmp,'data','current.json'),original=JSON.stringify(d,null,2)+'\n';fs.writeFileSync(current,original);
  const e=event();e.endDate=future;e.updatedAt=new Date(Date.now()-60000).toISOString();e.markets.forEach(m=>m.updatedAt=e.updatedAt);
  const preload=path.join(tmp,'mock.mjs'),calls=path.join(tmp,'calls.txt');
  fs.writeFileSync(preload,`import fs from 'node:fs';const e=${JSON.stringify(e)};globalThis.fetch=async(url)=>{fs.appendFileSync(${JSON.stringify(calls)},'1');if(process.argv.includes('--candidate')&&fs.existsSync(${JSON.stringify(path.join(tmp,'fail-boc'))})&&url.includes('boc-december'))return {ok:false,status:503};return {ok:true,json:async()=>[{...e,slug:url.includes('boc-december')?'boc-december':'fed-decision-december'}]};};`);
  const run=arg=>spawnSync(process.execPath,['--import',pathToFileURL(preload).href,path.join(tmp,'scripts','fetch_betting.mjs'),arg],{encoding:'utf8',timeout:10000});
  fn({tmp,current,original,run,calls,candidate:path.join(tmp,'data','betting-candidate.json')});
 } finally {cleanupTemp(tmp);}
}
test("CLI candidate emission preserves current and refuses a second candidate",()=>cliFixture(({current,original,run,candidate})=>{
 assert.equal(run('--candidate').status,0);assert.equal(fs.readFileSync(current,'utf8'),original);assert.ok(fs.existsSync(candidate));
 const saved=fs.readFileSync(candidate,'utf8');assert.notEqual(run('--candidate').status,0);assert.equal(fs.readFileSync(candidate,'utf8'),saved);assert.equal(fs.readFileSync(current,'utf8'),original);
}));
test("CLI partial fetch failure emits no candidate and preserves current",()=>cliFixture(({tmp,current,original,run,candidate,calls})=>{
 fs.writeFileSync(path.join(tmp,'fail-boc'),'fixture');const result=run('--candidate');assert.notEqual(result.status,0);assert.match(result.stderr,/HTTP 503/);assert.equal(fs.readFileSync(calls,'utf8'),'11');assert.equal(fs.existsSync(candidate),false);assert.equal(fs.readFileSync(current,'utf8'),original);
}));
test("CLI deprecated write fails before any fetch or file mutation",()=>cliFixture(({current,original,run,candidate,calls})=>{
 const p=run('--write');assert.notEqual(p.status,0);assert.match(p.stderr,/Direct --write removed/);assert.equal(fs.existsSync(calls),false);assert.equal(fs.existsSync(candidate),false);assert.equal(fs.readFileSync(current,'utf8'),original);
}));
